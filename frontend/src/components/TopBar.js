import { useStateStore, useAuthStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import ModeSwitcher from "@/components/ModeSwitcher";

function StatusDot({ s }) {
  const map = {
    connected: "bg-[hsl(var(--bull))]",
    polling: "bg-[hsl(var(--info))]",
    connecting: "bg-[hsl(var(--edge))]",
    idle: "bg-muted-foreground/50",
    error: "bg-[hsl(var(--bear))]",
    disconnected: "bg-muted-foreground/40",
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${map[s] || "bg-muted"}`} />;
}

export default function TopBar() {
  const snap = useStateStore((s) => s.snapshot);
  const auth = useAuthStore();
  const navigate = useNavigate();
  const lat = snap?.latency || {};
  const ws = snap?.ws_status || {};
  const spot = snap?.spot_price || 0;

  return (
    <div className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur-md terminal-bg">
      <div className="flex items-center gap-2 md:gap-4 px-3 md:px-5 py-2">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[hsl(var(--edge))] live-pulse" />
          <span className="font-mono uppercase tracking-widest text-[10px] md:text-xs text-muted-foreground">
            polymarket scalper
          </span>
        </div>

        <div
          className="ml-3 md:ml-6 flex items-baseline gap-2"
          data-testid="topbar-btc-price"
        >
          <span className="text-xs text-muted-foreground">BTC</span>
          <span className="font-mono text-base md:text-lg font-semibold tabular-nums">
            ${spot ? spot.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "---"}
          </span>
        </div>

        <div className="hidden md:flex items-center gap-3 ml-6 font-mono text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5" data-testid="ws-status-coinbase">
            <StatusDot s={ws.coinbase} /> coinbase
          </div>
          <div className="flex items-center gap-1.5" data-testid="ws-status-okx">
            <StatusDot s={ws.okx} /> okx
          </div>
          <div className="flex items-center gap-1.5" data-testid="ws-status-polymarket">
            <StatusDot s={ws.polymarket} /> polymarket
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-2 ml-4 font-mono text-[11px]">
          <Badge variant="outline" data-testid="latency-p50">
            feed P50 {lat.feed_p50 != null ? Math.round(lat.feed_p50) : "—"}ms
          </Badge>
          <Badge variant="outline" data-testid="latency-p95">
            P95 {lat.feed_p95 != null ? Math.round(lat.feed_p95) : "—"}ms
          </Badge>
          <Badge variant="outline" data-testid="latency-p99">
            P99 {lat.feed_p99 != null ? Math.round(lat.feed_p99) : "—"}ms
          </Badge>
          <Badge variant="outline">
            loop P50 {lat.loop_p50 != null ? Math.round(lat.loop_p50) : "—"}ms
          </Badge>
        </div>

        <div className="flex-1" />

        <ModeSwitcher />

        <div className="hidden md:block text-xs text-muted-foreground font-mono">
          {auth.email}
        </div>
        <Button
          size="sm"
          variant="ghost"
          data-testid="topbar-logout-button"
          onClick={() => {
            auth.logout();
            navigate("/login", { replace: true });
          }}
        >
          Logout
        </Button>
      </div>
    </div>
  );
}
