import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";

function Bar({ value, color = "hsl(var(--info))" }) {
  const pct = Math.max(-1, Math.min(1, value || 0));
  const positive = pct >= 0;
  return (
    <div className="relative h-2 rounded-full bg-[hsl(var(--panel-2))] border border-border overflow-hidden">
      <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
      <div
        className={`absolute top-0 bottom-0 ${positive ? "left-1/2" : "right-1/2"}`}
        style={{ width: `${Math.abs(pct) * 50}%`, background: positive ? "hsl(var(--bull))" : "hsl(var(--bear))" }}
      />
    </div>
  );
}

export default function SignalsPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const sig = snap?.signals || {};
  const comp = sig.components || {};
  const score = sig.convergence_score || 0;
  const label = sig.label || "NEUTRAL";
  const conflict = sig.conflict;

  const labelColor =
    label === "BULL"
      ? "text-[hsl(var(--bull))] border-[hsl(var(--bull))]/40 bg-[hsl(var(--bull))]/10"
      : label === "BEAR"
      ? "text-[hsl(var(--bear))] border-[hsl(var(--bear))]/40 bg-[hsl(var(--bear))]/10"
      : "text-muted-foreground border-border bg-muted";

  return (
    <Panel data-testid="signals-panel">
      <PanelHeader>
        <PanelTitle>Signals & Convergence</PanelTitle>
        <div className="flex items-center gap-1.5">
          {conflict && (
            <Badge className="bg-[hsl(var(--bear))]/15 text-[hsl(var(--bear))] border-[hsl(var(--bear))]/30 font-mono text-[10px]">
              conflict
            </Badge>
          )}
          <Badge
            data-testid="signal-label-badge"
            className={`font-mono text-[10px] ${labelColor}`}
          >
            {label}
          </Badge>
        </div>
      </PanelHeader>
      <div className="p-3 space-y-3">
        <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border p-3">
          <div className="text-[10px] text-muted-foreground uppercase">Convergence score</div>
          <div
            className={`text-2xl font-mono tabular-nums ${
              score >= 0.15 ? "text-[hsl(var(--bull))]" : score <= -0.15 ? "text-[hsl(var(--bear))]" : "text-foreground"
            }`}
            data-testid="convergence-score-value"
          >
            {score >= 0 ? "+" : ""}{score.toFixed(3)}
          </div>
          <div className="mt-2" data-testid="convergence-score-gauge">
            <Bar value={score} />
          </div>
          <div className="flex justify-between text-[10px] font-mono text-muted-foreground mt-1">
            <span>BEAR -1</span>
            <span>0</span>
            <span>+1 BULL</span>
          </div>
        </div>

        <div className="space-y-2 text-xs" data-testid="signal-components">
          {Object.entries(comp).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3">
              <div className="w-24 text-muted-foreground">{k}</div>
              <div className="flex-1">
                <Bar value={v} />
              </div>
              <div className="w-14 text-right font-mono tabular-nums">
                {v >= 0 ? "+" : ""}{Number(v).toFixed(3)}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-border">
          <Row k="RSI(14)" v={sig.rsi14 != null ? sig.rsi14.toFixed(1) : "—"} />
          <Row k="EMA9-EMA21" v={sig.ema_cross != null ? sig.ema_cross.toFixed(2) : "—"} />
          <Row k="funding%" v={sig.funding_skew != null ? sig.funding_skew.toFixed(4) : "—"} />
          <Row k="taker_imb" v={sig.taker_imbalance != null ? sig.taker_imbalance.toFixed(3) : "—"} />
        </div>
      </div>
    </Panel>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{k}</span>
      <span className="tabular-nums">{v}</span>
    </div>
  );
}
