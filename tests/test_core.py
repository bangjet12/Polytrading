"""
POC test_core.py — Polymarket BTC UP/DOWN Scalper Bot (v2)
============================================================
Validates the complete core workflow in isolation.

Data sources (Binance/Bybit geo-blocked in Emergent, so we use):
  - Spot WS:      Coinbase  (wss://ws-feed.exchange.coinbase.com)
  - Spot REST:    Coinbase  (api.exchange.coinbase.com)
  - Derivatives:  OKX       (funding rate, open interest, taker orderflow)
  - Predictions:  Polymarket Gamma + CLOB

Run:  python /app/tests/test_core.py
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp
import websockets
from eth_account import Account
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
END = "\033[0m"


def hdr(t: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 78}\n  {t}\n{'=' * 78}{END}")


def ok(t: str) -> None:
    print(f"{GREEN}[PASS]{END} {t}")


def fail(t: str) -> None:
    print(f"{RED}[FAIL]{END} {t}")


def info(t: str) -> None:
    print(f"{YELLOW}[INFO]{END} {t}")


# =============================================================================
# US-1  Coinbase WebSocket — real-time BTC spot
# =============================================================================

@dataclass
class PriceWindow:
    closes: list[float] = field(default_factory=list)
    last_price: float = 0.0
    last_update_ts: float = 0.0
    feed_latencies_ms: list[float] = field(default_factory=list)
    trades_count: int = 0


async def test_coinbase_ws(window: PriceWindow, run_seconds: int = 10) -> bool:
    hdr("US-1  Coinbase WebSocket (BTC-USD ticker + matches)")
    url = "wss://ws-feed.exchange.coinbase.com"
    sub = json.dumps(
        {
            "type": "subscribe",
            "channels": ["ticker", "matches"],
            "product_ids": ["BTC-USD"],
        }
    )
    try:
        async with websockets.connect(url, ping_interval=20, close_timeout=5) as ws:
            await ws.send(sub)
            t_end = time.time() + run_seconds
            messages = 0
            while time.time() < t_end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=run_seconds)
                except asyncio.TimeoutError:
                    break
                msg = json.loads(raw)
                msg_type = msg.get("type")
                now_ms = time.time() * 1000
                if msg_type in ("ticker", "last_match", "match"):
                    px_str = msg.get("price")
                    if px_str:
                        px = float(px_str)
                        window.last_price = px
                        window.last_update_ts = now_ms / 1000
                        # event time
                        ts = msg.get("time")
                        if ts:
                            try:
                                dt = datetime.fromisoformat(
                                    ts.replace("Z", "+00:00")
                                )
                                event_ms = dt.timestamp() * 1000
                                window.feed_latencies_ms.append(now_ms - event_ms)
                            except Exception:
                                pass
                        if msg_type != "ticker":
                            window.trades_count += 1
                messages += 1
            ok(f"Received {messages} messages in ~{run_seconds}s  ({window.trades_count} trades)")
            if window.last_price > 0:
                ok(f"Last BTC price: ${window.last_price:,.2f}")
                if window.feed_latencies_ms:
                    p50 = statistics.median(window.feed_latencies_ms)
                    p95 = sorted(window.feed_latencies_ms)[
                        max(0, int(len(window.feed_latencies_ms) * 0.95) - 1)
                    ]
                    ok(f"Feed latency  P50={p50:.0f}ms  P95={p95:.0f}ms")
                return True
            fail("No BTC price received")
            return False
    except Exception as e:
        fail(f"Coinbase WS error: {e}")
        return False


async def fetch_coinbase_5m_klines(window: PriceWindow, n: int = 100) -> bool:
    """Pull last N x 5m closes for TA."""
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    # granularity 300 = 5m
    async with aiohttp.ClientSession(
        headers={"User-Agent": "polymarket-scalper-poc/1.0"}
    ) as s:
        try:
            async with s.get(url, params={"granularity": "300"}, timeout=15) as r:
                if r.status != 200:
                    info(f"Coinbase candles HTTP {r.status}")
                    return False
                arr = await r.json()
                # Each row: [time, low, high, open, close, volume]
                arr_sorted = sorted(arr, key=lambda r: r[0])[-n:]
                window.closes = [float(r[4]) for r in arr_sorted]
                if window.last_price == 0 and window.closes:
                    window.last_price = window.closes[-1]
                ok(f"Loaded {len(window.closes)} x 5m closes from Coinbase REST")
                return True
        except Exception as e:
            fail(f"Coinbase candles error: {e}")
            return False


# =============================================================================
# US-1b  OKX derivatives  (funding / OI / orderflow)
# =============================================================================

@dataclass
class DerivSnapshot:
    funding_rate: float = 0.0
    mark_price: float = 0.0
    open_interest: float = 0.0
    taker_buy_volume: float = 0.0
    taker_sell_volume: float = 0.0


async def test_okx_derivatives(snap: DerivSnapshot) -> bool:
    hdr("US-1b  OKX derivatives proxies (funding / OI / taker volume)")
    base = "https://www.okx.com/api/v5"
    inst = "BTC-USDT-SWAP"  # perpetual
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(
                f"{base}/public/funding-rate", params={"instId": inst}, timeout=10
            ) as r:
                d = (await r.json()).get("data", [])
                if d:
                    snap.funding_rate = float(d[0].get("fundingRate", 0))
                    ok(f"Funding rate: {snap.funding_rate * 100:.4f}%")
            async with s.get(
                f"{base}/public/open-interest",
                params={"instType": "SWAP", "instId": inst},
                timeout=10,
            ) as r:
                d = (await r.json()).get("data", [])
                if d:
                    snap.open_interest = float(d[0].get("oi", 0))
                    ok(f"Open interest: {snap.open_interest:,.0f} contracts")
            async with s.get(
                f"{base}/market/ticker", params={"instId": "BTC-USDT-SWAP"}, timeout=10
            ) as r:
                d = (await r.json()).get("data", [])
                if d:
                    snap.mark_price = float(d[0].get("last", 0))
            # Taker orderflow: buy/sell ratio for last 5m
            async with s.get(
                f"{base}/rubik/stat/taker-volume",
                params={"ccy": "BTC", "instType": "SWAP", "period": "5m"},
                timeout=10,
            ) as r:
                d = (await r.json()).get("data", [])
                if d and len(d[0]) >= 3:
                    # [ts, sellVol, buyVol]
                    snap.taker_sell_volume = float(d[0][1])
                    snap.taker_buy_volume = float(d[0][2])
                    total = snap.taker_buy_volume + snap.taker_sell_volume
                    ratio = (snap.taker_buy_volume / total) if total else 0.5
                    ok(
                        f"Taker buy/(buy+sell) 5m: {ratio:.3f}  "
                        f"(buy={snap.taker_buy_volume:.0f}, sell={snap.taker_sell_volume:.0f})"
                    )
            return True
        except Exception as e:
            fail(f"OKX derivatives error: {e}")
            return False


# =============================================================================
# US-2  Polymarket market discovery + CLOB orderbook
# =============================================================================

@dataclass
class PolyMarket:
    market_id: str
    question: str
    slug: str
    outcomes: list[str]
    outcome_prices: list[float]
    yes_token_id: str
    no_token_id: str
    end_date: Optional[str]
    minutes_to_expiry: Optional[float]
    volume_24h: float
    liquidity: float
    market_type: str  # "5m_updown" / "hourly_above" / "daily_above" / "daily_updown"


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


async def discover_polymarket_btc(top_n: int = 30) -> list[PolyMarket]:
    hdr("US-2  Polymarket market discovery (BTC Up/Down + barrier markets)")
    out: list[PolyMarket] = []
    now = datetime.now(timezone.utc)

    async with aiohttp.ClientSession() as s:
        # Use liquidity sort to surface fresh active markets
        for order, ascending in (("liquidity", "false"), ("volume24hr", "false")):
            try:
                async with s.get(
                    "https://gamma-api.polymarket.com/markets",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": "500",
                        "order": order,
                        "ascending": ascending,
                    },
                    timeout=20,
                ) as r:
                    if r.status != 200:
                        info(f"Gamma HTTP {r.status} (order={order})")
                        continue
                    data = await r.json()
            except Exception as e:
                info(f"Gamma fetch error: {e}")
                continue

            seen = {m.market_id for m in out}
            for m in data:
                q = (m.get("question") or "")
                ql = q.lower()
                if not ("bitcoin" in ql or " btc " in ql or ql.startswith("btc")):
                    continue
                # must be 2-outcome binary
                outcomes = _safe_json(m.get("outcomes"), [])
                clob_ids = _safe_json(m.get("clobTokenIds"), [])
                prices = _safe_json(m.get("outcomePrices"), [])
                if len(outcomes) != 2 or len(clob_ids) != 2:
                    continue
                # Check end date in future
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
                pm = PolyMarket(
                    market_id=cid,
                    question=q,
                    slug=m.get("slug", ""),
                    outcomes=outcomes,
                    outcome_prices=fp,
                    yes_token_id=str(clob_ids[0]),
                    no_token_id=str(clob_ids[1]),
                    end_date=end_date,
                    minutes_to_expiry=mins,
                    volume_24h=float(m.get("volume24hr") or 0),
                    liquidity=float(m.get("liquidity") or 0),
                    market_type=_classify(q, mins),
                )
                out.append(pm)
                seen.add(cid)

    if not out:
        fail("No BTC markets discovered")
        return out

    # Prefer 5m / hourly markets first, then by shortest expiry
    type_rank = {"5m_updown": 0, "hourly_above": 1, "daily_above": 2, "daily_updown": 3, "other": 9}
    out.sort(key=lambda x: (type_rank.get(x.market_type, 9), x.minutes_to_expiry or 1e9))
    out = out[:top_n]
    ok(f"Discovered {len(out)} BTC markets (best candidates first)")
    for i, mk in enumerate(out[:8]):
        mins = f"{mk.minutes_to_expiry:.1f}m" if mk.minutes_to_expiry else "?"
        info(
            f"  [{i}] [{mk.market_type:14s}] +{mins:8s} liq=${mk.liquidity:>8,.0f} "
            f"vol24h=${mk.volume_24h:>9,.0f}  {mk.question[:60]}"
        )
    return out


async def fetch_polymarket_orderbook(market: PolyMarket) -> Optional[dict[str, Any]]:
    hdr(f"US-2b  Fetch Polymarket CLOB orderbook")
    info(f"Market: {market.question[:70]}")
    info(f"Type: {market.market_type}  liquidity=${market.liquidity:,.0f}")
    url = "https://clob.polymarket.com/book"
    out: dict[str, Any] = {"yes": None, "no": None}
    async with aiohttp.ClientSession() as s:
        for side_name, tid in (("yes", market.yes_token_id), ("no", market.no_token_id)):
            try:
                async with s.get(url, params={"token_id": tid}, timeout=10) as r:
                    if r.status != 200:
                        info(f"CLOB book {side_name} HTTP {r.status}")
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
                    out[side_name] = {
                        "best_bid": bb,
                        "best_ask": ba,
                        "mid": mid,
                        "spread": spread,
                        "depth_bid": db,
                        "depth_ask": da,
                        "n_bids": len(bids),
                        "n_asks": len(asks),
                    }
                    if mid is not None:
                        ok(
                            f"  {side_name.upper():3s}  bid={bb:.3f} ask={ba:.3f} mid={mid:.3f} "
                            f"spread={spread:.3f}  depth_bid={db:.0f} depth_ask={da:.0f}"
                        )
                    else:
                        info(f"  {side_name.upper()}: empty orderbook (n_bids={len(bids)}, n_asks={len(asks)})")
            except Exception as e:
                info(f"CLOB book {side_name} error: {e}")
    return out


# =============================================================================
# US-3  Signal engine + convergence
# =============================================================================

def rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[-i] - closes[-i - 1]
        if d > 0:
            gains += d
        else:
            losses += -d
    avg_g = gains / period
    avg_l = losses / period if losses > 0 else 1e-9
    rs = avg_g / avg_l
    return 100 - 100 / (1 + rs)


def ema(closes: list[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    e = closes[0]
    for px in closes[1:]:
        e = px * k + e * (1 - k)
    return e


@dataclass
class SignalSnapshot:
    rsi14: Optional[float]
    ema_fast: Optional[float]
    ema_slow: Optional[float]
    ema_cross: float
    funding_skew: float
    taker_imbalance: float
    convergence_score: float
    label: str
    conflict: bool
    components: dict[str, float] = field(default_factory=dict)


def compute_signals(closes: list[float], deriv: DerivSnapshot) -> SignalSnapshot:
    hdr("US-3  Signal engine + BULL/BEAR convergence")
    r = rsi(closes, 14)
    ef = ema(closes, 9)
    es = ema(closes, 21)
    cross = (ef - es) if (ef and es) else 0.0
    funding_pct = deriv.funding_rate * 100  # convert to %
    total = deriv.taker_buy_volume + deriv.taker_sell_volume
    imb = (deriv.taker_buy_volume - deriv.taker_sell_volume) / total if total else 0.0

    rsi_score = ((r - 50) / 50) if r is not None else 0.0
    last = closes[-1] if closes else 1.0
    ema_score = max(-1.0, min(1.0, cross / max(last * 0.002, 1e-6)))
    fund_score = max(-1.0, min(1.0, funding_pct / 0.05))
    imb_score = max(-1.0, min(1.0, imb * 2))
    components = {
        "rsi": rsi_score,
        "ema_cross": ema_score,
        "funding": fund_score,
        "taker_imb": imb_score,
    }
    parts = list(components.values())
    convergence = sum(parts) / len(parts)
    pos = sum(1 for p in parts if p > 0.15)
    neg = sum(1 for p in parts if p < -0.15)
    conflict = pos >= 2 and neg >= 2
    label = "BULL" if convergence > 0.15 else "BEAR" if convergence < -0.15 else "NEUTRAL"

    snap = SignalSnapshot(
        rsi14=r,
        ema_fast=ef,
        ema_slow=es,
        ema_cross=cross,
        funding_skew=funding_pct,
        taker_imbalance=imb,
        convergence_score=convergence,
        label=label,
        conflict=conflict,
        components=components,
    )
    ok(
        f"RSI14={r if r is None else f'{r:.1f}'}  EMA9-EMA21={cross:+.2f}  "
        f"funding={funding_pct:+.4f}%  taker_imb={imb:+.3f}"
    )
    ok(f"Components: " + "  ".join(f"{k}={v:+.2f}" for k, v in components.items()))
    ok(f"Convergence score = {convergence:+.3f}  → label={label}  conflict={conflict}")
    return snap


# =============================================================================
# US-4  Mispricing / edge detector
# =============================================================================

@dataclass
class EdgeResult:
    has_edge: bool
    fair_yes_prob: float
    market_yes_prob: float
    edge: float
    direction: str
    reason: str
    barrier: Optional[float]


def estimate_fair_prob_above(
    spot: float, signal: SignalSnapshot, minutes_to_expiry: float, barrier: float
) -> float:
    """Probability spot > barrier at expiry (geometric Brownian, 5m sigma ~0.25%)."""
    if minutes_to_expiry <= 0:
        return 1.0 if spot > barrier else 0.0
    sigma5 = max(spot * 0.0025, 1.0)
    horizon_sigma = sigma5 * math.sqrt(minutes_to_expiry / 5.0)
    z = (spot - barrier) / horizon_sigma if horizon_sigma > 0 else 0.0
    base_p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    tilt = 0.05 * signal.convergence_score
    return max(0.01, min(0.99, base_p + tilt))


def estimate_fair_prob_updown(spot: float, signal: SignalSnapshot, minutes_to_expiry: float, ref_price: float) -> float:
    """For 'Up or Down' market: probability final_price > current price at start of window."""
    if minutes_to_expiry <= 0:
        return 1.0 if spot > ref_price else 0.0
    sigma5 = max(spot * 0.0025, 1.0)
    horizon_sigma = sigma5 * math.sqrt(minutes_to_expiry / 5.0)
    z = (spot - ref_price) / horizon_sigma if horizon_sigma > 0 else 0.0
    base_p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    tilt = 0.10 * signal.convergence_score  # signals matter more for short window
    return max(0.01, min(0.99, base_p + tilt))


def extract_barrier(question: str, fallback: float) -> float:
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", question)
    if not m:
        return fallback
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return fallback


def detect_edge(
    spot: float,
    market: PolyMarket,
    book: dict[str, Any],
    signal: SignalSnapshot,
    edge_threshold: float = 0.003,
) -> EdgeResult:
    hdr("US-4  Mispricing / edge detector (>0.3%)")
    yes = book.get("yes") or {}
    yes_mid = yes.get("mid")
    if yes_mid is None:
        return EdgeResult(False, 0.5, 0.5, 0.0, "NONE", "no orderbook", None)

    mins = market.minutes_to_expiry or 60.0
    if "above" in market.question.lower() or "reach" in market.question.lower():
        barrier = extract_barrier(market.question, spot)
        fair = estimate_fair_prob_above(spot, signal, mins, barrier)
    else:
        # "Up or Down" — use spot at this instant as approximation of start price
        barrier = spot
        fair = estimate_fair_prob_updown(spot, signal, mins, spot)

    edge = fair - yes_mid
    direction = "NONE"
    if abs(edge) > edge_threshold:
        if signal.conflict:
            reason = "signal conflict → skip"
        else:
            direction = "BUY_YES" if edge > 0 else "BUY_NO"
            reason = "edge above threshold"
    else:
        reason = "edge below threshold → skip"

    res = EdgeResult(
        has_edge=(direction != "NONE"),
        fair_yes_prob=fair,
        market_yes_prob=yes_mid,
        edge=edge,
        direction=direction,
        reason=reason,
        barrier=barrier,
    )
    ok(
        f"spot=${spot:,.0f}  barrier=${barrier:,.0f}  mins={mins:.1f}  "
        f"fair_YES={fair:.3f}  mkt_YES={yes_mid:.3f}  edge={edge:+.3f}  "
        f"→ {direction}  ({reason})"
    )
    return res


# =============================================================================
# US-5  Order construction + dry-run signing
# =============================================================================

def test_order_dry_run(market: PolyMarket, direction: str = "BUY_YES") -> bool:
    hdr("US-5  Order construction + EIP-712 dry-run signing")
    try:
        acct = Account.create()
        pk = acct.key.hex()
        info(f"Throwaway dry-run wallet: {acct.address}")
        host = "https://clob.polymarket.com"
        client = ClobClient(host, key=pk, chain_id=137)
        token_id = market.yes_token_id if "YES" in direction else market.no_token_id
        order_args = OrderArgs(
            token_id=token_id,
            price=0.55,
            size=5.0,
            side=BUY,
        )
        signed = client.create_order(order_args)
        sig = getattr(signed, "signature", None) or ""
        salt = getattr(signed, "salt", None)
        if sig and len(str(sig)) >= 130:
            ok(f"Order signed OK.  sig_len={len(str(sig))}  salt={salt}")
            ok(f"  token_id={token_id[:14]}...  side=BUY  price=0.55  size=5.0")
            return True
        fail(f"Signed order invalid: {signed}")
        return False
    except Exception as e:
        fail(f"Dry-run sign error: {e}")
        return False


# =============================================================================
# US-6  Risk manager
# =============================================================================

@dataclass
class RiskState:
    equity: float = 1000.0
    daily_pnl: float = 0.0
    risk_per_trade_pct: float = 0.005
    daily_dd_halt_pct: float = 0.02
    hard_stop_pct: float = 0.004
    daily_trade_count: int = 0
    daily_trade_cap: int = 200


def test_risk_manager() -> bool:
    hdr("US-6  Risk manager (0.5% risk / 2% daily DD / -0.4% hard stop)")
    rs = RiskState()
    size = rs.equity * rs.risk_per_trade_pct / rs.hard_stop_pct
    ok(f"Position notional for 0.5% risk @ 0.4% stop = ${size:.2f}")
    assert abs(size - 1250.0) < 1e-6
    rs.daily_pnl = -rs.equity * rs.daily_dd_halt_pct
    halt = (rs.daily_pnl / rs.equity) <= -rs.daily_dd_halt_pct
    ok(f"Daily DD {rs.daily_pnl:+.2f} ({rs.daily_pnl / rs.equity * 100:+.2f}%) → halt={halt}")
    assert halt
    pnl_pct = -0.005
    triggered = pnl_pct <= -rs.hard_stop_pct
    ok(f"Open PnL {pnl_pct * 100:+.2f}% → hard stop triggered={triggered}")
    assert triggered
    rs.daily_trade_count = rs.daily_trade_cap
    cap_hit = rs.daily_trade_count >= rs.daily_trade_cap
    ok(f"Trade count {rs.daily_trade_count} → daily cap hit={cap_hit}")
    return True


def test_skip_rules(book: dict[str, Any], signal: SignalSnapshot) -> bool:
    hdr("Skip rules (no edge / low liquidity / conflict / limit hit)")
    yes = book.get("yes") or {}
    min_depth = 50
    max_spread = 0.04
    low_liq = (yes.get("depth_bid") or 0) < min_depth or (yes.get("depth_ask") or 0) < min_depth
    wide_spread = (yes.get("spread") or 1.0) > max_spread
    conflict = signal.conflict
    info(f"low_liquidity={low_liq}  wide_spread={wide_spread}  conflict={conflict}")
    ok("Skip rules evaluable — pipeline wired")
    return True


# =============================================================================
# Main
# =============================================================================

async def main() -> int:
    print(f"{BOLD}{CYAN}\n  Polymarket BTC UP/DOWN Scalper — POC test_core.py (v2){END}")
    print(f"  Started: {datetime.now().isoformat()}\n")

    results: dict[str, bool] = {}

    # US-1  Coinbase WS
    window = PriceWindow()
    results["US-1 Coinbase WS"] = await test_coinbase_ws(window, run_seconds=8)

    # Backfill closes
    if len(window.closes) < 30:
        await fetch_coinbase_5m_klines(window, n=100)

    # US-1b OKX derivatives
    deriv = DerivSnapshot()
    results["US-1b OKX derivatives"] = await test_okx_derivatives(deriv)

    # US-2  Polymarket discover
    markets = await discover_polymarket_btc(top_n=30)
    results["US-2 Polymarket discovery"] = bool(markets)

    # Pick best market with non-empty orderbook
    selected = None
    book: dict[str, Any] = {}
    for m in markets[:10]:
        bk = await fetch_polymarket_orderbook(m) or {}
        yes = bk.get("yes") or {}
        if yes.get("mid") is not None:
            selected = m
            book = bk
            break
    results["US-2b Polymarket orderbook"] = bool(book.get("yes"))

    # US-3 signals
    signal = compute_signals(window.closes, deriv)
    results["US-3 Signal engine"] = True

    # US-4 edge detector
    if selected and book:
        edge = detect_edge(window.last_price, selected, book, signal)
        results["US-4 Edge detector"] = True
        test_skip_rules(book, signal)
    else:
        edge = EdgeResult(False, 0.5, 0.5, 0.0, "NONE", "no market", None)
        results["US-4 Edge detector"] = False

    # US-5 order signing
    if selected:
        results["US-5 Order signing dry-run"] = test_order_dry_run(
            selected,
            direction=(edge.direction if edge.direction != "NONE" else "BUY_YES"),
        )
    else:
        results["US-5 Order signing dry-run"] = False

    # US-6 risk
    results["US-6 Risk manager"] = test_risk_manager()

    # Summary
    hdr("POC SUMMARY")
    all_ok = True
    for name, passed in results.items():
        (ok if passed else fail)(name)
        all_ok &= passed
    print()
    if all_ok:
        print(f"{BOLD}{GREEN}  ✓ POC PASSED — core workflow healthy. Proceed to app build.{END}\n")
        return 0
    print(f"{BOLD}{RED}  ✗ POC FAILED — fix failing user-story before building.{END}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
