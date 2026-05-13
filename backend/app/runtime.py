"""Main strategy loop: signals → edge → skip rules → execution (paper or live)."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from .state import STATE
from .strategy import compute_signals, detect_edge, build_graph, detect_lag
from .risk import position_size_usd, skip_reasons
from .polymarket import place_live_order

log = logging.getLogger("runtime")


def _paper_execute(market: dict, direction: str, price: float, size_tokens: float) -> dict:
    """Simulate fill — entry_price is the actual ask we cross to fill our buy."""
    pos = {
        "id": str(uuid.uuid4()),
        "market_id": market.get("market_id"),
        "market_question": market.get("question"),
        "direction": direction,
        "entry_price": float(price),
        "size_tokens": float(size_tokens),
        "size_usd": float(price * size_tokens),
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
            # Update rolling spot history
            if STATE.spot_price > 0:
                STATE.spot_history.append((t0, STATE.spot_price))
            # Update rolling mid history (YES mid)
            yes_now = (STATE.selected_book or {}).get("yes") or {}
            if yes_now.get("mid") is not None:
                STATE.mid_history.append((t0, float(yes_now["mid"])))

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
            target_price = None
            if mkt:
                ref = STATE.market_refs.get(mkt.get("market_id"))
                if ref:
                    target_price = ref.get("target_price")
            edge = detect_edge(STATE.spot_price, mkt or {}, book, sig, edge_threshold, target_price=target_price, closes=STATE.closes_5m)
            edge["timestamp"] = time.time()
            edge["target_price"] = target_price

            # 2b. Lag detector (CLOB repricing lag) — PRIMARY edge per user spec
            lag = detect_lag(list(STATE.spot_history), list(STATE.mid_history), window_s=5.0)
            edge["lag"] = lag
            # Lag edges are the bot's real edge. Model edges are kept for display only.
            model_edge_val = edge.get("edge", 0)
            model_direction = edge.get("direction")
            edge["model_edge"] = model_edge_val
            edge["model_direction"] = model_direction
            if lag.get("has_lag"):
                edge["has_edge"] = True
                edge["direction"] = lag["direction"]
                edge["reason"] = f"clob_lag (Δspot={lag['spot_delta_pct']*100:+.3f}%)"
                edge["edge"] = lag["lag_score"]
                edge["edge_type"] = "lag"
            else:
                edge["has_edge"] = False
                edge["direction"] = "NONE"
                edge["edge"] = 0.0
                edge["edge_type"] = "model"  # nothing actionable
                edge["reason"] = "no_lag"
            STATE.edge = edge

            # 3. graph
            STATE.graph = build_graph(STATE.markets, sig, edge)

            # 4. evaluate skip rules
            skips = skip_reasons(book, sig, edge)
            edge["skip_reasons"] = skips

            # 5. execute if edge & no skip & not in cooldown for this market
            mid_id = (mkt or {}).get("market_id")
            already = any(
                p["market_id"] == mid_id and p.get("status") == "open"
                for p in STATE.open_positions
            )
            # cooldown: don't re-open same market for 90s after any close
            cooldown_active = False
            cooldown_s = 90.0
            now_ts = time.time()
            for p in reversed(STATE.open_positions):
                if p["market_id"] == mid_id and p.get("status") != "open":
                    closed_at = p.get("closed_at")
                    if closed_at:
                        try:
                            cts = datetime.fromisoformat(closed_at).timestamp()
                            if now_ts - cts < cooldown_s:
                                cooldown_active = True
                        except Exception:
                            pass
                    break
            if cooldown_active:
                edge["skip_reasons"] = list(edge.get("skip_reasons", [])) + ["cooldown"]
                skips = edge["skip_reasons"]

            if edge.get("has_edge") and not skips and mkt and not already:
                yes = book.get("yes") or {}
                no = book.get("no") or {}
                # In LIVE mode, cross the spread (use ask) — in PAPER, fill at mid (assume maker)
                if STATE.mode == "live":
                    if edge["direction"] == "BUY_YES":
                        entry_price = yes.get("best_ask")
                        side_depth_tokens = yes.get("depth_ask") or 0
                    else:
                        entry_price = no.get("best_ask")
                        side_depth_tokens = no.get("depth_ask") or 0
                else:
                    if edge["direction"] == "BUY_YES":
                        entry_price = yes.get("mid")
                        side_depth_tokens = (yes.get("depth_ask") or 0) + (yes.get("depth_bid") or 0)
                    else:
                        entry_price = no.get("mid")
                        side_depth_tokens = (no.get("depth_ask") or 0) + (no.get("depth_bid") or 0)
                if entry_price and entry_price > 0:
                    notional = position_size_usd()
                    # cap notional at ~25% of side depth to avoid moving the book
                    max_notional_book = entry_price * side_depth_tokens * 0.25
                    notional = min(notional, max_notional_book) if max_notional_book > 0 else notional
                    size_tokens = max(1.0, notional / max(entry_price, 0.01))
                    if STATE.mode == "live":
                        live_res = await place_live_order(mkt, edge["direction"], entry_price, size_tokens)
                        pos = {
                            "id": str(uuid.uuid4()),
                            "market_id": mkt.get("market_id"),
                            "market_question": mkt.get("question"),
                            "direction": edge["direction"],
                            "entry_price": float(entry_price),
                            "size_tokens": float(size_tokens),
                            "size_usd": float(entry_price * size_tokens),
                            "opened_at": datetime.now(timezone.utc).isoformat(),
                            "status": "open" if live_res.get("ok") else "failed",
                            "mode": "live",
                            "order_id": live_res.get("order_id"),
                            "error": live_res.get("error"),
                            "latency_ms": live_res.get("latency_ms"),
                        }
                    else:
                        pos = _paper_execute(mkt, edge["direction"], entry_price, size_tokens)

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
    """Mark-to-market open positions; apply hard stop, take profit, AND settlement at window expiry."""
    while True:
        try:
            book = STATE.selected_book or {}
            yes = book.get("yes") or {}
            no = book.get("no") or {}
            current_yes_mid = yes.get("mid")
            current_no_mid = no.get("mid")
            now_ts = time.time()
            for pos in list(STATE.open_positions):
                if pos.get("status") != "open":
                    continue
                mid = pos.get("market_id")
                # Find market info for settlement
                ref = STATE.market_refs.get(mid) or {}
                target = ref.get("target_price")
                end_ts = ref.get("end_ts") or 0
                expired = end_ts and now_ts >= end_ts

                # SETTLEMENT at window expiry: pay 1.0 if won, 0.0 if lost
                if expired and target is not None and STATE.spot_price > 0:
                    spot = STATE.spot_price
                    yes_wins = spot > target
                    settle_price = 1.0 if (
                        (pos["direction"] == "BUY_YES" and yes_wins)
                        or (pos["direction"] == "BUY_NO" and not yes_wins)
                    ) else 0.0
                    pnl = (settle_price - pos["entry_price"]) * pos["size_tokens"]
                    pos["status"] = "settled_win" if settle_price == 1.0 else "settled_loss"
                    pos["exit_price"] = float(settle_price)
                    pos["realized_pnl"] = float(pnl)
                    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                    STATE.daily_pnl += pnl
                    STATE.equity += pnl
                    STATE.equity_curve.append({"ts": now_ts, "equity": STATE.equity})
                    STATE.trade_journal.append({"ts": now_ts, "event": "settlement", "position": pos})
                    log.info(
                        "settled %s: spot=$%.2f target=$%.2f → %s PnL=$%.2f",
                        pos["direction"], spot, target,
                        "WIN" if settle_price == 1.0 else "LOSS", pnl,
                    )
                    continue

                # Mark-to-market only if we still have a fresh book for THIS market
                if mid != (STATE.selected_market or {}).get("market_id"):
                    continue
                # PAPER: mark at mid (maker-like fill assumption). LIVE: mark at bid (where we'd actually close).
                token_book = (book.get("yes") if pos["direction"] == "BUY_YES" else book.get("no")) or {}
                if pos.get("mode") == "live":
                    exit_p = token_book.get("best_bid")
                else:
                    exit_p = token_book.get("mid")
                if exit_p is None:
                    continue
                pnl_pct_now = (exit_p - pos["entry_price"]) / max(pos["entry_price"], 1e-6)
                pos["current_price"] = float(exit_p)
                pos["unrealized_pnl_pct"] = float(pnl_pct_now)
                pos["unrealized_pnl"] = float((exit_p - pos["entry_price"]) * pos["size_tokens"])
                # hard stop -hard_stop_pct
                if pnl_pct_now <= -STATE.settings["hard_stop_pct"]:
                    realized_exit = pos["entry_price"] * (1 - STATE.settings["hard_stop_pct"])
                    pnl = (realized_exit - pos["entry_price"]) * pos["size_tokens"]
                    pos["status"] = "closed_stop"
                    pos["exit_price"] = float(realized_exit)
                    pos["realized_pnl"] = float(pnl)
                    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                    STATE.daily_pnl += pnl
                    STATE.equity += pnl
                    STATE.equity_curve.append({"ts": now_ts, "equity": STATE.equity})
                    STATE.trade_journal.append({"ts": now_ts, "event": "hard_stop", "position": pos})
                # take profit at >= 0.6% (within target 0.3-0.8%)
                elif pnl_pct_now >= 0.006:
                    realized_exit = pos["entry_price"] * 1.006
                    pnl = (realized_exit - pos["entry_price"]) * pos["size_tokens"]
                    pos["status"] = "closed_tp"
                    pos["exit_price"] = float(realized_exit)
                    pos["realized_pnl"] = float(pnl)
                    pos["closed_at"] = datetime.now(timezone.utc).isoformat()
                    STATE.daily_pnl += pnl
                    STATE.equity += pnl
                    STATE.equity_curve.append({"ts": now_ts, "equity": STATE.equity})
                    STATE.trade_journal.append({"ts": now_ts, "event": "take_profit", "position": pos})

            # cleanup closed positions older than 60s
            STATE.open_positions = [
                p for p in STATE.open_positions
                if p.get("status") == "open"
                or (
                    p.get("closed_at")
                    and (now_ts - datetime.fromisoformat(p["closed_at"]).timestamp()) < 60
                )
            ]
        except Exception as e:
            log.exception("position manager error: %s", e)
        await asyncio.sleep(0.5)
