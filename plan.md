# plan.md — Polymarket BTC UP/DOWN Scalper Bot (LIVE-capable)

## STATUS: Phase 2 COMPLETE ✓ — Phase 3 (LIVE hardening) optional / on request

## What was built

### Phase 1 — POC (all 8 user stories passing)
- `tests/test_core.py` proved core workflow end-to-end:
  - Coinbase WS streaming BTC-USD (P50=24ms, P95=27ms latency)
  - OKX derivatives (funding rate, OI, taker volume)
  - Polymarket Gamma discovery: 30+ BTC markets including 5-minute "Up or Down" markets
  - Polymarket CLOB orderbook fetch (YES/NO bid/ask/mid/spread/depth)
  - Signal engine + BULL/BEAR convergence score
  - Edge detector (>0.3% threshold) + skip rules (conflict, low liquidity, large edge)
  - EIP-712 dry-run order signing with py-clob-client
  - Risk manager (0.5% per trade, 2% daily DD, -0.4% hard stop)

### Phase 2 — Production app (100% test pass)
**Backend** (FastAPI, /app/backend):
- `server.py` — main API + WebSocket /api/ws/state + auth (JWT) + TV webhook
- `app/state.py` — shared runtime state (in-memory)
- `app/market_data.py` — Coinbase WS, REST candles, OKX derivatives polling
- `app/polymarket.py` — Gamma discovery, CLOB book refresh, py-clob-client live signer
- `app/strategy.py` — RSI/EMA/funding/imbalance signals, convergence, edge detector, 100-node/180-edge graph builder
- `app/risk.py` — position sizing, daily DD halt, hard stop, skip rules
- `app/runtime.py` — strategy loop (~300ms) + position manager (mark-to-market, TP/SL)
- Endpoints: /api/auth/login, /api/state, /api/settings, /api/mode, /api/kill_switch, /api/select_market, /api/wallet/config, /api/webhooks/tradingview, /api/tv_events
- LIVE mode wired (py-clob-client) but BLOCKED until POLY_PRIVATE_KEY is set

**Frontend** (React + shadcn, /app/frontend):
- Login page with demo creds (trader@scalper.local / scalper2026)
- Top bar: BTC live price, WS status dots, latency P50/P95/P99, PAPER/LIVE pill
- Live Monitor tab: lightweight-charts candlestick + Polymarket orderbook + edge meter
- Signals tab: convergence gauge + component bars + TradingView log
- Force-Graph tab: react-force-graph-2d (100 nodes / 180 edges)
- Trades tab: open positions + trade journal with P&L
- Risk tab: equity curve, daily DD bar, kill-switch with confirm dialog
- Settings tab: strategy thresholds + wallet/API form + TV webhook URL
- LIVE activation flow with double-confirm dialog
- Sonner toasts for edge alerts, opens, TP/SL

## Verified working
- Coinbase WS BTC live feed (was Binance — geo-blocked, swapped to Coinbase)
- OKX derivatives (was Binance — geo-blocked, swapped to OKX)
- Polymarket finds REAL 5-minute "Bitcoin Up or Down" markets (e.g. "Bitcoin Up or Down - May 13, 2:30PM-2:45PM ET")
- Paper trading actively opening/closing positions with TP/SL
- Risk rules enforced (DD halt at 2%, hard stop at -0.4%)
- All skip rules working (no_edge, signal_conflict, low_liquidity, wide_spread, edge_too_large, daily_dd_halt, daily_cap, kill_switch, bot_paused)

## Demo credentials & secrets
- Login: trader@scalper.local / scalper2026
- TradingView webhook secret: tv-scalper-secret-change-me
- LIVE trading: requires user to set POLY_PRIVATE_KEY (+ optional funder/api creds) in Settings tab or /app/backend/.env

## Known geo limitations
- Binance & Bybit blocked from Emergent cloud IP (HTTP 451 / CloudFront 403)
- Used Coinbase + OKX as functionally equivalent replacements
- Polymarket Gamma/CLOB works fine

## Phase 3 (post-V1, optional)
- Polygon RPC balance/allowance checks before LIVE
- Order status reconciliation (placed → partial → filled/cancel)
- CSV export of trade journal
- Backtest replay module
- Per-symbol multi-market scaling
