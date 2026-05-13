import { useState } from "react";
import { useStateStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Checkbox } from "@/components/ui/checkbox";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function ModeSwitcher() {
  const mode = useStateStore((s) => s.snapshot?.mode) || "paper";
  const [open, setOpen] = useState(false);
  const [understand, setUnderstand] = useState(false);

  const isLive = mode === "live";

  const activateLive = async () => {
    try {
      const r = await api.post("/mode", { mode: "live", confirm: true });
      toast.success(`Mode → ${r.data.mode.toUpperCase()}`);
      setOpen(false);
    } catch (e) {
      toast.error("Failed to activate LIVE", {
        description: e?.response?.data?.detail || e.message,
      });
    }
  };

  const switchToPaper = async () => {
    try {
      const r = await api.post("/mode", { mode: "paper" });
      toast.success(`Mode → ${r.data.mode.toUpperCase()}`);
    } catch (e) {
      toast.error("Switch failed", { description: e.message });
    }
  };

  if (isLive) {
    return (
      <Badge
        data-testid="mode-pill"
        className="bg-[hsl(var(--edge))]/15 text-[hsl(var(--edge))] border border-[hsl(var(--edge))]/40 live-pulse font-mono text-[11px] cursor-pointer"
        onClick={switchToPaper}
        title="Click to switch to PAPER"
      >
        ● LIVE
      </Badge>
    );
  }

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Badge
          data-testid="mode-pill"
          className="bg-muted text-muted-foreground border border-border font-mono text-[11px] cursor-pointer hover:bg-accent"
          onClick={() => setOpen(true)}
        >
          ○ PAPER
        </Badge>
      </AlertDialogTrigger>
      <AlertDialogContent data-testid="live-mode-activate-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Activate LIVE Trading</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <div>
              You are about to place <span className="text-[hsl(var(--edge))]">real signed orders</span> on Polymarket CLOB.
              Confirm wallet is configured in Settings and you accept risk limits.
            </div>
            <div className="text-xs font-mono mt-2 text-muted-foreground">
              risk_per_trade: 0.5% • daily_DD_halt: 2% • hard_stop: -0.4%
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex items-center gap-2">
          <Checkbox
            id="understand"
            checked={understand}
            onCheckedChange={setUnderstand}
            data-testid="live-mode-activate-understand-checkbox"
          />
          <label htmlFor="understand" className="text-sm text-muted-foreground">
            I understand and accept the risks.
          </label>
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            data-testid="live-mode-activate-confirm-button"
            disabled={!understand}
            onClick={activateLive}
            className="bg-[hsl(var(--edge))] text-black hover:opacity-90"
          >
            Activate LIVE
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
