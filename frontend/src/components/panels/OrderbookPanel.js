import { useMemo } from "react";
import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Badge } from "@/components/ui/badge";
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

  return (
    <Panel data-testid="orderbook-panel">
      <PanelHeader>
        <PanelTitle>Polymarket CLOB</PanelTitle>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px]">
            {selected?.market_type || "—"}
          </Badge>
          <Badge variant="outline" className="font-mono text-[10px]">
            +{selected?.minutes_to_expiry ? Math.round(selected.minutes_to_expiry) : "—"}m
          </Badge>
        </div>
      </PanelHeader>
      <div className="p-3 space-y-3">
        <Select
          value={selected?.market_id || ""}
          onValueChange={onSelectMarket}
        >
          <SelectTrigger data-testid="orderbook-market-select" className="w-full">
            <SelectValue placeholder="Pick a BTC market" />
          </SelectTrigger>
          <SelectContent className="max-h-80">
            {markets.slice(0, 40).map((m) => (
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
          {selected?.question || "No market selected"}
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
