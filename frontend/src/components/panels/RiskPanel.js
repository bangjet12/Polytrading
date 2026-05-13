import { useState } from "react";
import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { api } from "@/lib/api";
import { toast } from "sonner";

function fmtUSD(n, d = 2) {
  if (n == null || isNaN(n)) return "—";
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: d })}`;
}

export default function RiskPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const eq = snap?.equity || 0;
  const start = snap?.starting_equity_today || eq;
  const dailyPnl = snap?.daily_pnl || 0;
  const dailyDDPct = start > 0 ? (dailyPnl / start) * 100 : 0;
  const haltPct = (snap?.settings?.daily_dd_halt_pct || 0.02) * 100;
  const tradeCount = snap?.trade_count_today || 0;
  const cap = snap?.settings?.daily_trade_cap || 200;
  const killed = !!snap?.kill_switch;

  const eqCurve = (snap?.equity_curve || []).map((e) => ({
    t: new Date(e.ts * 1000).toLocaleTimeString(),
    equity: e.equity,
  }));
  // last 30 trade PnLs as bars
  const journal = snap?.trade_journal || [];
  const ddBars = journal
    .filter((e) => e.position?.realized_pnl != null)
    .slice(-30)
    .map((e, i) => ({ i: i + 1, pnl: e.position.realized_pnl }));

  const [open, setOpen] = useState(false);
  const toggleKill = async (engage) => {
    try {
      const r = await api.post("/kill_switch", { engaged: engage });
      toast.success(r.data.kill_switch ? "Kill switch engaged" : "Kill switch released");
      setOpen(false);
    } catch (e) {
      toast.error("Kill failed", { description: e.message });
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <Panel data-testid="risk-overview-panel" className="lg:col-span-1">
        <PanelHeader>
          <PanelTitle>Risk Overview</PanelTitle>
          <Badge variant="outline" className="font-mono text-[10px]">
            {killed ? "KILLED" : "ARMED"}
          </Badge>
        </PanelHeader>
        <div className="p-3 space-y-3">
          <Stat label="equity" value={fmtUSD(eq)} testid="risk-equity" />
          <Stat
            label="daily PnL"
            value={fmtUSD(dailyPnl)}
            valueClass={dailyPnl >= 0 ? "text-[hsl(var(--bull))]" : "text-[hsl(var(--bear))]"}
            testid="risk-daily-pnl"
          />
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">daily DD vs halt</div>
            <div className="flex justify-between text-xs font-mono mt-0.5">
              <span
                className={
                  dailyDDPct <= -haltPct ? "text-[hsl(var(--bear))]" : "text-foreground"
                }
              >
                {dailyDDPct.toFixed(2)}% / -{haltPct.toFixed(2)}%
              </span>
            </div>
            <div className="mt-1 h-2 bg-[hsl(var(--panel-2))] border border-border rounded-full overflow-hidden">
              <div
                className="h-full bg-[hsl(var(--bear))]"
                style={{ width: `${Math.min(100, (Math.abs(Math.min(dailyDDPct, 0)) / haltPct) * 100)}%` }}
              />
            </div>
          </div>
          <Stat
            label="trades today"
            value={`${tradeCount} / ${cap}`}
            testid="risk-trade-count"
          />
          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button
                data-testid="risk-kill-switch-button"
                className="w-full bg-[hsl(var(--bear))] text-white hover:opacity-90"
                onClick={() => setOpen(true)}
              >
                {killed ? "Release Kill Switch" : "Engage Kill Switch"}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent data-testid="risk-kill-switch-dialog">
              <AlertDialogHeader>
                <AlertDialogTitle>{killed ? "Release Kill Switch?" : "Engage Kill Switch?"}</AlertDialogTitle>
                <AlertDialogDescription>
                  {killed
                    ? "This re-arms the bot. New orders may be placed."
                    : "This cancels all open positions and disables execution."}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  data-testid="risk-kill-switch-confirm-button"
                  onClick={() => toggleKill(!killed)}
                  className="bg-[hsl(var(--bear))] text-white"
                >
                  {killed ? "Release" : "Engage"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </Panel>

      <Panel className="lg:col-span-2" data-testid="risk-equity-curve-panel">
        <PanelHeader>
          <PanelTitle>Equity Curve</PanelTitle>
        </PanelHeader>
        <div className="p-2 h-[200px]" data-testid="risk-equity-curve-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={eqCurve}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="t" stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 10 }} />
              <YAxis stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#0b0f14", border: "1px solid #1a2230" }}
                labelStyle={{ color: "#9ca3af" }}
              />
              <Line type="monotone" dataKey="equity" stroke="#00D1FF" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="px-2 pb-2 h-[160px]" data-testid="risk-daily-dd-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={ddBars}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="i" stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 10 }} />
              <YAxis stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0b0f14", border: "1px solid #1a2230" }} />
              <Bar dataKey="pnl" fill="#FF4D6D" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

function Stat({ label, value, testid, valueClass = "" }) {
  return (
    <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border p-3">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className={`text-lg font-mono tabular-nums ${valueClass}`} data-testid={testid}>
        {value}
      </div>
    </div>
  );
}
