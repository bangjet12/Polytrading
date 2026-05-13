# plan.md — Polymarket BTC UP/DOWN Scalper Bot (LIVE-capable)

## 1) Objectives
- Prove end-to-end core loop works: **Binance 5m feed → signal/convergence → Polymarket market discovery + orderbook → mispricing edge → (paper) order build → (live) signed + placed order**.
- Ship an MVP dashboard + runner that can operate **PAPER by default** with an explicit **LIVE toggle** (LIVE requires wallet + API creds).
- Incorporate **TradingView alerts via webhook** as an optional signal input.
- Include a **force-directed graph visualization (100 nodes / 180 edges)** in the frontend to show signal correlations and cluster convergence (BULL/BEAR).
- Enforce risk controls: **0.5% risk/trade**, **2% max daily drawdown halt**, **-0.4% hard stop**, plus skip rules.
- Target realistic performance: **<500ms decision-loop** (acknowledging Polymarket CLOB rate limits and Polygon confirmation latency).
- Make it runnable on Emergent preview and downloadable to run locally (no GPU).

**Current status / progress**
- Requirements clarified:
  - Mode: **LIVE trading desired** (but credentials only requested/used after POC passes).
  - TradingView: **webhook-based** (user configures TV alerts → POST to our backend).
  - Visualization: **build force-graph** (react-force-graph) with **100 nodes / 180 edges**.
  - Latency: realistic targets; accept chain limits.
  - Deployment: run anywhere (Emergent + local).
- Implementation not started yet; next step is Phase 1 POC.

## 2) Implementation Steps

### Phase 1 — Core POC (isolation; do not proceed until green)
**Web search / best practices**
- Confirm current Polymarket CLOB endpoints, auth, rate limits, and `py-clob-client` examples.
- Confirm what shortest-duration BTC “Up/Down” markets exist (5m vs hourly) and how to compute time-to-expiry.

**POC focus (updated):** Binance WS + Polymarket CLOB read + signal engine + mispricing + risk + dry-run order signing.

**POC deliverable:** `test_core.py` (single script) + `README_poc.md`
1. **Binance WS**
   - Connect to `btcusdt@kline_5m` and also a spot price stream.
   - Log timestamps, compute feed latency, maintain rolling window.
2. **Derivatives proxies (Binance REST/WS)**
   - Pull funding rate, OI delta, taker buy/sell imbalance (minimal endpoints).
3. **Polymarket market discovery (public read)**
   - List active BTC markets; select **shortest time-to-expiry** “Up/Down” candidate.
   - Fetch CLOB orderbook for YES/NO tokens; compute mid, spread, liquidity.
4. **Signal & convergence engine (core)**
   - Compute base features: RSI(14), EMA cross, funding skew, OI change, taker imbalance.
   - Output:
     - single **convergence score** ∈ [-1, 1]
     - label: **BULL / BEAR / NEUTRAL**
     - **conflict flag** (e.g., TA bullish but flow bearish)
5. **Mispricing detector**
   - Compute implied prob from CLOB midprice.
   - Compare vs fair value model (spot move vs barrier + time-to-expiry + score adjustment).
   - Trigger edge if **abs(edge) > 0.3%** and passes skip rules.
6. **Skip rules (POC-level)**
   - No edge → skip
   - Low liquidity (min depth / max spread) → skip
   - Signal conflict → skip
   - Daily limit hit → skip
7. **Risk manager unit checks**
   - Position sizing: risk = **0.5% equity** per trade.
   - Daily max drawdown: **2%** → halt.
   - Hard stop: **-0.4%** per position.
8. **Order signing dry-run**
   - Build EIP-712 typed order via `py-clob-client` without submitting.
   - Validate payload shape, signature creation, and deterministic order params.

**Phase 1 user stories (POC)**
1. As an operator, I can confirm Binance WS streams 5m candles continuously with measured latency.
2. As an operator, I can confirm Polymarket has tradeable BTC Up/Down markets and can fetch their orderbooks.
3. As an operator, I can see a stable convergence score that reacts to RSI/EMA + funding/OI/orderflow.
4. As an operator, I can see edge events when Polymarket implied prob lags the spot-derived fair value by >0.3%.
5. As an operator, I can verify orders can be constructed and signed (dry-run) without exposing secrets.

**Exit gate (must pass):** Binance data stable; Polymarket market selection works; edge events appear; dry-run signing succeeds; risk rules prevent trades when triggered.

---

### Phase 2 — V1 App Development (MVP dashboard + bot runner)
**Architecture**
- Backend: FastAPI (async) + background tasks.
- Storage: SQLite (simple) or MongoDB (if already available) for journal.
- Frontend: React dashboard.

**Backend modules (updated)**
1. **Market data service**: Binance WS consumers (spot/kline) + periodic derivatives snapshots.
2. **Polymarket service**: public reads + trading client integration (via `py-clob-client`).
3. **Strategy service**: convergence scoring + mispricing detector (tick every ~200ms).
4. **Execution service (paper-first)**
   - Paper executor: slippage model, fill simulation, PnL.
   - Rate-limited order queue design mirrored to live constraints.
5. **Risk service**: sizing, DD halt, per-trade hard stop, daily reset.
6. **Journal service**: log signals, decisions, orders, fills, PnL, latency.
7. **Settings**: paper/live toggle, thresholds, liquidity limits.
8. **TradingView webhook receiver (NEW)**
   - Endpoint: `POST /api/webhooks/tradingview`
   - Validate shared secret / signature token.
   - Parse alert payload → normalize into internal signal events.
   - Store + broadcast to UI.
9. **Graph builder service (NEW)**
   - Maintain a rolling correlation/relationship graph between signals/features (nodes/edges).
   - Output exactly **100 nodes / 180 edges** (top-K by weight, pruned/normalized).

**Frontend screens (updated)**
1. **Live Monitor**: spot price, selected Polymarket market, orderbook top, implied prob, edge meter.
2. **Signals**: RSI/EMA/funding/OI/imbalance + TradingView alerts + convergence score + conflict flags.
3. **Force-Graph View (NEW)**
   - Use `react-force-graph`.
   - Render 100 nodes / 180 edges.
   - Color by cluster (BULL/BEAR/NEUTRAL), edge thickness by correlation/weight.
   - Click node → show feature description + recent values.
4. **Trades**: open positions, recent orders, fills, PnL.
5. **Risk**: equity curve, DD, daily halt state, kill-switch.
6. **Settings**: configure thresholds; secrets entered locally; enable LIVE toggle (double confirm).

**Safety requirements in V1**
- Default **PAPER**; LIVE requires explicit enable + typed confirmation.
- Never send private key to frontend; backend reads `.env` only.
- Global kill-switch halts new orders and cancels working orders (paper cancels simulated queue).

**Phase 2 user stories (V1)**
1. As a user, I can run the bot in PAPER mode and see simulated trades with PnL and latency metrics.
2. As a user, I can see when the bot skips trading due to low liquidity, conflict, or insufficient edge.
3. As a user, I can send TradingView alerts to the bot and see them influence the convergence score.
4. As a user, I can view a force-graph of signal relationships and see BULL/BEAR cluster convergence.
5. As a user, I can press a kill-switch to immediately stop new orders and cancel open orders.
6. As a user, I can review a journal of all signals/edges/orders to audit decisions.

**Phase 2 testing**
- One full E2E pass: start backend+frontend → verify streaming updates → TradingView webhook event appears → paper trade → journal entries → kill-switch.

---

### Phase 3 — Live Trading Hardening + Refinement (updated)
1. **Credential + balance checks (NEW emphasis)**
   - Polygon RPC connectivity.
   - USDC balance, allowance approvals, and address checks.
   - Polymarket API key/secret/passphrase validation.
2. **LIVE execution enablement**
   - Strict toggles: paper/live environment separation.
   - Rate limiting aligned with CLOB constraints.
   - Cancel/replace logic under rate limits.
3. **Fill handling**
   - Reconcile partial fills, order states, and cancels.
   - Detect stuck orders and auto-cancel under risk rules.
4. **Slippage + spread-aware execution**
   - Only cross spread when edge > fees+slippage.
   - Prefer maker where feasible, with timeout-to-taker fallback.
5. **Latency profiling**
   - P50/P95/P99 decision time + order placement time.
   - Display on dashboard + export to logs.
6. **Force-graph refinements (if needed)**
   - Stabilize layout, add filtering, time-windowed edges.
7. **Backtest-lite**
   - Replay stored Binance candles + stored signals; approximate fills.

**Phase 3 user stories**
1. As a live trader, I can verify wallet balance/allowances before enabling LIVE.
2. As a live trader, I can see exact order status transitions (placed/partial/filled/canceled).
3. As a live trader, I can see measured end-to-end latency and rate-limit status.
4. As a live trader, I can enforce daily DD halt and see it block new entries.
5. As a live trader, I can export trade logs to CSV for accounting.

---

### Phase 4 — Optional (post-v1)
- Add authentication (only after user approval; affects agent testing).
- Add alerting (desktop/browser), more robust backtesting, strategy parameter presets.

## 3) Next Actions
1. Run Phase 1 web search to confirm Polymarket shortest-duration BTC Up/Down market availability and the correct CLOB endpoints.
2. Implement `test_core.py` and iterate until Phase 1 exit gate is green.
3. After POC passes, request LIVE credentials (store in `.env` only): Polygon private key, Polymarket API key/secret/passphrase, RPC URL.
4. Build Phase 2 MVP app around the proven core: add TradingView webhook receiver + force-graph + paper executor.

## 4) Success Criteria
- **POC:** stable Binance WS; Polymarket market discovery + orderbook fetch works; edge events detected; signed order dry-run succeeds; risk rules block appropriately.
- **V1 (Phase 2):** dashboard shows live data + TradingView events; force-graph renders 100/180; paper trades execute; journal persists; kill-switch works; LIVE toggle gated.
- **Live readiness (Phase 3):** credentials validated; balance/allowance verified; orders placed and reconciled; daily DD + hard stop reliably enforced; latency metrics visible and within target (<500ms decision loop, acknowledging chain confirmation limits).
