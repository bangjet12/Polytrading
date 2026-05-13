"""Main strategy loop: signals → edge → skip rules → execution (paper or live)."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from .state import STATE
from .strategy import compute_signals, detect_edge, build_graph
from .risk import position_size_usd, skip_reasons
from .polymarket import place_live_order

log = logging.getLogger("runtime")


def _paper_execute(market: dict, direction: str, price: float, size_tokens: float) -> dict:
    """Simulate fill at mid price ± half-spread (slippage)."""
    yes = (STATE.selected_book or {}).get("yes") or {}
    ask = yes.get("best_ask") or price
    bid = yes.get("best_bid") or price
    fill_price = ask if direction == "BUY_YES" else (1 - bid)  # if BUY_NO, NO ask ~ 1 - YES_bid
    pos = {
        "id": str(uuid.uuid4()),
        "market_id": market.get("market_id"),
        "market_question": market.get("question"),
        "direction": direction,
        "entry_price": float(fill_price),
        "size_tokens": float(size_tokens),
        "size_usd": float(fill_price * size_tokens),
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "mode": "paper",
    }
    return pos


async def strategy_loop():
    """Run signal+edge detection every ~300ms, execute when edge & no skip."""
    while True:
        t0 = time.time()
        try:
            # 1. signals
            deriv = {
                "funding_rate": STATE.funding_rate,
                "taker_buy_volume": STATE.taker_buy_volume,
                "taker_sell_volume": STATE.taker_sell_volume,
                "open_interest": STATE.open_interest,
            }
            sig = compute_signals(STATE.closes_5m, deriv)
            STATE.signals = sig

            # 2. edge
            mkt = STATE.selected_market
            book = STATE.selected_book or {}
            edge_threshold = STATE.settings["edge_threshold"]
            edge = detect_edge(STATE.spot_price, mkt or {}, book, sig, edge_threshold)
            edge["timestamp"] = time.time()
            STATE.edge = edge

            # 3. graph
            STATE.graph = build_graph(STATE.markets, sig, edge)

            # 4. evaluate skip rules
            skips = skip_reasons(book, sig, edge)
            edge["skip_reasons"] = skips

            # 5. execute if edge & no skip & not already in a position on this market
            already = any(
                p["market_id"] == (mkt or {}).get("market_id") and p.get("status") == "open"
                for p in STATE.open_positions
            )
            if edge.get("has_edge") and not skips and mkt and not already:
                yes = book.get("yes") or {}
                target_price = (
                    yes.get("best_ask") if edge["direction"] == "BUY_YES"
                    else (yes.get("best_bid") or 0)
                )
                if target_price and target_price > 0:
                    notional = position_size_usd()
                    # bound by depth on the side we cross
                    side_depth_size = (
                        (yes.get("depth_ask") or 0) if edge["direction"] == "BUY_YES"
                        else (yes.get("depth_bid") or 0)
                    )
                    max_tokens = max(1.0, min(side_depth_size, notional / max(target_price, 0.01)))
                    size_tokens = min(max_tokens, notional / target_price)
                    if STATE.mode == "live":
                        live_res = await place_live_order(mkt, edge["direction"], target_price, size_tokens)
                        pos = {
                            "id": str(uuid.uuid4()),
                            "market_id": mkt.get("market_id"),
                            "market_question": mkt.get("question"),
                            "direction": edge["direction"],
                            "entry_price": float(target_price),
                            "size_tokens": float(size_tokens),
                            "size_usd": float(target_price * size_tokens),
                            "opened_at": datetime.now(timezone.utc).isoformat(),
                            "status": "open" if live_res.get("ok") else "failed",
                            "mode": "live",
                            "order_id": live_res.get("order_id"),
                            "error": live_res.get("error"),
                            "latency_ms": live_res.get("latency_ms"),
                        }
                    else:
                        pos = _paper_execute(mkt, edge["direction"], target_price, size_tokens)

                    STATE.open_positions.append(pos)
                    STATE.trade_count_today += 1
                    STATE.trade_journal.append({
                        "ts": time.time(),
                        "event": "open",
                        "position": pos,
                        "edge": edge,
                        "signal_label": sig.get("label"),
                    })
        except Exception as e:
            log.exception("strategy loop error: %s", e)
        finally:
            dt = (time.time() - t0) * 1000
            STATE.decision_loop_latencies_ms.append(dt)
        # ~300ms cadence
        await asyncio.sleep(0.3)


async def position_manager_loop():
    """Mark-to-market open positions, apply hard stop, daily DD halt."""
    while True:
        try:
            book = STATE.selected_book or {}
            yes = book.get("yes") or {}
            no = book.get("no") or {}
            current_yes_mid = yes.get("mid")
            current_no_mid = no.get("mid")
            for pos in list(STATE.open_positions):
                if pos.get("status") != "open":
                    continue
                if pos["market_id"] != (STATE.selected_market or {}).get("market_id"):
                    continue  # only mark when we have its book
                exit_p = current_yes_mid if pos["direction"] == "BUY_YES" else current_no_mid
                if exit_p is None:
                    continue
                pnl = (exit_p - pos["entry_price"]) * pos["size_tokens"]
                pnl_pct = (exit_p - pos["entry_price"]) / max(pos["entry_price"], 1e-6)
                pos["current_price"] = float(exit_p)
                pos["unrealized_pnl"] = float(pnl)
                pos["unrealized_pnl_pct"] = float(pnl_pct)
                # hard stop -0.4%
                if pnl_pct <= -STATE.settings["hard_stop_pct"]:
                    pos["status"] = "closed_stop"
                    pos["exit_price"] = float(exit_p)
                    pos["realized_pnl"] = float(pnl)
                    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                    STATE.daily_pnl += pnl
                    STATE.equity += pnl
                    STATE.equity_curve.append({"ts": time.time(), "equity": STATE.equity})
                    STATE.trade_journal.append({"ts": time.time(), "event": "hard_stop", "position": pos})
                # take profit at >= 0.6% (within target 0.3-0.8%)
                elif pnl_pct >= 0.006:
                    pos["status"] = "closed_tp"
                    pos["exit_price"] = float(exit_p)
                    pos["realized_pnl"] = float(pnl)
                    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                    STATE.daily_pnl += pnl
                    STATE.equity += pnl
                    STATE.equity_curve.append({"ts": time.time(), "equity": STATE.equity})
                    STATE.trade_journal.append({"ts": time.time(), "event": "take_profit", "position": pos})

            # cleanup closed positions older than 30s
            STATE.open_positions = [
                p for p in STATE.open_positions if p.get("status") == "open"
                or (time.time() - datetime.fromisoformat(p.get("closed_at", datetime.now(timezone.utc).isoformat())).timestamp() < 30 if p.get("closed_at") else True)
            ]
        except Exception as e:
            log.exception("position manager error: %s", e)
        await asyncio.sleep(0.5)
