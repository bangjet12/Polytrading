import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";

function fmtUSD(n, d = 2) {
  if (n == null || isNaN(n)) return "—";
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: d })}`;
}
function fmtPct(n) {
  if (n == null || isNaN(n)) return "—";
  return `${(n * 100).toFixed(3)}%`;
}
function tsShort(ts) {
  try {
    return new Date(ts * 1000).toLocaleTimeString();
  } catch {
    return "—";
  }
}

export default function TradesPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const open = snap?.open_positions || [];
  const journal = (snap?.trade_journal || []).slice().reverse();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel data-testid="open-positions-panel">
        <PanelHeader>
          <PanelTitle>Open Positions</PanelTitle>
          <Badge variant="outline" className="font-mono text-[10px]">
            n={open.length}
          </Badge>
        </PanelHeader>
        <div className="overflow-auto max-h-[420px] subtle-scroll">
          <table className="w-full text-xs">
            <thead className="text-muted-foreground sticky top-0 bg-card">
              <tr>
                <th className="text-left px-2 py-1.5">market</th>
                <th className="text-left px-2 py-1.5">dir</th>
                <th className="text-right px-2 py-1.5">entry</th>
                <th className="text-right px-2 py-1.5">size$</th>
                <th className="text-right px-2 py-1.5">cur</th>
                <th className="text-right px-2 py-1.5">PnL%</th>
                <th className="text-left px-2 py-1.5">status</th>
              </tr>
            </thead>
            <tbody data-testid="open-positions-rows">
              {open.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-muted-foreground py-4">
                    No open positions
                  </td>
                </tr>
              ) : (
                open.map((p) => (
                  <tr key={p.id} className="border-t border-border/40">
                    <td className="px-2 py-1.5 max-w-[180px] truncate">{p.market_question}</td>
                    <td className="px-2 py-1.5">
                      <Badge
                        className={`font-mono text-[10px] ${
                          p.direction === "BUY_YES"
                            ? "text-[hsl(var(--bull))] border-[hsl(var(--bull))]/40 bg-[hsl(var(--bull))]/10"
                            : "text-[hsl(var(--bear))] border-[hsl(var(--bear))]/40 bg-[hsl(var(--bear))]/10"
                        }`}
                      >
                        {p.direction}
                      </Badge>
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono">{Number(p.entry_price).toFixed(3)}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{fmtUSD(p.size_usd, 0)}</td>
                    <td className="px-2 py-1.5 text-right font-mono">
                      {p.current_price != null ? Number(p.current_price).toFixed(3) : "—"}
                    </td>
                    <td
                      className={`px-2 py-1.5 text-right font-mono ${
                        (p.unrealized_pnl_pct || 0) >= 0
                          ? "text-[hsl(var(--bull))]"
                          : "text-[hsl(var(--bear))]"
                      }`}
                    >
                      {p.unrealized_pnl_pct != null ? fmtPct(p.unrealized_pnl_pct) : "—"}
                    </td>
                    <td className="px-2 py-1.5 text-muted-foreground">{p.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel data-testid="journal-panel">
        <PanelHeader>
          <PanelTitle>Trade Journal</PanelTitle>
          <Badge variant="outline" className="font-mono text-[10px]">
            n={journal.length}
          </Badge>
        </PanelHeader>
        <div className="overflow-auto max-h-[420px] subtle-scroll">
          <table className="w-full text-xs">
            <thead className="text-muted-foreground sticky top-0 bg-card">
              <tr>
                <th className="text-left px-2 py-1.5">time</th>
                <th className="text-left px-2 py-1.5">event</th>
                <th className="text-left px-2 py-1.5">dir</th>
                <th className="text-right px-2 py-1.5">edge</th>
                <th className="text-right px-2 py-1.5">PnL</th>
              </tr>
            </thead>
            <tbody>
              {journal.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-muted-foreground py-4">
                    No trades yet
                  </td>
                </tr>
              ) : (
                journal.slice(0, 50).map((e, i) => {
                  const p = e.position || {};
                  return (
                    <tr key={i} className="border-t border-border/40">
                      <td className="px-2 py-1.5 font-mono text-muted-foreground">{tsShort(e.ts)}</td>
                      <td className="px-2 py-1.5">{e.event}</td>
                      <td className="px-2 py-1.5">{p.direction || "—"}</td>
                      <td className="px-2 py-1.5 text-right font-mono">
                        {e.edge?.edge != null ? `${(e.edge.edge * 100).toFixed(2)}%` : "—"}
                      </td>
                      <td
                        className={`px-2 py-1.5 text-right font-mono ${
                          (p.realized_pnl || 0) >= 0
                            ? "text-[hsl(var(--bull))]"
                            : "text-[hsl(var(--bear))]"
                        }`}
                      >
                        {p.realized_pnl != null ? fmtUSD(p.realized_pnl, 2) : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
