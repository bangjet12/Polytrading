"""Shared in-memory runtime state for the bot."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RuntimeState:
    # market data
    spot_price: float = 0.0
    spot_last_ts: float = 0.0
    closes_5m: list[float] = field(default_factory=list)
    candles_5m: list[dict] = field(default_factory=list)  # [{t, o, h, l, c, v}]
    trade_count: int = 0
    feed_latencies_ms: deque = field(default_factory=lambda: deque(maxlen=400))
    ws_status: dict[str, str] = field(default_factory=lambda: {
        "coinbase": "disconnected",
        "okx": "idle",
        "polymarket": "idle",
    })

    # derivatives
    funding_rate: float = 0.0
    mark_price: float = 0.0
    open_interest: float = 0.0
    taker_buy_volume: float = 0.0
    taker_sell_volume: float = 0.0

    # polymarket
    markets: list[dict] = field(default_factory=list)  # discovered markets
    selected_market: Optional[dict] = None
    selected_book: dict = field(default_factory=dict)

    # strategy
    signals: dict = field(default_factory=dict)
    edge: dict = field(default_factory=dict)
    decision_loop_latencies_ms: deque = field(default_factory=lambda: deque(maxlen=400))

    # graph
    graph: dict = field(default_factory=lambda: {"nodes": [], "links": []})

    # tv webhook events log (most recent first)
    tv_events: deque = field(default_factory=lambda: deque(maxlen=100))

    # bot status
    mode: str = "paper"  # paper / live
    bot_running: bool = True
    kill_switch: bool = False

    # risk + journal
    equity: float = 1000.0
    starting_equity_today: float = 1000.0
    daily_pnl: float = 0.0
    open_positions: list[dict] = field(default_factory=list)
    trade_journal: deque = field(default_factory=lambda: deque(maxlen=500))
    equity_curve: deque = field(default_factory=lambda: deque(maxlen=500))
    trade_count_today: int = 0

    # settings
    settings: dict = field(default_factory=lambda: {
        "risk_per_trade_pct": 0.005,
        "daily_dd_halt_pct": 0.02,
        "hard_stop_pct": 0.004,
        "edge_threshold": 0.003,  # 0.3 %
        "max_edge_threshold": 0.05,  # ignore extreme edges (likely stale)
        "min_liquidity_usd": 100.0,
        "max_spread": 0.04,
        "daily_trade_cap": 200,
        "target_market_type": "any",  # any / 5m_updown / hourly_above / daily_above
        "min_minutes_to_expiry": 1,
        "max_minutes_to_expiry": 1500,
    })

    # lock for safe concurrent updates
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def snapshot(self) -> dict:
        """Return JSON-serializable snapshot for frontend."""
        # latency percentiles
        feed = sorted(self.feed_latencies_ms)
        loop = sorted(self.decision_loop_latencies_ms)

        def pct(arr, p):
            if not arr:
                return None
            idx = max(0, min(len(arr) - 1, int(len(arr) * p) - 1))
            return float(arr[idx])

        return {
            "ts": time.time(),
            "spot_price": self.spot_price,
            "spot_last_ts": self.spot_last_ts,
            "candles_5m": self.candles_5m[-200:],
            "trade_count": self.trade_count,
            "ws_status": dict(self.ws_status),
            "funding_rate": self.funding_rate,
            "mark_price": self.mark_price,
            "open_interest": self.open_interest,
            "taker_buy_volume": self.taker_buy_volume,
            "taker_sell_volume": self.taker_sell_volume,
            "markets": self.markets,
            "selected_market": self.selected_market,
            "selected_book": self.selected_book,
            "signals": self.signals,
            "edge": self.edge,
            "graph": self.graph,
            "mode": self.mode,
            "bot_running": self.bot_running,
            "kill_switch": self.kill_switch,
            "equity": self.equity,
            "starting_equity_today": self.starting_equity_today,
            "daily_pnl": self.daily_pnl,
            "open_positions": self.open_positions,
            "trade_journal": list(self.trade_journal)[-100:],
            "equity_curve": list(self.equity_curve),
            "trade_count_today": self.trade_count_today,
            "tv_events": [{k: v for k, v in e.items() if k != "_id"} for e in list(self.tv_events)],
            "settings": dict(self.settings),
            "latency": {
                "feed_p50": pct(feed, 0.5),
                "feed_p95": pct(feed, 0.95),
                "feed_p99": pct(feed, 0.99),
                "loop_p50": pct(loop, 0.5),
                "loop_p95": pct(loop, 0.95),
                "loop_p99": pct(loop, 0.99),
                "feed_n": len(feed),
                "loop_n": len(loop),
            },
        }


STATE = RuntimeState()
