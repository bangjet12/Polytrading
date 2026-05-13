"""Polymarket Gamma discovery + CLOB orderbook fetch + (live) order signing."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from .state import STATE

log = logging.getLogger("polymarket")

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def _safe_json(raw: Any, default: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return default
    return raw if raw is not None else default


def _classify(question: str, minutes: Optional[float]) -> str:
    q = (question or "").lower()
    if "up or down" in q:
        if minutes is not None and minutes < 30:
            return "5m_updown"
        return "daily_updown"
    if "above" in q or "reach" in q:
        if minutes is not None and minutes < 90:
            return "hourly_above"
        return "daily_above"
    return "other"


async def discover_btc_markets_loop():
    """Refresh BTC market list every 30s."""
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                STATE.ws_status["polymarket"] = "polling"
                seen: set[str] = set()
                merged: list[dict] = []
                now = datetime.now(timezone.utc)
                for order, asc in (("liquidity", "false"), ("volume24hr", "false")):
                    async with s.get(
                        f"{GAMMA}/markets",
                        params={
                            "active": "true",
                            "closed": "false",
                            "limit": "500",
                            "order": order,
                            "ascending": asc,
                        },
                        timeout=20,
                    ) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                    for m in data:
                        q = (m.get("question") or "")
                        ql = q.lower()
                        if not ("bitcoin" in ql or " btc " in ql or ql.startswith("btc")):
                            continue
                        outcomes = _safe_json(m.get("outcomes"), [])
                        clob_ids = _safe_json(m.get("clobTokenIds"), [])
                        prices = _safe_json(m.get("outcomePrices"), [])
                        if len(outcomes) != 2 or len(clob_ids) != 2:
                            continue
                        end_date = m.get("endDate")
                        mins = None
                        if end_date:
                            try:
                                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                                mins = (end_dt - now).total_seconds() / 60.0
                                if mins <= 0:
                                    continue
                            except Exception:
                                pass
                        cid = m.get("conditionId") or m.get("id") or ""
                        if cid in seen:
                            continue
                        try:
                            fp = [float(x) for x in prices] if prices else [0.5, 0.5]
                        except Exception:
                            fp = [0.5, 0.5]
                        merged.append({
                            "market_id": cid,
                            "question": q,
                            "slug": m.get("slug", ""),
                            "outcomes": outcomes,
                            "outcome_prices": fp,
                            "yes_token_id": str(clob_ids[0]),
                            "no_token_id": str(clob_ids[1]),
                            "end_date": end_date,
                            "minutes_to_expiry": mins,
                            "volume_24h": float(m.get("volume24hr") or 0),
                            "liquidity": float(m.get("liquidity") or 0),
                            "market_type": _classify(q, mins),
                        })
                        seen.add(cid)
                rank = {"5m_updown": 0, "hourly_above": 1, "daily_above": 2, "daily_updown": 3, "other": 9}
                merged.sort(key=lambda x: (rank.get(x["market_type"], 9), x.get("minutes_to_expiry") or 1e9))
                STATE.markets = merged[:60]
                STATE.ws_status["polymarket"] = "connected"
            except Exception as e:
                STATE.ws_status["polymarket"] = "error"
                log.warning("discover error: %s", e)
            await asyncio.sleep(30)


async def fetch_orderbook(market: dict) -> dict:
    out: dict[str, Any] = {"yes": None, "no": None}
    async with aiohttp.ClientSession() as s:
        for side, tid in (("yes", market["yes_token_id"]), ("no", market["no_token_id"])):
            try:
                async with s.get(f"{CLOB}/book", params={"token_id": tid}, timeout=10) as r:
                    if r.status != 200:
                        continue
                    book = await r.json()
                    bids = book.get("bids", []) or []
                    asks = book.get("asks", []) or []
                    bb = max((float(b["price"]) for b in bids), default=None)
                    ba = min((float(a["price"]) for a in asks), default=None)
                    mid = (bb + ba) / 2 if (bb is not None and ba is not None) else None
                    spread = (ba - bb) if (bb is not None and ba is not None) else None
                    db = sum(float(b["size"]) for b in bids)
                    da = sum(float(a["size"]) for a in asks)
                    out[side] = {
                        "best_bid": bb,
                        "best_ask": ba,
                        "mid": mid,
                        "spread": spread,
                        "depth_bid": db,
                        "depth_ask": da,
                        "n_bids": len(bids),
                        "n_asks": len(asks),
                        "bids": [[float(b["price"]), float(b["size"])] for b in bids[:15]],
                        "asks": [[float(a["price"]), float(a["size"])] for a in asks[:15]],
                    }
            except Exception:
                continue
    return out


async def orderbook_refresh_loop():
    """Continuously refresh the orderbook of the currently selected market."""
    while True:
        try:
            mkt = STATE.selected_market
            if not mkt:
                # auto-select best market
                if STATE.markets:
                    STATE.selected_market = STATE.markets[0]
                else:
                    await asyncio.sleep(2)
                    continue
            book = await fetch_orderbook(STATE.selected_market)
            STATE.selected_book = book
        except Exception as e:
            log.warning("book refresh error: %s", e)
        await asyncio.sleep(1.0)


# ============== LIVE order placement ==============
async def place_live_order(market: dict, direction: str, price: float, size: float) -> dict:
    """
    Place a real signed order via py-clob-client.
    Requires env: POLY_PRIVATE_KEY, POLY_FUNDER_ADDRESS, POLY_API_KEY, POLY_API_SECRET, POLY_API_PASSPHRASE.
    Returns {ok, order_id?, error?, latency_ms}
    """
    t0 = time.time()
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import OrderArgs, ApiCreds, OrderType
        from py_clob_client.order_builder.constants import BUY
    except Exception as e:
        return {"ok": False, "error": f"py-clob-client import failed: {e}", "latency_ms": 0}

    pk = os.environ.get("POLY_PRIVATE_KEY") or ""
    funder = os.environ.get("POLY_FUNDER_ADDRESS") or ""
    api_key = os.environ.get("POLY_API_KEY") or ""
    api_secret = os.environ.get("POLY_API_SECRET") or ""
    passphrase = os.environ.get("POLY_API_PASSPHRASE") or ""
    if not pk:
        return {"ok": False, "error": "POLY_PRIVATE_KEY missing", "latency_ms": 0}
    try:
        # signature_type=2 is for proxy wallet funder (matic safe / browser wallet)
        # signature_type=0 is EOA
        kwargs = {"key": pk, "chain_id": 137}
        if funder:
            kwargs["signature_type"] = 2
            kwargs["funder"] = funder
        if api_key and api_secret and passphrase:
            kwargs["creds"] = ApiCreds(
                api_key=api_key, api_secret=api_secret, api_passphrase=passphrase
            )
        client = ClobClient(CLOB, **kwargs)
        token_id = market["yes_token_id"] if "YES" in direction else market["no_token_id"]
        order_args = OrderArgs(token_id=token_id, price=float(price), size=float(size), side=BUY)
        signed = client.create_order(order_args)
        resp = client.post_order(signed, OrderType.GTC)
        return {"ok": True, "order_id": resp.get("orderID") or resp.get("id"), "resp": resp,
                "latency_ms": (time.time() - t0) * 1000}
    except Exception as e:
        return {"ok": False, "error": str(e), "latency_ms": (time.time() - t0) * 1000}
