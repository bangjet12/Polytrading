"""Signal engine + edge detector + force-graph builder."""
from __future__ import annotations

import math
import random
import re
import time
from typing import Optional


def rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
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


def compute_signals(closes: list[float], deriv: dict) -> dict:
    r = rsi(closes, 14)
    ef = ema(closes, 9)
    es = ema(closes, 21)
    cross = (ef - es) if (ef and es) else 0.0
    funding_pct = deriv.get("funding_rate", 0) * 100
    tb = deriv.get("taker_buy_volume", 0)
    ts = deriv.get("taker_sell_volume", 0)
    total = tb + ts
    imb = (tb - ts) / total if total else 0.0

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
    convergence = sum(parts) / max(1, len(parts))
    pos = sum(1 for p in parts if p > 0.15)
    neg = sum(1 for p in parts if p < -0.15)
    conflict = pos >= 2 and neg >= 2
    label = "BULL" if convergence > 0.15 else "BEAR" if convergence < -0.15 else "NEUTRAL"
    return {
        "rsi14": r,
        "ema_fast": ef,
        "ema_slow": es,
        "ema_cross": cross,
        "funding_skew": funding_pct,
        "taker_imbalance": imb,
        "convergence_score": convergence,
        "label": label,
        "conflict": conflict,
        "components": components,
    }


def estimate_fair_prob_above(spot: float, signal: dict, minutes_to_expiry: float, barrier: float) -> float:
    if minutes_to_expiry <= 0:
        return 1.0 if spot > barrier else 0.0
    sigma5 = max(spot * 0.0025, 1.0)
    h = sigma5 * math.sqrt(minutes_to_expiry / 5.0)
    z = (spot - barrier) / h if h > 0 else 0.0
    base_p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    tilt = 0.05 * signal.get("convergence_score", 0)
    return max(0.01, min(0.99, base_p + tilt))


def estimate_fair_prob_updown(spot: float, signal: dict, minutes_to_expiry: float, ref_price: float) -> float:
    if minutes_to_expiry <= 0:
        return 1.0 if spot > ref_price else 0.0
    sigma5 = max(spot * 0.0025, 1.0)
    h = sigma5 * math.sqrt(minutes_to_expiry / 5.0)
    z = (spot - ref_price) / h if h > 0 else 0.0
    base_p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    tilt = 0.10 * signal.get("convergence_score", 0)
    return max(0.01, min(0.99, base_p + tilt))


def extract_barrier(question: str, fallback: float) -> float:
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", question)
    if not m:
        return fallback
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return fallback


def detect_edge(spot: float, market: dict, book: dict, signal: dict, edge_threshold: float = 0.003) -> dict:
    yes = (book or {}).get("yes") or {}
    yes_mid = yes.get("mid")
    if yes_mid is None or spot <= 0:
        return {"has_edge": False, "direction": "NONE", "reason": "no book/spot",
                "market_yes_prob": yes_mid, "fair_yes_prob": None, "edge": 0.0,
                "barrier": None}
    mins = market.get("minutes_to_expiry") or 60.0
    q = (market.get("question") or "").lower()
    if "above" in q or "reach" in q:
        barrier = extract_barrier(market.get("question", ""), spot)
        fair = estimate_fair_prob_above(spot, signal, mins, barrier)
    else:
        barrier = spot
        fair = estimate_fair_prob_updown(spot, signal, mins, spot)
    edge = fair - yes_mid
    if signal.get("conflict"):
        return {"has_edge": False, "direction": "NONE", "reason": "signal conflict",
                "market_yes_prob": yes_mid, "fair_yes_prob": fair, "edge": edge, "barrier": barrier}
    if abs(edge) <= edge_threshold:
        return {"has_edge": False, "direction": "NONE", "reason": "edge below threshold",
                "market_yes_prob": yes_mid, "fair_yes_prob": fair, "edge": edge, "barrier": barrier}
    direction = "BUY_YES" if edge > 0 else "BUY_NO"
    return {"has_edge": True, "direction": direction, "reason": "edge above threshold",
            "market_yes_prob": yes_mid, "fair_yes_prob": fair, "edge": edge, "barrier": barrier}


# ====================== Force-graph builder ======================
# Build exactly 100 nodes / 180 edges representing the strategy's feature graph.
GROUP_COLORS = {
    "price": "#00D1FF",      # info / cyan
    "ta": "#2EE59D",        # bull-green for technical analysis
    "flow": "#A3E635",      # lime for orderflow
    "derivs": "#FFB84D",    # edge / amber for derivatives
    "market": "#7DD3FC",    # light blue for polymarket markets
    "edge": "#FF4D6D",      # bear-red for edge events
    "signal": "#FFE066",    # warm yellow for synthesized signals
}

FEATURE_NODES = [
    # 10 price/candle nodes
    *[(f"candle:{i}", "price", 4) for i in range(10)],
    # 8 TA nodes
    ("ta:rsi14", "ta", 9), ("ta:rsi7", "ta", 6), ("ta:ema9", "ta", 9), ("ta:ema21", "ta", 9),
    ("ta:ema_cross", "ta", 12), ("ta:vwap", "ta", 7), ("ta:atr14", "ta", 7), ("ta:bbands", "ta", 6),
    # 8 orderflow nodes
    ("flow:taker_buy_5m", "flow", 8), ("flow:taker_sell_5m", "flow", 8),
    ("flow:imbalance", "flow", 10), ("flow:large_trades", "flow", 6),
    ("flow:cvd", "flow", 7), ("flow:depth_bid", "flow", 5), ("flow:depth_ask", "flow", 5),
    ("flow:liquidations", "flow", 6),
    # 8 derivatives nodes
    ("deriv:funding_rate", "derivs", 9), ("deriv:open_interest", "derivs", 9),
    ("deriv:mark_price", "derivs", 5), ("deriv:basis", "derivs", 6),
    ("deriv:perp_premium", "derivs", 6), ("deriv:oi_change_5m", "derivs", 7),
    ("deriv:longshort_ratio", "derivs", 7), ("deriv:next_funding", "derivs", 4),
    # 4 synthesized signals
    ("signal:bull_score", "signal", 13), ("signal:bear_score", "signal", 13),
    ("signal:convergence", "signal", 16), ("signal:conflict_flag", "signal", 8),
    # 1 spot price
    ("price:spot_btc", "price", 18),
    # remainder: market candidates (we add at runtime up to ~60 if available)
]


def build_graph(
    markets: list[dict],
    signal: dict,
    edge: dict,
    target_nodes: int = 100,
    target_edges: int = 180,
) -> dict:
    """Build a stable, semi-deterministic 100-node / 180-edge graph."""
    nodes: list[dict] = []
    seen_ids: set[str] = set()

    def add(id_: str, group: str, val: float, label: str | None = None, score: float = 0.0):
        if id_ in seen_ids:
            return
        seen_ids.add(id_)
        nodes.append({
            "id": id_,
            "group": group,
            "color": GROUP_COLORS.get(group, "#7DD3FC"),
            "val": float(val),
            "label": label or id_,
            "score": float(score),
        })

    # Add feature nodes
    for nid, group, val in FEATURE_NODES:
        add(nid, group, val)

    # Add market nodes (up to remaining capacity)
    remaining_for_markets = target_nodes - len(nodes)
    # always leave a couple for edge events
    reserved_for_edges = 2
    take = max(0, remaining_for_markets - reserved_for_edges)
    for m in (markets or [])[:take]:
        mid = m.get("market_id", "")[:14]
        if not mid:
            continue
        add(
            f"market:{mid}",
            "market",
            6 + min(8, math.log10(1 + (m.get("liquidity") or 1))),
            label=(m.get("question") or "")[:50],
            score=float(m.get("liquidity") or 0),
        )

    # Edge event nodes (one for current edge state, one for last alert)
    if edge.get("has_edge"):
        add("edge:current", "edge", 14, label=f"EDGE {edge.get('edge', 0):+.3f} {edge.get('direction')}", score=abs(edge.get("edge", 0)))
    else:
        add("edge:current", "edge", 6, label="no edge")
    add("edge:meter", "edge", 10, label="edge meter")

    # Pad to exactly target_nodes if we're short
    pad_i = 0
    while len(nodes) < target_nodes:
        add(f"feature:filler_{pad_i}", "price", 3, label=f"feat{pad_i}")
        pad_i += 1

    # Trim to target_nodes
    nodes = nodes[:target_nodes]

    # Build edges deterministically (semantic backbone)
    edges: list[dict] = []
    seen_links: set[tuple[str, str]] = set()

    def link(a: str, b: str, w: float = 1.0):
        if a == b:
            return
        key = tuple(sorted((a, b)))
        if key in seen_links:
            return
        if a not in seen_ids or b not in seen_ids:
            return
        seen_links.add(key)
        edges.append({"source": a, "target": b, "weight": float(w)})

    # 1. spot price connects to candles + TA
    for i in range(10):
        link("price:spot_btc", f"candle:{i}", 0.8)
    for ta in ("ta:rsi14", "ta:rsi7", "ta:ema9", "ta:ema21", "ta:ema_cross",
               "ta:vwap", "ta:atr14", "ta:bbands"):
        link("price:spot_btc", ta, 0.7)
        link("candle:0", ta, 0.5)
    # 2. TA → signals
    for ta in ("ta:rsi14", "ta:ema9", "ta:ema21", "ta:ema_cross", "ta:vwap", "ta:atr14", "ta:bbands", "ta:rsi7"):
        link(ta, "signal:bull_score", 0.6)
        link(ta, "signal:bear_score", 0.6)
    # 3. Orderflow → signals
    for fl in ("flow:taker_buy_5m", "flow:taker_sell_5m", "flow:imbalance", "flow:large_trades",
               "flow:cvd", "flow:depth_bid", "flow:depth_ask", "flow:liquidations"):
        link(fl, "signal:bull_score", 0.5)
        link(fl, "signal:bear_score", 0.5)
    # 4. Derivatives → signals
    for dv in ("deriv:funding_rate", "deriv:open_interest", "deriv:mark_price", "deriv:basis",
               "deriv:perp_premium", "deriv:oi_change_5m", "deriv:longshort_ratio", "deriv:next_funding"):
        link(dv, "signal:bull_score", 0.55)
        link(dv, "signal:bear_score", 0.55)
    # 5. signals → convergence/conflict → edge meter
    link("signal:bull_score", "signal:convergence", 1.0)
    link("signal:bear_score", "signal:convergence", 1.0)
    link("signal:convergence", "signal:conflict_flag", 0.6)
    link("signal:convergence", "edge:meter", 1.0)
    link("signal:conflict_flag", "edge:meter", 0.5)
    link("edge:meter", "edge:current", 1.5)

    # 6. Markets cluster: connect each market node to edge meter + a couple of signal/derivs
    market_node_ids = [n["id"] for n in nodes if n["group"] == "market"]
    for i, mid in enumerate(market_node_ids):
        link(mid, "edge:meter", 0.4)
        # bridge to derivs/signals via stable picks
        link(mid, "signal:convergence", 0.3)
        if i % 2 == 0:
            link(mid, "deriv:funding_rate", 0.25)
        else:
            link(mid, "flow:imbalance", 0.25)

    # 7. Pad with cross-links between filler/candle nodes until we hit target_edges
    pad_pairs = [
        ("ta:rsi14", "ta:rsi7"), ("ta:ema9", "ta:ema21"),
        ("flow:depth_bid", "flow:depth_ask"), ("deriv:open_interest", "deriv:oi_change_5m"),
        ("deriv:funding_rate", "deriv:perp_premium"),
        ("flow:cvd", "flow:imbalance"), ("flow:large_trades", "flow:liquidations"),
        ("deriv:basis", "deriv:mark_price"), ("deriv:longshort_ratio", "flow:imbalance"),
        ("ta:bbands", "ta:atr14"), ("ta:vwap", "price:spot_btc"),
    ]
    for a, b in pad_pairs:
        link(a, b, 0.4)

    # If still under target, link consecutive candle/filler pairs for stability
    if len(edges) < target_edges:
        # candle chain
        for i in range(9):
            link(f"candle:{i}", f"candle:{i+1}", 0.4)
            if len(edges) >= target_edges:
                break
    if len(edges) < target_edges:
        # filler ring
        fillers = [n["id"] for n in nodes if n["id"].startswith("feature:filler_")]
        for i in range(len(fillers)):
            link(fillers[i], fillers[(i + 1) % len(fillers)], 0.3)
            if len(edges) >= target_edges:
                break
    if len(edges) < target_edges:
        # market ring + bridges
        for i in range(len(market_node_ids)):
            link(market_node_ids[i], market_node_ids[(i + 1) % len(market_node_ids)], 0.3)
            if len(edges) >= target_edges:
                break

    # Hard trim to target_edges in case we overshot
    edges = edges[:target_edges]
    return {"nodes": nodes, "links": edges, "counts": {"nodes": len(nodes), "edges": len(edges)}}
