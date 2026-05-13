import { useEffect, useState } from "react";
import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function SettingsPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const settings = snap?.settings || {};
  const [form, setForm] = useState({ ...settings });
  const [walletStatus, setWalletStatus] = useState(null);
  const [wallet, setWallet] = useState({
    private_key: "",
    funder_address: "",
    api_key: "",
    api_secret: "",
    api_passphrase: "",
  });

  useEffect(() => {
    setForm((f) => ({ ...settings, ...f }));
    api.get("/wallet/status").then((r) => setWalletStatus(r.data)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap?.settings && Object.keys(snap.settings).length]);

  const onSave = async () => {
    try {
      const r = await api.put("/settings", form);
      toast.success("Settings saved");
      setForm({ ...r.data });
    } catch (e) {
      toast.error("Save failed", { description: e.message });
    }
  };

  const onSaveWallet = async () => {
    try {
      const payload = Object.fromEntries(Object.entries(wallet).filter(([_, v]) => v));
      const r = await api.post("/wallet/config", payload);
      setWalletStatus(r.data.configured);
      toast.success("Wallet config saved (memory-only)");
      setWallet({
        private_key: "",
        funder_address: "",
        api_key: "",
        api_secret: "",
        api_passphrase: "",
      });
    } catch (e) {
      toast.error("Wallet config failed", { description: e.message });
    }
  };

  const setF = (k) => (e) => setForm((s) => ({ ...s, [k]: parseFloat(e.target.value) }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Panel data-testid="settings-strategy-panel">
        <PanelHeader>
          <PanelTitle>Strategy Thresholds</PanelTitle>
          <Badge variant="outline" className="font-mono text-[10px]">
            risk + skip rules
          </Badge>
        </PanelHeader>
        <div className="p-4 grid grid-cols-2 gap-3 text-xs">
          <Field label="risk per trade %" v={form.risk_per_trade_pct} onChange={setF("risk_per_trade_pct")} step="0.001" testid="settings-risk-per-trade" />
          <Field label="daily DD halt %" v={form.daily_dd_halt_pct} onChange={setF("daily_dd_halt_pct")} step="0.005" testid="settings-daily-dd-halt" />
          <Field label="hard stop %" v={form.hard_stop_pct} onChange={setF("hard_stop_pct")} step="0.001" testid="settings-hard-stop" />
          <Field label="edge threshold" v={form.edge_threshold} onChange={setF("edge_threshold")} step="0.001" testid="settings-edge-threshold" />
          <Field label="max edge (skip if larger)" v={form.max_edge_threshold} onChange={setF("max_edge_threshold")} step="0.01" testid="settings-max-edge" />
          <Field label="min liquidity (book size)" v={form.min_liquidity_usd} onChange={setF("min_liquidity_usd")} step="10" testid="settings-min-liquidity" />
          <Field label="max spread" v={form.max_spread} onChange={setF("max_spread")} step="0.005" testid="settings-max-spread" />
          <Field label="daily trade cap" v={form.daily_trade_cap} onChange={setF("daily_trade_cap")} step="10" testid="settings-daily-cap" />
          <div className="col-span-2">
            <Button onClick={onSave} className="w-full" data-testid="settings-save-button">
              Save thresholds
            </Button>
          </div>
        </div>
      </Panel>

      <Panel data-testid="settings-wallet-panel">
        <PanelHeader>
          <PanelTitle>Wallet & API (LIVE only)</PanelTitle>
          <Badge
            variant="outline"
            className={`font-mono text-[10px] ${walletStatus?.private_key ? "text-[hsl(var(--bull))]" : "text-muted-foreground"}`}
          >
            {walletStatus?.private_key ? "configured" : "not configured"}
          </Badge>
        </PanelHeader>
        <div className="p-4 space-y-3 text-xs">
          <div className="rounded-md border border-[hsl(var(--edge))]/30 bg-[hsl(var(--edge))]/5 p-3 text-[11px] leading-relaxed space-y-1.5">
            <div className="text-[hsl(var(--edge))] font-medium">How to enable LIVE trading</div>
            <ol className="list-decimal list-inside text-muted-foreground space-y-1">
              <li>Get a <strong>Polygon proxy wallet private key</strong> from your Polymarket account (Profile → Export Private Key).</li>
              <li>Fund the proxy with USDC.e on Polygon (this is your trading bankroll).</li>
              <li>Set <strong>Funder address</strong> = your Polymarket proxy wallet address (0x…).</li>
              <li>Generate <strong>API key / secret / passphrase</strong> using <code className="font-mono">/auth/api-key</code> on <code className="font-mono">clob.polymarket.com</code>.</li>
              <li>Paste all 5 fields below and click <strong>Save wallet config</strong>.</li>
              <li>Top-right pill: click <strong>PAPER</strong> → confirm → LIVE pulse turns red.</li>
              <li>Bot will auto-execute on next lag-edge in any <code className="font-mono">BTC Up or Down 5m</code> market.</li>
            </ol>
            <div className="text-[10px] text-muted-foreground pt-1">Secrets kept in <em>process memory only</em>. To persist, set them in <code className="font-mono">/app/backend/.env</code> and restart backend.</div>
          </div>
          <WalletField id="pk" label="Polygon private key (0x…)" value={wallet.private_key} onChange={(v) => setWallet((w) => ({ ...w, private_key: v }))} type="password" testid="settings-wallet-pk" />
          <WalletField id="funder" label="Funder address (proxy wallet)" value={wallet.funder_address} onChange={(v) => setWallet((w) => ({ ...w, funder_address: v }))} testid="settings-wallet-funder" />
          <WalletField id="ak" label="Polymarket API key" value={wallet.api_key} onChange={(v) => setWallet((w) => ({ ...w, api_key: v }))} testid="settings-wallet-api-key" />
          <WalletField id="as" label="Polymarket API secret" value={wallet.api_secret} onChange={(v) => setWallet((w) => ({ ...w, api_secret: v }))} type="password" testid="settings-wallet-api-secret" />
          <WalletField id="ap" label="Polymarket API passphrase" value={wallet.api_passphrase} onChange={(v) => setWallet((w) => ({ ...w, api_passphrase: v }))} type="password" testid="settings-wallet-api-passphrase" />
          <Button onClick={onSaveWallet} className="w-full" data-testid="settings-wallet-save-button">
            Save wallet config (memory only)
          </Button>
          <div className="text-[11px] text-muted-foreground border-t border-border pt-2 space-y-1">
            <div>TradingView webhook URL:</div>
            <code className="block break-all bg-[hsl(var(--panel-2))] border border-border rounded p-2 text-[10px]">
              {process.env.REACT_APP_BACKEND_URL}/api/webhooks/tradingview
            </code>
            <div>Send POST with JSON body including <code className="font-mono">secret</code>, <code className="font-mono">action</code> (BUY/SELL), and optional metadata.</div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

function Field({ label, v, onChange, step = "0.001", testid }) {
  return (
    <div>
      <Label className="text-[11px] text-muted-foreground">{label}</Label>
      <Input
        type="number"
        step={step}
        value={v ?? ""}
        onChange={onChange}
        data-testid={testid}
        className="font-mono tabular-nums"
      />
    </div>
  );
}

function WalletField({ id, label, value, onChange, type = "text", testid }) {
  return (
    <div>
      <Label htmlFor={id} className="text-[11px] text-muted-foreground">{label}</Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="off"
        data-testid={testid}
        className="font-mono text-xs"
      />
    </div>
  );
}
