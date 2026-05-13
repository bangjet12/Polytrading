"""Risk manager: sizing, daily DD halt, hard stop, daily cap, skip rules."""
from __future__ import annotations

from .state import STATE


def position_size_usd() -> float:
    s = STATE.settings
    return STATE.equity * s["risk_per_trade_pct"] / max(s["hard_stop_pct"], 1e-6)


def daily_dd_halted() -> bool:
    s = STATE.settings
    if STATE.starting_equity_today <= 0:
        return False
    return (STATE.daily_pnl / STATE.starting_equity_today) <= -s["daily_dd_halt_pct"]


def daily_cap_reached() -> bool:
    return STATE.trade_count_today >= STATE.settings["daily_trade_cap"]


def skip_reasons(book: dict, signal: dict, edge: dict) -> list[str]:
    reasons: list[str] = []
    s = STATE.settings
    yes = (book or {}).get("yes") or {}
    no = (book or {}).get("no") or {}
    edge_type = edge.get("edge_type", "model")
    if not edge.get("has_edge"):
        reasons.append("no_edge")
    if signal.get("conflict") and edge_type != "lag":
        # Lag-based edges are price-action driven; signal conflict still allows trade
        reasons.append("signal_conflict")
    if (yes.get("depth_bid") or 0) < s["min_liquidity_usd"] or (yes.get("depth_ask") or 0) < s["min_liquidity_usd"]:
        reasons.append("low_liquidity")
    if (yes.get("spread") or 1.0) > s["max_spread"]:
        reasons.append("wide_spread")
    # edge_too_large only applies to model-based edges; lag edges are small by construction
    if edge_type == "model" and abs(edge.get("edge", 0)) > s["max_edge_threshold"]:
        reasons.append("edge_too_large")
    if daily_dd_halted():
        reasons.append("daily_dd_halt")
    if daily_cap_reached():
        reasons.append("daily_cap_reached")
    if STATE.kill_switch:
        reasons.append("kill_switch")
    if not STATE.bot_running:
        reasons.append("bot_paused")
    return reasons
