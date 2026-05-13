import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useStateStore } from "@/lib/store";
import { Panel, PanelHeader, PanelTitle } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ForceGraphPanel() {
  const snap = useStateStore((s) => s.snapshot);
  const graph = snap?.graph || { nodes: [], links: [] };

  const fgRef = useRef(null);
  const containerRef = useRef(null);
  const [size, setSize] = useState({ w: 600, h: 460 });
  const [hoverId, setHoverId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [frozen, setFrozen] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      const r = containerRef.current.getBoundingClientRect();
      setSize({ w: Math.max(320, r.width), h: 460 });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (frozen && fgRef.current) {
      try {
        fgRef.current.pauseAnimation();
      } catch {}
    } else if (fgRef.current) {
      try {
        fgRef.current.resumeAnimation();
      } catch {}
    }
  }, [frozen]);

  const counts = graph.counts || { nodes: graph.nodes.length, edges: graph.links.length };

  return (
    <Panel data-testid="force-graph-panel">
      <PanelHeader>
        <PanelTitle>Market Graph — 100 nodes / 180 edges</PanelTitle>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="font-mono text-[10px]">
            n={counts.nodes} e={counts.edges}
          </Badge>
          <Button
            size="sm"
            variant="ghost"
            data-testid="force-graph-freeze-toggle"
            onClick={() => setFrozen((f) => !f)}
          >
            {frozen ? "resume" : "freeze"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            data-testid="force-graph-zoom-to-fit-button"
            onClick={() => fgRef.current?.zoomToFit?.(350, 40)}
          >
            fit
          </Button>
        </div>
      </PanelHeader>
      <div className="grid grid-cols-1 lg:grid-cols-3">
        <div ref={containerRef} className="col-span-2 h-[460px]" data-testid="force-graph-canvas">
          <ForceGraph2D
            ref={fgRef}
            width={size.w}
            height={size.h}
            graphData={graph}
            backgroundColor="#0b0f14"
            nodeRelSize={4}
            cooldownTicks={80}
            warmupTicks={10}
            linkColor={(l) =>
              (hoverId && (l.source.id === hoverId || l.target.id === hoverId)) ||
              (selected && (l.source.id === selected.id || l.target.id === selected.id))
                ? "rgba(255,255,255,0.75)"
                : "rgba(0,209,255,0.22)"
            }
            linkWidth={(l) =>
              (hoverId && (l.source.id === hoverId || l.target.id === hoverId)) ? 2 : 1
            }
            onNodeHover={(n) => setHoverId(n ? n.id : null)}
            onNodeClick={(n) => setSelected(n)}
            nodeCanvasObject={(node, ctx, scale) => {
              const r = node.val ? Math.max(3, Math.min(7, node.val / 3)) : 4;
              const hot = hoverId === node.id || selected?.id === node.id;
              ctx.beginPath();
              ctx.arc(node.x, node.y, hot ? r + 1.5 : r, 0, 2 * Math.PI);
              ctx.fillStyle = node.color || "#00D1FF";
              ctx.fill();
              ctx.lineWidth = 1;
              ctx.strokeStyle = "rgba(255,255,255,0.22)";
              ctx.stroke();
              if (hot) {
                const label = node.label || node.id;
                ctx.font = `${10 / scale}px IBM Plex Mono, monospace`;
                ctx.fillStyle = "rgba(255,255,255,0.95)";
                ctx.textAlign = "center";
                ctx.fillText(label.slice(0, 32), node.x, node.y + r + 8 / scale);
              }
            }}
          />
        </div>

        <div
          className="col-span-1 border-l border-border p-3 text-xs space-y-3"
          data-testid="force-graph-inspector"
        >
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">Selected node</div>
            <div className="font-mono text-sm break-all">
              {selected?.label || selected?.id || "— (click a node)"}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Stat k="group" v={selected?.group || "—"} />
            <Stat k="score" v={selected?.score != null ? Number(selected.score).toFixed(2) : "—"} />
            <Stat k="val" v={selected?.val != null ? Number(selected.val).toFixed(2) : "—"} />
            <Stat k="color" v={selected?.color || "—"} />
          </div>
          <div className="pt-2 border-t border-border">
            <div className="text-[10px] uppercase text-muted-foreground mb-1">Legend</div>
            <div className="grid grid-cols-2 gap-1 text-[11px]">
              <Legend color="#00D1FF" label="price" />
              <Legend color="#2EE59D" label="ta" />
              <Legend color="#A3E635" label="flow" />
              <Legend color="#FFB84D" label="derivs" />
              <Legend color="#7DD3FC" label="market" />
              <Legend color="#FF4D6D" label="edge" />
              <Legend color="#FFE066" label="signal" />
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function Stat({ k, v }) {
  return (
    <div className="rounded-md bg-[hsl(var(--panel-2))] border border-border px-2 py-1.5">
      <div className="text-[10px] text-muted-foreground">{k}</div>
      <div className="font-mono">{v}</div>
    </div>
  );
}

function Legend({ color, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}
