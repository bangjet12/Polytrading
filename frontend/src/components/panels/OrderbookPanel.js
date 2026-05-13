import { useMemo } from "react";
import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function fmt(n, d = 3) {
  if (n == null || isNaN(n)) return "—";
  return Number(n).toFixed(d);
}
function fmtUSD(n) {
  if (n == null || isNaN(n)) return "—";
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export default function OrderbookPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const markets = snap?.markets || [];
  const selected = snap?.selected_market;
  const book = snap?.selected_book || {};
  const yes = book.yes || {};
  const no = book.no || {};
  const strict5m = !!snap?.strict_5m_only;
  const targetPrice = selected
    ? (snap?.market_refs || {})[selected.market_id]?.target_price
    : null;
  const spot = snap?.spot_price || 0;

  const visibleMarkets = useMemo(() => {
    if (strict5m) return markets.filter((m) => m.market_type === "5m_updown");
    return markets;
  }, [markets, strict5m]);

  const maxBidSize = useMemo(() => {
    const sizes = (yes.bids || []).map((r) => r[1]);
    return sizes.length ? Math.max(...sizes) : 1;
  }, [yes.bids]);
  const maxAskSize = useMemo(() => {
    const sizes = (yes.asks || []).map((r) => r[1]);
    return sizes.length ? Math.max(...sizes) : 1;
  }, [yes.asks]);

  const onSelectMarket = async (mid) => {
    try {
      await api.post("/select_market", { market_id: mid });
      toast.success("Market selected");
    } catch (e) {
      toast.error("Select failed", { description: e.message });
    }
  };

  const onToggleStrict = async (val) => {
    try {
      await api.post("/strict_5m", { strict_5m_only: val });
      toast.success(val ? "Strict 5m mode ON" : "All markets visible");
    } catch (e) {
      toast.error("Toggle failed", { description: e.message });
    }
  };

  return (
    <Panel data-testid="orderbook-panel">
      <PanelHeader>
        <PanelTitle>Polymarket CLOB</PanelTitle>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase text-muted-foreground">5m only</span>
            <Switch
              checked={strict5m}
              onCheckedChange={onToggleStrict}
              data-testid="strict-5m-toggle"
            />
          </div>
          <Badge variant="outline" className="font-mono text-[10px]">
            {selected?.market_type || "—"}
          </Badge>
          <Badge variant="outline" className="font-mono text-[10px]">
            +{selected?.minutes_to_expiry ? selected.minutes_to_expiry.toFixed(1) : "—"}m
          </Badge>
        </div>
      </PanelHeader>
      <div className="p-3 space-y-3">
        <Select
          value={selected?.market_id || ""}
          onValueChange={onSelectMarket}
        >
          <SelectTrigger data-testid="orderbook-market-select" className="w-full">
            <SelectValue placeholder={strict5m ? "Waiting for next 5m market…" : "Pick a BTC market"} />
          </SelectTrigger>
          <SelectContent className="max-h-80">
            {visibleMarkets.slice(0, 40).map((m) => (
              <SelectItem key={m.market_id} value={m.market_id}>
                <span className="font-mono text-[11px] mr-2">[{m.market_type}]</span>
                {m.question?.slice(0, 70)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div
          className="text-xs text-muted-foreground line-clamp-2"
          data-testid="orderbook-selected-question"
        >
          {selected?.question || (strict5m ? "Auto-cycling 5m markets…" : "No market selected")}
        </div>

        {/* Target vs Spot like Polymarket UI */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border px-3 py-2">
            <div className="text-[10px] text-muted-foreground uppercase">Target price</div>
            <div
              className="text-lg font-mono tabular-nums text-muted-foreground"
              data-testid="orderbook-target-price"
            >
              {targetPrice != null
                ? `$${targetPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                : "—"}
            </div>
          </div>
          <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border px-3 py-2">
            <div className="text-[10px] text-muted-foreground uppercase">Spot now</div>
            <div
              className={`text-lg font-mono tabular-nums ${
                targetPrice != null && spot >= targetPrice
                  ? "text-[hsl(var(--bull))]"
                  : "text-[hsl(var(--bear))]"
              }`}
              data-testid="orderbook-spot-now"
            >
              {spot ? `$${spot.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Stat label="YES mid" value={fmt(yes.mid)} testid="orderbook-yes-mid" />
          <Stat label="NO mid" value={fmt(no.mid)} testid="orderbook-no-mid" />
          <Stat
            label="spread"
            value={yes.spread != null ? `${(yes.spread * 100).toFixed(2)}%` : "—"}
          />
          <Stat label="depth (YES)" value={fmtUSD((yes.depth_bid || 0) + (yes.depth_ask || 0))} />
        </div>

        <div className="grid grid-cols-2 gap-3" data-testid="orderbook-rows">
          {/* Bids (YES) */}
          <div className="rounded-md border border-border">
            <div className="px-2 py-1.5 text-[11px] text-muted-foreground border-b border-border/70 flex justify-between">
              <span>YES Bids</span>
              <span>n={yes.n_bids || 0}</span>
            </div>
            <div className="max-h-60 overflow-auto subtle-scroll">
              <table className="w-full text-xs">
                <tbody>
                  {(yes.bids || []).slice(0, 12).map((r, i) => (
                    <tr key={i} className="relative">
                      <td className="relative px-2 py-1 text-[hsl(var(--bull))] font-mono tabular-nums w-1/2">
                        <span
                          className="absolute inset-y-0 right-0 bg-[hsl(var(--bull))]/15"
                          style={{ width: `${(r[1] / maxBidSize) * 100}%` }}
                        />
                        <span className="relative">{fmt(r[0])}</span>
                      </td>
                      <td className="px-2 py-1 text-right text-muted-foreground font-mono tabular-nums">
                        {Math.round(r[1])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {/* Asks (YES) */}
          <div className="rounded-md border border-border">
            <div className="px-2 py-1.5 text-[11px] text-muted-foreground border-b border-border/70 flex justify-between">
              <span>YES Asks</span>
              <span>n={yes.n_asks || 0}</span>
            </div>
            <div className="max-h-60 overflow-auto subtle-scroll">
              <table className="w-full text-xs">
                <tbody>
                  {(yes.asks || []).slice(0, 12).map((r, i) => (
                    <tr key={i} className="relative">
                      <td className="relative px-2 py-1 text-[hsl(var(--bear))] font-mono tabular-nums w-1/2">
                        <span
                          className="absolute inset-y-0 right-0 bg-[hsl(var(--bear))]/15"
                          style={{ width: `${(r[1] / maxAskSize) * 100}%` }}
                        />
                        <span className="relative">{fmt(r[0])}</span>
                      </td>
                      <td className="px-2 py-1 text-right text-muted-foreground font-mono tabular-nums">
                        {Math.round(r[1])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function Stat({ label, value, testid }) {
  return (
    <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border px-2 py-1.5">
      <div className="text-[10px] text-muted-foreground uppercase">{label}</div>
      <div className="text-base font-mono tabular-nums" data-testid={testid}>
        {value}
      </div>
    </div>
  );
}
