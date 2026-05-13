import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";

export default function TradingViewLogPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const events = snap?.tv_events || [];
  return (
    <Panel data-testid="tv-log-panel">
      <PanelHeader>
        <PanelTitle>TradingView Alerts</PanelTitle>
        <Badge variant="outline" className="font-mono text-[10px]">
          n={events.length}
        </Badge>
      </PanelHeader>
      <div className="p-3 space-y-2 max-h-72 overflow-auto subtle-scroll">
        {events.length === 0 ? (
          <div className="text-xs text-muted-foreground">
            No alerts received. Send POST to <code className="font-mono text-[10px]">/api/webhooks/tradingview</code> with the shared secret to log events here.
          </div>
        ) : (
          events.map((e, i) => (
            <div key={i} className="text-xs border border-border rounded-md p-2 bg-[hsl(var(--panel-2))]">
              <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
                <span>{new Date(e.ts * 1000).toLocaleTimeString()}</span>
                <span>{e.symbol} · {e.timeframe}</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  className={`font-mono text-[10px] ${
                    /BULL|BUY|LONG/i.test(e.action)
                      ? "text-[hsl(var(--bull))] border-[hsl(var(--bull))]/40 bg-[hsl(var(--bull))]/10"
                      : /BEAR|SELL|SHORT/i.test(e.action)
                      ? "text-[hsl(var(--bear))] border-[hsl(var(--bear))]/40 bg-[hsl(var(--bear))]/10"
                      : ""
                  }`}
                >
                  {e.action || "—"}
                </Badge>
                <span className="font-mono text-xs">{e.price ? `$${Number(e.price).toLocaleString()}` : ""}</span>
              </div>
              {e.note && <div className="text-[11px] text-muted-foreground mt-1">{e.note}</div>}
            </div>
          ))
        )}
      </div>
    </Panel>
  );
}
