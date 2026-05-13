import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { toast } from "sonner";

export default function LoginPage() {
  const [email, setEmail] = useState("trader@scalper.local");
  const [password, setPassword] = useState("scalper2026");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await api.post("/auth/login", { email, password });
      setAuth(r.data.token, r.data.email);
      toast.success("Authenticated", { description: r.data.email });
      navigate("/", { replace: true });
    } catch (e2) {
      const msg = e2?.response?.data?.detail || e2.message || "login failed";
      setError(msg);
      toast.error("Login failed", { description: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full grid grid-cols-1 md:grid-cols-2 bg-background text-foreground">
      {/* Left: brand panel */}
      <div className="hidden md:flex flex-col justify-between p-10 border-r border-border terminal-bg relative overflow-hidden">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[hsl(var(--edge))] live-pulse" />
            <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              polymarket scalper terminal
            </span>
          </div>
          <h1 className="text-4xl lg:text-5xl font-semibold leading-tight">
            BTC <span className="text-[hsl(var(--bull))]">UP</span>
            <span className="text-muted-foreground">/</span>
            <span className="text-[hsl(var(--bear))]">DOWN</span>
            <br />
            <span className="text-muted-foreground">5-minute scalper.</span>
          </h1>
          <p className="text-sm md:text-base text-muted-foreground max-w-md">
            Exploits the lag between BTC spot, signal convergence, and Polymarket
            CLOB repricing. Paper mode by default, LIVE behind double confirm.
          </p>
        </div>
        <div className="font-mono text-xs text-muted-foreground space-y-1">
          <div>core: coinbase ws + okx derivatives + polymarket clob</div>
          <div>risk: 0.5% / trade • 2% daily DD • -0.4% hard stop</div>
          <div>edge floor: 0.3% — skip on conflict / low liquidity / cap</div>
        </div>
      </div>

      {/* Right: login card */}
      <div className="flex items-center justify-center p-6 md:p-10">
        <Card className="w-full max-w-sm p-6 rounded-2xl border border-border bg-card shadow-[0_12px_30px_rgba(0,0,0,0.45)]">
          <div className="mb-6">
            <h2 className="text-xl font-semibold">Sign in</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Default demo credentials are pre-filled.
            </p>
          </div>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                data-testid="login-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                data-testid="login-password-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && (
              <div
                className="text-xs text-[hsl(var(--bear))]"
                data-testid="login-error-text"
              >
                {error}
              </div>
            )}
            <Button
              type="submit"
              disabled={loading}
              data-testid="login-form-submit-button"
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
