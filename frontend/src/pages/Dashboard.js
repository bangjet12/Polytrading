import { useEffect, useRef } from "react";
import TopBar from "@/components/TopBar";
import CandlestickPanel from "@/components/panels/CandlestickPanel";
import OrderbookPanel from "@/components/panels/OrderbookPanel";
import EdgeMeterPanel from "@/components/panels/EdgeMeterPanel";
import SignalsPanel from "@/components/panels/SignalsPanel";
import ForceGraphPanel from "@/components/panels/ForceGraphPanel";
import TradesPanel from "@/components/panels/TradesPanel";
import RiskPanel from "@/components/panels/RiskPanel";
import SettingsPanel from "@/components/panels/SettingsPanel";
import TradingViewLogPanel from "@/components/panels/TradingViewLogPanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLiveState } from "@/lib/useLiveState";
import { useStateStore } from "@/lib/store";
import { toast } from "sonner";

export default function DashboardPage() {
  useLiveState();
  const snap = useStateStore((s) => s.snapshot);
  const lastEdgeRef = useRef(null);
  const lastJournalLenRef = useRef(0);

  // Edge alert toast
  useEffect(() => {
    const e = snap?.edge;
    if (!e) return;
    if (e.has_edge) {
      const key = `${e.direction}-${Math.round((e.edge || 0) * 1000)}`;
      if (lastEdgeRef.current !== key) {
        lastEdgeRef.current = key;
        toast(
          `Edge ${((e.edge || 0) * 100).toFixed(2)}% → ${e.direction}`,
          {
            description: snap?.selected_market?.question?.slice(0, 60) || "",
          }
        );
      }
    }
  }, [snap?.edge, snap?.selected_market]);

  // Trade alert toast
  useEffect(() => {
    const j = snap?.trade_journal || [];
    if (j.length > lastJournalLenRef.current && lastJournalLenRef.current > 0) {
      const newest = j[j.length - 1];
      const ev = newest?.event;
      if (ev === "open") {
        toast.success(
          `Open — ${newest.position?.direction} @ ${Number(newest.position?.entry_price).toFixed(3)}`,
          { description: newest.position?.market_question?.slice(0, 60) }
        );
      } else if (ev === "take_profit") {
        toast.success(`Take profit — $${Number(newest.position?.realized_pnl || 0).toFixed(2)}`);
      } else if (ev === "hard_stop") {
        toast.error(`Hard stop — $${Number(newest.position?.realized_pnl || 0).toFixed(2)}`);
      }
    }
    lastJournalLenRef.current = j.length;
  }, [snap?.trade_journal]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopBar />
      <div className="p-3 md:p-5">
        <Tabs defaultValue="live" className="w-full">
          <TabsList
            className="flex flex-wrap gap-1 bg-card border border-border rounded-lg p-1"
            data-testid="dashboard-tabs"
          >
            <TabsTrigger value="live" data-testid="tab-live">
              Live Monitor
            </TabsTrigger>
            <TabsTrigger value="signals" data-testid="tab-signals">
              Signals
            </TabsTrigger>
            <TabsTrigger value="graph" data-testid="tab-graph">
              Force-Graph
            </TabsTrigger>
            <TabsTrigger value="trades" data-testid="tab-trades">
              Trades
            </TabsTrigger>
            <TabsTrigger value="risk" data-testid="tab-risk">
              Risk
            </TabsTrigger>
            <TabsTrigger value="settings" data-testid="tab-settings">
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="live" className="mt-3 space-y-3" data-testid="tab-content-live">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-8 space-y-3">
                <CandlestickPanel />
                <EdgeMeterPanel />
              </div>
              <div className="lg:col-span-4 space-y-3">
                <OrderbookPanel />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="signals" className="mt-3 space-y-3" data-testid="tab-content-signals">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <SignalsPanel />
              <TradingViewLogPanel />
            </div>
          </TabsContent>

          <TabsContent value="graph" className="mt-3" data-testid="tab-content-graph">
            <ForceGraphPanel />
          </TabsContent>

          <TabsContent value="trades" className="mt-3" data-testid="tab-content-trades">
            <TradesPanel />
          </TabsContent>

          <TabsContent value="risk" className="mt-3" data-testid="tab-content-risk">
            <RiskPanel />
          </TabsContent>

          <TabsContent value="settings" className="mt-3" data-testid="tab-content-settings">
            <SettingsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
