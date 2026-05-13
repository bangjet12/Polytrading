import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";

export default function EdgeMeterPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const edge = snap?.edge || {};
  const pct = edge.edge != null ? edge.edge * 100 : 0;
  const abs = Math.min(5, Math.abs(pct));
  const bull = pct >= 0;
  const reasons = edge.skip_reasons || [];
  const direction = edge.direction || "NONE";

  return (
    <Panel data-testid="edge-meter-panel">
      <PanelHeader>
        <PanelTitle>Edge Meter</PanelTitle>
        <Badge
          variant="outline"
          className={`font-mono text-[10px] ${
            direction === "BUY_YES"
              ? "text-[hsl(var(--bull))] border-[hsl(var(--bull))]/40"
              : direction === "BUY_NO"
              ? "text-[hsl(var(--bear))] border-[hsl(var(--bear))]/40"
              : "text-muted-foreground"
          }`}
          data-testid="edge-direction"
        >
          {direction}
        </Badge>
      </PanelHeader>
      <div className="p-3 space-y-3">
        <div className="flex items-baseline justify-between">
          <span
            className={`text-3xl font-mono tabular-nums ${
              bull ? "text-[hsl(var(--bull))]" : "text-[hsl(var(--bear))]"
            }`}
            data-testid="edge-meter-percent"
          >
            {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
          </span>
          <div className="text-right text-xs font-mono text-muted-foreground space-y-0.5">
            <div>fair YES: <span className="text-foreground">{edge.fair_yes_prob?.toFixed(3) ?? "—"}</span></div>
            <div>mkt YES: <span className="text-foreground">{edge.market_yes_prob?.toFixed(3) ?? "—"}</span></div>
          </div>
        </div>

        {/* Bar */}
        <div
          className="relative h-3 rounded-full bg-[hsl(var(--panel-2))] border border-border overflow-hidden"
          data-testid="edge-meter"
        >
          <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
          <div
            className={`absolute top-0 bottom-0 ${bull ? "left-1/2" : "right-1/2"}`}
            style={{
              width: `${Math.min(50, (abs / 5) * 50)}%`,
              background: `linear-gradient(90deg, ${bull ? "hsl(var(--bull))" : "hsl(var(--bear))"}, ${bull ? "hsl(var(--bull) / 0.4)" : "hsl(var(--bear) / 0.4)"})`,
            }}
          />
        </div>
        <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
          <span>-5%</span>
          <span>0</span>
          <span>+5%</span>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-1" data-testid="edge-skip-reasons">
          {reasons.length === 0 ? (
            <Badge className="bg-[hsl(var(--bull))]/15 text-[hsl(var(--bull))] border-[hsl(var(--bull))]/30">
              ready
            </Badge>
          ) : (
            reasons.map((r) => (
              <Badge
                key={r}
                className="bg-[hsl(var(--bear))]/10 text-[hsl(var(--bear))] border-[hsl(var(--bear))]/30 font-mono text-[10px]"
              >
                skip: {r}
              </Badge>
            ))
          )}
        </div>
        <div className="text-[10px] font-mono text-muted-foreground">
          reason: {edge.reason || "—"}
        </div>
      </div>
    </Panel>
  );
}
