"""Market data: Coinbase WS + REST + OKX derivatives."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime

import aiohttp
import websockets

from .state import STATE

log = logging.getLogger("market_data")

COINBASE_WS = "wss://ws-feed.exchange.coinbase.com"
COINBASE_REST = "https://api.exchange.coinbase.com"
OKX_REST = "https://www.okx.com/api/v5"


async def coinbase_ws_loop():
    sub = json.dumps({
        "type": "subscribe",
        "channels": ["ticker", "matches"],
        "product_ids": ["BTC-USD"],
    })
    while True:
        try:
            STATE.ws_status["coinbase"] = "connecting"
            async with websockets.connect(
                COINBASE_WS, ping_interval=20, close_timeout=5
            ) as ws:
                await ws.send(sub)
                STATE.ws_status["coinbase"] = "connected"
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    msg = json.loads(raw)
                    t = msg.get("type")
                    if t not in ("ticker", "last_match", "match"):
                        continue
                    px_str = msg.get("price")
                    if not px_str:
                        continue
                    now_ms = time.time() * 1000
                    try:
                        STATE.spot_price = float(px_str)
                        STATE.spot_last_ts = now_ms / 1000
                    except Exception:
                        continue
                    ts_str = msg.get("time")
                    if ts_str:
                        try:
                            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            STATE.feed_latencies_ms.append(now_ms - dt.timestamp() * 1000)
                        except Exception:
                            pass
                    if t in ("match", "last_match"):
                        STATE.trade_count += 1
        except Exception as e:
            STATE.ws_status["coinbase"] = "error"
            log.warning("coinbase ws error: %s — reconnect in 3s", e)
            await asyncio.sleep(3)


async def fetch_coinbase_candles_loop():
    """Pull 5m candles every 30s."""
    async with aiohttp.ClientSession(headers={"User-Agent": "polymarket-scalper/1.0"}) as s:
        while True:
            try:
                async with s.get(
                    f"{COINBASE_REST}/products/BTC-USD/candles",
                    params={"granularity": "300"},
                    timeout=15,
                ) as r:
                    if r.status == 200:
                        arr = await r.json()
                        # each: [time, low, high, open, close, volume]
                        arr_sorted = sorted(arr, key=lambda x: x[0])
                        candles = [
                            {
                                "t": int(x[0]),
                                "l": float(x[1]),
                                "h": float(x[2]),
                                "o": float(x[3]),
                                "c": float(x[4]),
                                "v": float(x[5]),
                            }
                            for x in arr_sorted
                        ]
                        STATE.candles_5m = candles
                        STATE.closes_5m = [c["c"] for c in candles]
            except Exception as e:
                log.warning("coinbase candles error: %s", e)
            await asyncio.sleep(30)


async def fetch_okx_derivatives_loop():
    inst = "BTC-USDT-SWAP"
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                STATE.ws_status["okx"] = "polling"
                # funding
                async with s.get(
                    f"{OKX_REST}/public/funding-rate", params={"instId": inst}, timeout=10
                ) as r:
                    d = (await r.json()).get("data", [])
                    if d:
                        STATE.funding_rate = float(d[0].get("fundingRate", 0))
                # OI
                async with s.get(
                    f"{OKX_REST}/public/open-interest",
                    params={"instType": "SWAP", "instId": inst},
                    timeout=10,
                ) as r:
                    d = (await r.json()).get("data", [])
                    if d:
                        STATE.open_interest = float(d[0].get("oi", 0))
                # mark / last price
                async with s.get(
                    f"{OKX_REST}/market/ticker", params={"instId": inst}, timeout=10
                ) as r:
                    d = (await r.json()).get("data", [])
                    if d:
                        STATE.mark_price = float(d[0].get("last", 0))
                # Taker buy/sell volume
                async with s.get(
                    f"{OKX_REST}/rubik/stat/taker-volume",
                    params={"ccy": "BTC", "instType": "SWAP", "period": "5m"},
                    timeout=10,
                ) as r:
                    d = (await r.json()).get("data", [])
                    if d and len(d[0]) >= 3:
                        STATE.taker_sell_volume = float(d[0][1])
                        STATE.taker_buy_volume = float(d[0][2])
                STATE.ws_status["okx"] = "connected"
            except Exception as e:
                STATE.ws_status["okx"] = "error"
                log.warning("okx derivatives error: %s", e)
            await asyncio.sleep(15)
