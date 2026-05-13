import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { useStateStore } from "@/lib/store";

export default function CandlestickPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const candles = useMemo(() => (snap?.candles_5m || []).slice(-200), [snap?.candles_5m]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (chartRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 360,
      localization: { locale: "en-US" },
      layout: {
        background: { color: "#0b0f14" },
        textColor: "rgba(255,255,255,0.75)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: true, secondsVisible: false },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#2EE59D",
      downColor: "#FF4D6D",
      borderUpColor: "#2EE59D",
      borderDownColor: "#FF4D6D",
      wickUpColor: "#2EE59D",
      wickDownColor: "#FF4D6D",
    });
    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chart) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      try {
        chart.remove();
      } catch {}
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    const data = candles.map((c) => ({
      time: c.t,
      open: c.o,
      high: c.h,
      low: c.l,
      close: c.c,
    }));
    seriesRef.current.setData(data);
  }, [candles]);

  const spot = snap?.spot_price || 0;
  const lastClose = candles.length ? candles[candles.length - 1].c : 0;
  const change = lastClose ? ((spot - lastClose) / lastClose) * 100 : 0;

  return (
    <Panel data-testid="candlestick-panel">
      <PanelHeader>
        <PanelTitle>BTC-USD · 5m · Coinbase</PanelTitle>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="tabular-nums" data-testid="candlestick-spot">
            ${spot ? spot.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "---"}
          </span>
          <span
            className={`tabular-nums ${change >= 0 ? "text-[hsl(var(--bull))]" : "text-[hsl(var(--bear))]"}`}
          >
            {change >= 0 ? "+" : ""}{change.toFixed(3)}%
          </span>
        </div>
      </PanelHeader>
      <div ref={containerRef} className="w-full" data-testid="candlestick-chart" style={{ height: 360 }} />
    </Panel>
  );
}
