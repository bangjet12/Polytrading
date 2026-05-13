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
        # Polymarket "BTC Up or Down 5m" markets always have ~5 min windows
        if minutes is not None and minutes <= 6:
            return "5m_updown"
        return "daily_updown"
    if "above" in q or "reach" in q:
        if minutes is not None and minutes < 90:
            return "hourly_above"
        return "daily_above"
    return "other"


async def discover_btc_markets_loop():
    """Refresh BTC market list every 15s using Polymarket events endpoint.

    Uses /events?tag_slug=bitcoin which surfaces the LIVE 5-minute
    'Bitcoin Up or Down' markets that the regular /markets endpoint misses.
    """
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                STATE.ws_status["polymarket"] = "polling"
                seen: set[str] = set()
                merged: list[dict] = []
                now = datetime.now(timezone.utc)

                # 1) Primary: events endpoint with tag_slug=bitcoin (finds 5m markets)
                try:
                    async with s.get(
                        f"{GAMMA}/events",
                        params={
                            "closed": "false",
                            "limit": "500",
                            "tag_slug": "bitcoin",
                        },
                        timeout=20,
                    ) as r:
                        if r.status == 200:
                            evts = await r.json()
                        else:
                            evts = []
                except Exception:
                    evts = []

                for e in evts if isinstance(evts, list) else []:
                    title = (e.get("title") or "")
                    tl = title.lower()
                    if "bitcoin" not in tl and "btc" not in tl:
                        continue
                    end_date = e.get("endDate")
                    mins = None
                    if end_date:
                        try:
                            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                            mins = (end_dt - now).total_seconds() / 60.0
                            if mins <= 0:
                                continue
                        except Exception:
                            pass
                    # each event has 1 underlying market
                    mks = e.get("markets") or []
                    if not mks:
                        continue
                    m = mks[0]
                    if not m.get("acceptingOrders", True):
                        continue
                    outcomes = _safe_json(m.get("outcomes"), [])
                    clob_ids = _safe_json(m.get("clobTokenIds"), [])
                    prices = _safe_json(m.get("outcomePrices"), [])
                    if len(outcomes) != 2 or len(clob_ids) != 2:
                        continue
                    try:
                        fp = [float(x) for x in prices] if prices else [0.5, 0.5]
                    except Exception:
                        fp = [0.5, 0.5]
                    cid = m.get("conditionId") or m.get("id") or e.get("id") or ""
                    if not cid or cid in seen:
                        continue
                    q = title
                    merged.append({
                        "market_id": cid,
                        "question": q,
                        "slug": e.get("slug", "") or m.get("slug", ""),
                        "outcomes": outcomes,
                        "outcome_prices": fp,
                        "yes_token_id": str(clob_ids[0]),
                        "no_token_id": str(clob_ids[1]),
                        "end_date": end_date,
                        "minutes_to_expiry": mins,
                        "volume_24h": float(m.get("volume24hr") or m.get("volume24Hr") or 0),
                        "liquidity": float(m.get("liquidity") or 0),
                        "market_type": _classify(q, mins),
                    })
                    seen.add(cid)

                # 2) Supplement: /markets endpoint for daily/hourly above/reach markets
                for order, asc in (("liquidity", "false"), ("volume24hr", "false")):
                    try:
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
                    except Exception:
                        continue
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
                STATE.markets = merged[:120]
                STATE.ws_status["polymarket"] = "connected"
            except Exception as e:
                STATE.ws_status["polymarket"] = "error"
                log.warning("discover error: %s", e)
            await asyncio.sleep(15)


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


def _pick_next_5m_market(now_ts: float) -> Optional[dict]:
    """Pick the next 'BTC Up or Down 5m' market with end_date > now + 30s.

    Strategy:
      1. Among 5m_updown markets, prefer one whose START_TS (=end-5min) is in the past
         OR within the next ~10s (so we're trading the CURRENT live window).
      2. Otherwise pick the soonest-ending one.
    """
    candidates: list[tuple[float, dict]] = []
    for m in STATE.markets:
        if m.get("market_type") != "5m_updown":
            continue
        mins = m.get("minutes_to_expiry")
        if mins is None or mins <= 0.4:  # too close to expiry, don't enter
            continue
        end_str = m.get("end_date")
        if not end_str:
            continue
        try:
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except Exception:
            continue
        end_ts = end_dt.timestamp()
        # We need at least 1 minute of trading window left to make a play
        if end_ts - now_ts < 60:
            continue
        candidates.append((end_ts, m))
    if not candidates:
        return None
    # earliest expiring among "fresh enough" markets => the LIVE current window
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _capture_target(market: dict, spot: float) -> None:
    """Snapshot the BTC spot price as the 'target' when we first see this market.

    For 'BTC Up or Down 5m', YES wins if final price > target.
    """
    mid = market.get("market_id")
    if not mid or mid in STATE.market_refs:
        return
    if spot <= 0:
        return
    end_str = market.get("end_date") or ""
    end_ts = 0.0
    try:
        end_ts = datetime.fromisoformat(end_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        pass
    STATE.market_refs[mid] = {
        "target_price": float(spot),
        "captured_ts": time.time(),
        "end_ts": end_ts,
        "question": market.get("question", "")[:80],
    }
    log.info(
        "captured target for %s: $%.2f (ends in %.1fs)",
        market.get("question", "")[:50],
        spot,
        end_ts - time.time() if end_ts else 0,
    )


async def orderbook_refresh_loop():
    """Continuously refresh the orderbook of the currently selected market, and
    auto-cycle to the next 5m market when needed (if strict_5m_only=True).
    """
    while True:
        try:
            now_ts = time.time()
            mkt = STATE.selected_market
            mkt_ended = False
            if mkt and mkt.get("end_date"):
                try:
                    end_dt = datetime.fromisoformat(
                        mkt["end_date"].replace("Z", "+00:00")
                    )
                    mkt_ended = end_dt.timestamp() - now_ts < 30  # within 30s of expiry
                except Exception:
                    pass

            # Auto-cycle when in strict mode and either nothing selected or current is ending
            if STATE.strict_5m_only and (mkt is None or mkt_ended or mkt.get("market_type") != "5m_updown"):
                nxt = _pick_next_5m_market(now_ts)
                if nxt and (mkt is None or nxt.get("market_id") != mkt.get("market_id")):
                    STATE.selected_market = nxt
                    STATE.selected_book = {}
                    log.info("auto-cycled to next 5m market: %s", nxt.get("question", "")[:60])
                elif nxt is None:
                    # No 5m available — wait. Clear selection so UI shows idle.
                    if mkt_ended:
                        STATE.selected_market = None
                        STATE.selected_book = {}
                    await asyncio.sleep(2)
                    continue

            mkt = STATE.selected_market
            if not mkt:
                await asyncio.sleep(2)
                continue

            # Capture target price snapshot if not yet
            if STATE.spot_price > 0:
                _capture_target(mkt, STATE.spot_price)

            book = await fetch_orderbook(mkt)
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
