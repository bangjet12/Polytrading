from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from app.state import STATE
from app.market_data import coinbase_ws_loop, fetch_coinbase_candles_loop, fetch_okx_derivatives_loop
from app.polymarket import discover_btc_markets_loop, orderbook_refresh_loop
from app.runtime import strategy_loop, position_manager_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("server")

# Mongo (used for persistent trade journal)
mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "trader@scalper.local")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "scalper2026")
TV_SECRET = os.environ.get("TV_WEBHOOK_SECRET", "tv-secret")

app = FastAPI(title="Polymarket BTC Scalper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# =================== Auth ===================
class LoginReq(BaseModel):
    email: str
    password: str


def make_token(email: str) -> str:
    payload = {"sub": email, "iat": int(time.time()), "exp": int(time.time()) + 7 * 86400}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except Exception as e:
        raise HTTPException(401, f"invalid token: {e}")


@api.post("/auth/login")
async def login(body: LoginReq):
    if body.email == DEMO_EMAIL and body.password == DEMO_PASSWORD:
        return {"token": make_token(body.email), "email": body.email}
    raise HTTPException(401, "invalid credentials")


@api.get("/auth/me")
async def me(user: str = Depends(verify_token)):
    return {"email": user}


# =================== Health ===================
@api.get("/health")
async def health():
    return {"ok": True, "ts": time.time()}


# =================== State snapshot ===================
@api.get("/state")
async def get_state(user: str = Depends(verify_token)):
    return STATE.snapshot()


@api.get("/state/public")
async def get_state_public():
    """Same snapshot but unauthenticated for the live ticker (no secrets)."""
    snap = STATE.snapshot()
    return snap


# =================== Settings ===================
class SettingsBody(BaseModel):
    risk_per_trade_pct: Optional[float] = None
    daily_dd_halt_pct: Optional[float] = None
    hard_stop_pct: Optional[float] = None
    edge_threshold: Optional[float] = None
    max_edge_threshold: Optional[float] = None
    min_liquidity_usd: Optional[float] = None
    max_spread: Optional[float] = None
    daily_trade_cap: Optional[int] = None
    target_market_type: Optional[str] = None
    min_minutes_to_expiry: Optional[float] = None
    max_minutes_to_expiry: Optional[float] = None


@api.get("/settings")
async def get_settings(user: str = Depends(verify_token)):
    return STATE.settings


@api.put("/settings")
async def put_settings(body: SettingsBody, user: str = Depends(verify_token)):
    for k, v in body.model_dump(exclude_none=True).items():
        STATE.settings[k] = v
    return STATE.settings


class ModeBody(BaseModel):
    mode: str  # paper / live
    confirm: bool = False


@api.post("/mode")
async def set_mode(body: ModeBody, user: str = Depends(verify_token)):
    if body.mode not in ("paper", "live"):
        raise HTTPException(400, "mode must be paper or live")
    if body.mode == "live" and not body.confirm:
        raise HTTPException(400, "live mode requires confirm=true")
    # Check creds present if going live
    if body.mode == "live":
        if not os.environ.get("POLY_PRIVATE_KEY"):
            raise HTTPException(400, "POLY_PRIVATE_KEY not configured")
    STATE.mode = body.mode
    return {"mode": STATE.mode}


class KillBody(BaseModel):
    engaged: bool


@api.post("/kill_switch")
async def kill_switch(body: KillBody, user: str = Depends(verify_token)):
    STATE.kill_switch = body.engaged
    if body.engaged:
        # cancel all open positions (paper close at current mid)
        for p in STATE.open_positions:
            if p.get("status") == "open":
                p["status"] = "cancelled_kill"
                p["closed_at"] = datetime.now(timezone.utc).isoformat()
    return {"kill_switch": STATE.kill_switch}


class StrictBody(BaseModel):
    strict_5m_only: bool


@api.post("/strict_5m")
async def set_strict_5m(body: StrictBody, user: str = Depends(verify_token)):
    STATE.strict_5m_only = body.strict_5m_only
    if body.strict_5m_only:
        # clear current selection so auto-cycle picks a 5m market
        STATE.selected_market = None
        STATE.selected_book = {}
    return {"strict_5m_only": STATE.strict_5m_only}


class SelectMarketBody(BaseModel):
    market_id: str


@api.post("/select_market")
async def select_market(body: SelectMarketBody, user: str = Depends(verify_token)):
    for m in STATE.markets:
        if m.get("market_id") == body.market_id:
            STATE.selected_market = m
            STATE.selected_book = {}  # force refresh
            return {"selected": m}
    raise HTTPException(404, "market not found in active list")


class WalletConfigBody(BaseModel):
    private_key: Optional[str] = None
    funder_address: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_passphrase: Optional[str] = None


@api.post("/wallet/config")
async def wallet_config(body: WalletConfigBody, user: str = Depends(verify_token)):
    # Stored in environment (process only, not persisted to disk)
    mapping = {
        "POLY_PRIVATE_KEY": body.private_key,
        "POLY_FUNDER_ADDRESS": body.funder_address,
        "POLY_API_KEY": body.api_key,
        "POLY_API_SECRET": body.api_secret,
        "POLY_API_PASSPHRASE": body.api_passphrase,
    }
    for k, v in mapping.items():
        if v is not None:
            os.environ[k] = v
    return {
        "configured": {
            "private_key": bool(os.environ.get("POLY_PRIVATE_KEY")),
            "funder_address": bool(os.environ.get("POLY_FUNDER_ADDRESS")),
            "api_key": bool(os.environ.get("POLY_API_KEY")),
            "api_secret": bool(os.environ.get("POLY_API_SECRET")),
            "api_passphrase": bool(os.environ.get("POLY_API_PASSPHRASE")),
        }
    }


@api.get("/wallet/status")
async def wallet_status(user: str = Depends(verify_token)):
    return {
        "private_key": bool(os.environ.get("POLY_PRIVATE_KEY")),
        "funder_address": bool(os.environ.get("POLY_FUNDER_ADDRESS")),
        "api_key": bool(os.environ.get("POLY_API_KEY")),
        "api_secret": bool(os.environ.get("POLY_API_SECRET")),
        "api_passphrase": bool(os.environ.get("POLY_API_PASSPHRASE")),
    }


# =================== TradingView webhook ===================
class TVAlertBody(BaseModel):
    secret: Optional[str] = None
    symbol: Optional[str] = "BTCUSDT"
    timeframe: Optional[str] = "5m"
    action: Optional[str] = None  # BUY / SELL / LONG / SHORT / BULL / BEAR
    price: Optional[float] = None
    rsi: Optional[float] = None
    note: Optional[str] = None


@api.post("/webhooks/tradingview")
async def tradingview_webhook(body: TVAlertBody):
    if body.secret != TV_SECRET:
        raise HTTPException(401, "invalid secret")
    ev = {
        "ts": time.time(),
        "symbol": body.symbol,
        "timeframe": body.timeframe,
        "action": body.action,
        "price": body.price,
        "rsi": body.rsi,
        "note": body.note,
    }
    STATE.tv_events.appendleft(ev)
    # Persist last 200 to mongo (use copy so mongo's _id doesn't taint in-memory ev)
    try:
        await db.tv_events.insert_one(dict(ev))
    except Exception:
        pass
    return {"ok": True, "queued": True}


@api.get("/tv_events")
async def tv_events(user: str = Depends(verify_token)):
    events = [{k: v for k, v in e.items() if k != "_id"} for e in list(STATE.tv_events)]
    return {"events": events}


# =================== WebSocket (live state stream) ===================
@app.websocket("/api/ws/state")
async def ws_state(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            snap = STATE.snapshot()
            await ws.send_json(snap)
            await asyncio.sleep(0.5)  # 2 Hz
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws_state error: %s", e)


app.include_router(api)


# =================== Lifecycle ===================
@app.on_event("startup")
async def on_startup():
    log.info("Starting Polymarket BTC Scalper background tasks")
    asyncio.create_task(coinbase_ws_loop())
    asyncio.create_task(fetch_coinbase_candles_loop())
    asyncio.create_task(fetch_okx_derivatives_loop())
    asyncio.create_task(discover_btc_markets_loop())
    asyncio.create_task(orderbook_refresh_loop())
    asyncio.create_task(strategy_loop())
    asyncio.create_task(position_manager_loop())
    STATE.equity_curve.append({"ts": time.time(), "equity": STATE.equity})


@app.on_event("shutdown")
async def on_shutdown():
    mongo_client.close()
