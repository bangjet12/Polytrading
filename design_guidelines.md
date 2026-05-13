{
  "meta": {
    "product": "Polymarket BTC 5m Scalper — Pro Trading Terminal",
    "design_personality": [
      "war-room terminal",
      "precision + speed",
      "high information density",
      "low eye-fatigue dark theme",
      "color used as signal (not decoration)"
    ],
    "north_star": "Bloomberg Terminal structure + modern crypto exchange UI (Hyperliquid/dYdX/Drift) with strict risk controls and real-time telemetry.",
    "non_goals": [
      "marketing/landing-page aesthetics",
      "playful gradients",
      "centered single-column layouts",
      "heavy animations on live data"
    ],
    "testing_requirement": {
      "rule": "All interactive and key informational elements MUST include data-testid (kebab-case, role-based).",
      "examples": [
        "data-testid=\"login-form-submit-button\"",
        "data-testid=\"orderbook-mid-price\"",
        "data-testid=\"risk-kill-switch-button\"",
        "data-testid=\"live-mode-activate-confirm-button\"",
        "data-testid=\"force-graph-zoom-to-fit-button\""
      ]
    },
    "js_only_note": "Project uses .js (not .tsx). All examples/components should be written in React .js with prop-types optional."
  },

  "inspiration_refs": {
    "visual_refs": [
      {
        "name": "Hyperliquid-style trading terminal (Dribbble search reference)",
        "url": "https://dribbble.com/shots/27340433-Crypto-Trading-Platform-Design-Hyperliquid-Exchange",
        "takeaways": [
          "tight grid, modular panels",
          "high-contrast numbers",
          "accent colors only for state",
          "top bar with market + latency"
        ]
      },
      {
        "name": "Dark trading UI patterns (Dribbble search)",
        "url": "https://dribbble.com/search/dark-mode-trading",
        "takeaways": [
          "orderbook + chart split",
          "tabbed sub-panels",
          "dense tables with sticky headers"
        ]
      },
      {
        "name": "react-force-graph docs/examples",
        "url": "https://github.com/vasturiano/react-force-graph",
        "takeaways": [
          "canvas-based rendering",
          "custom nodeCanvasObject for labels/glow",
          "zoomToFit + cameraPosition for focus",
          "performance knobs: cooldownTicks, warmupTicks"
        ]
      }
    ]
  },

  "design_tokens": {
    "fonts": {
      "ui_sans": {
        "family": "Space Grotesk",
        "fallback": "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
        "usage": "Navigation, labels, headings (short), buttons"
      },
      "numbers_mono": {
        "family": "IBM Plex Mono",
        "fallback": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace",
        "usage": "Prices, sizes, PnL, latency, timestamps, orderbook"
      },
      "implementation": {
        "google_fonts": [
          "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
        ],
        "tailwind_notes": [
          "Set body font to Space Grotesk; apply font-mono to numeric blocks.",
          "Use tabular-nums for aligned digits: className=\"tabular-nums\""
        ]
      }
    },

    "type_scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs",
      "numeric": {
        "price_primary": "text-xl md:text-2xl font-mono tabular-nums",
        "price_secondary": "text-sm font-mono tabular-nums",
        "table": "text-xs md:text-sm font-mono tabular-nums"
      }
    },

    "color_system": {
      "strategy": "Neutral-first dark palette; accents reserved for BULL/BEAR/EDGE/ALERT. Avoid purple. Keep gradients minimal and only as subtle background wash (<20% viewport).",
      "css_custom_properties": {
        "note": "These should replace current :root/.dark tokens in /app/frontend/src/index.css to match terminal aesthetic.",
        "root_dark": {
          "--background": "220 18% 6%",
          "--foreground": "210 20% 96%",
          "--card": "220 18% 8%",
          "--card-foreground": "210 20% 96%",
          "--popover": "220 18% 8%",
          "--popover-foreground": "210 20% 96%",

          "--primary": "210 20% 96%",
          "--primary-foreground": "220 18% 8%",

          "--secondary": "220 14% 14%",
          "--secondary-foreground": "210 20% 96%",

          "--muted": "220 14% 14%",
          "--muted-foreground": "215 12% 70%",

          "--accent": "220 14% 14%",
          "--accent-foreground": "210 20% 96%",

          "--border": "220 12% 18%",
          "--input": "220 12% 18%",
          "--ring": "190 95% 55%",

          "--destructive": "0 72% 52%",
          "--destructive-foreground": "210 20% 96%",

          "--radius": "0.75rem",

          "--chart-1": "190 95% 55%",
          "--chart-2": "145 70% 45%",
          "--chart-3": "0 72% 52%",
          "--chart-4": "38 92% 55%",
          "--chart-5": "210 10% 70%"
        },
        "semantic_extras_add": {
          "--bull": "145 70% 45%",
          "--bear": "0 72% 52%",
          "--edge": "38 92% 55%",
          "--info": "190 95% 55%",
          "--warn": "38 92% 55%",
          "--ok": "145 70% 45%",
          "--panel": "220 18% 8%",
          "--panel-2": "220 16% 10%",
          "--hairline": "220 12% 18%",
          "--focus": "190 95% 55%"
        }
      },
      "tailwind_usage_examples": {
        "backgrounds": [
          "bg-background",
          "bg-card",
          "bg-[hsl(var(--panel))]",
          "bg-[hsl(var(--panel-2))]"
        ],
        "text": [
          "text-foreground",
          "text-muted-foreground",
          "text-[hsl(var(--bull))]",
          "text-[hsl(var(--bear))]",
          "text-[hsl(var(--edge))]"
        ],
        "borders": [
          "border-border",
          "border-[hsl(var(--hairline))]"
        ],
        "rings": [
          "focus-visible:ring-2 focus-visible:ring-[hsl(var(--focus))] focus-visible:ring-offset-0"
        ]
      }
    },

    "gradients_and_texture": {
      "allowed": [
        {
          "name": "Subtle terminal wash (top header only)",
          "css": "radial-gradient(900px circle at 20% -10%, rgba(0, 209, 255, 0.10), transparent 55%), radial-gradient(700px circle at 80% 0%, rgba(255, 184, 77, 0.08), transparent 50%)",
          "usage": "Top app header background overlay; keep under 20% viewport height"
        }
      ],
      "noise_overlay": {
        "css": "background-image: url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"120\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.8\" numOctaves=\"3\" stitchTiles=\"stitch\"/></filter><rect width=\"120\" height=\"120\" filter=\"url(%23n)\" opacity=\"0.06\"/></svg>')",
        "usage": "Apply to app shell via pseudo-element (pointer-events none). Keep opacity 0.04–0.08."
      },
      "restriction": "Follow GRADIENT RESTRICTION RULE (no saturated purple/pink gradients; no gradients on small elements; no gradients on reading areas)."
    },

    "spacing_and_density": {
      "principle": "Dense but breathable: use more spacing between panels than inside tables.",
      "panel_padding": "p-3 md:p-4",
      "panel_gap": "gap-3 md:gap-4",
      "table_cell_padding": "py-1.5 px-2 md:py-2 md:px-2.5",
      "row_height": "leading-5"
    },

    "shadows_and_strokes": {
      "stroke": "Prefer 1px hairlines (border-border) + subtle inner highlight.",
      "shadow": [
        "shadow-[0_0_0_1px_rgba(255,255,255,0.04)]",
        "shadow-[0_12px_30px_rgba(0,0,0,0.45)]"
      ],
      "glass_rule": "Avoid heavy glassmorphism; use only for modals/overlays with subtle blur (backdrop-blur-sm)."
    }
  },

  "layout": {
    "app_shell": {
      "structure": "Top command bar + left rail (optional on desktop) + main grid panels. Mobile uses tabs-first navigation.",
      "mobile_first": {
        "nav": "Use shadcn Tabs as primary navigation on mobile (Live, Signals, Graph, Trades, Risk, Settings).",
        "panels": "Single column stack; each panel collapsible (shadcn Collapsible) with sticky mini-header."
      },
      "desktop_grid": {
        "grid": "12-col CSS grid; 24px outer padding; 16px gutters.",
        "recommended": [
          "Top bar: full width",
          "Left column (4/12): Orderbook + Edge Meter + Latency",
          "Center (5/12): Candlestick + Positions",
          "Right (3/12): Signals + Convergence Gauge + Quick Trade",
          "Lower row: Force-Graph full width (or 8/12) + Journal/Risk (remaining)"
        ],
        "tailwind_scaffold": "grid grid-cols-1 lg:grid-cols-12 gap-3 md:gap-4"
      },
      "panel_chrome": {
        "header": "Panel header row with title (sans), right-side actions (icon buttons), and status dot.",
        "classes": "rounded-xl border border-border bg-card/90",
        "header_classes": "flex items-center justify-between px-3 py-2 border-b border-border/70"
      }
    },

    "key_panels": {
      "live_monitor": [
        "Candlestick 5m (primary)",
        "Orderbook (YES/NO) + depth",
        "Edge meter + lag detector",
        "Latency stats (P50/P95/P99)"
      ],
      "signals": [
        "RSI, EMA cross, funding, OI, taker imbalance",
        "TradingView webhook log (stream)"
      ],
      "force_graph": [
        "100 nodes / 180 edges force-directed graph",
        "Cluster legend + filters",
        "Selected node inspector"
      ],
      "trades": [
        "Active positions",
        "Order queue",
        "Trade journal + PnL"
      ],
      "risk": [
        "Equity curve",
        "Daily DD bar",
        "Kill-switch + limits"
      ],
      "settings": [
        "Paper/Live toggle",
        "Wallet config",
        "Thresholds",
        "Skip rules"
      ]
    }
  },

  "components": {
    "component_path": {
      "shadcn_primary": "/app/frontend/src/components/ui/",
      "use_components": [
        { "name": "button", "path": "/app/frontend/src/components/ui/button.jsx" },
        { "name": "card", "path": "/app/frontend/src/components/ui/card.jsx" },
        { "name": "tabs", "path": "/app/frontend/src/components/ui/tabs.jsx" },
        { "name": "table", "path": "/app/frontend/src/components/ui/table.jsx" },
        { "name": "badge", "path": "/app/frontend/src/components/ui/badge.jsx" },
        { "name": "tooltip", "path": "/app/frontend/src/components/ui/tooltip.jsx" },
        { "name": "hover-card", "path": "/app/frontend/src/components/ui/hover-card.jsx" },
        { "name": "scroll-area", "path": "/app/frontend/src/components/ui/scroll-area.jsx" },
        { "name": "separator", "path": "/app/frontend/src/components/ui/separator.jsx" },
        { "name": "resizable", "path": "/app/frontend/src/components/ui/resizable.jsx" },
        { "name": "dialog", "path": "/app/frontend/src/components/ui/dialog.jsx" },
        { "name": "alert-dialog", "path": "/app/frontend/src/components/ui/alert-dialog.jsx" },
        { "name": "switch", "path": "/app/frontend/src/components/ui/switch.jsx" },
        { "name": "slider", "path": "/app/frontend/src/components/ui/slider.jsx" },
        { "name": "input", "path": "/app/frontend/src/components/ui/input.jsx" },
        { "name": "select", "path": "/app/frontend/src/components/ui/select.jsx" },
        { "name": "sonner", "path": "/app/frontend/src/components/ui/sonner.jsx" },
        { "name": "skeleton", "path": "/app/frontend/src/components/ui/skeleton.jsx" },
        { "name": "collapsible", "path": "/app/frontend/src/components/ui/collapsible.jsx" }
      ]
    },

    "buttons": {
      "style": "Professional / Corporate with action-first emphasis",
      "variants": {
        "primary": {
          "usage": "Place order, confirm live mode, apply settings",
          "classes": "rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.99]",
          "focus": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--focus))]"
        },
        "secondary": {
          "usage": "Panel actions (refresh, reset zoom)",
          "classes": "rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80"
        },
        "ghost": {
          "usage": "Icon-only actions in headers",
          "classes": "rounded-md hover:bg-accent/60"
        },
        "danger": {
          "usage": "Kill-switch, cancel all",
          "classes": "rounded-lg bg-[hsl(var(--bear))] text-white hover:opacity-90"
        }
      },
      "sizes": {
        "sm": "h-8 px-2.5 text-xs",
        "md": "h-9 px-3 text-sm",
        "lg": "h-10 px-4 text-sm"
      }
    },

    "badges_and_state": {
      "bull_badge": "bg-[hsl(var(--bull))]/15 text-[hsl(var(--bull))] border border-[hsl(var(--bull))]/25",
      "bear_badge": "bg-[hsl(var(--bear))]/15 text-[hsl(var(--bear))] border border-[hsl(var(--bear))]/25",
      "edge_badge": "bg-[hsl(var(--edge))]/15 text-[hsl(var(--edge))] border border-[hsl(var(--edge))]/25",
      "neutral_badge": "bg-muted text-muted-foreground border border-border"
    },

    "tables_orderbook": {
      "principles": [
        "Monospace + tabular nums",
        "Right-align numeric columns",
        "Use subtle row hover only (no animated transitions on live rows)",
        "Sticky header for scrollable orderbook"
      ],
      "classes": {
        "table": "w-full text-xs md:text-sm",
        "thead": "sticky top-0 bg-card/95 backdrop-blur-sm",
        "row": "hover:bg-accent/30",
        "cell_numeric": "text-right font-mono tabular-nums"
      },
      "depth_visual": {
        "approach": "Use background fill bars per row (absolute inset-y-0 right-0) with low opacity; green for bids, red for asks.",
        "opacity": "0.10–0.18"
      }
    },

    "forms_login": {
      "layout": "Two-column on desktop: left brand/telemetry, right login card. Mobile: single card.",
      "card_classes": "rounded-2xl border border-border bg-card shadow-[0_12px_30px_rgba(0,0,0,0.45)]",
      "inputs": "Use shadcn Input + Label; show inline errors under fields.",
      "required_testids": [
        "login-email-input",
        "login-password-input",
        "login-form-submit-button",
        "login-error-text"
      ]
    },

    "dialogs_and_confirmations": {
      "live_mode_activation": {
        "component": "AlertDialog (double confirm)",
        "copy": [
          "Title: Activate LIVE Trading",
          "Body: You are about to place real orders on Polymarket CLOB. Confirm you understand risk limits and kill-switch.",
          "Checkbox: I understand (required)",
          "Confirm button: Activate LIVE"
        ],
        "testids": [
          "live-mode-activate-button",
          "live-mode-activate-dialog",
          "live-mode-activate-understand-checkbox",
          "live-mode-activate-confirm-button"
        ]
      },
      "kill_switch": {
        "component": "AlertDialog",
        "copy": [
          "Title: Kill Switch",
          "Body: Cancels open orders and disables execution until re-armed.",
          "Confirm: Engage Kill Switch"
        ],
        "testids": [
          "risk-kill-switch-button",
          "risk-kill-switch-dialog",
          "risk-kill-switch-confirm-button"
        ]
      }
    },

    "toasts": {
      "library": "sonner",
      "component_path": "/app/frontend/src/components/ui/sonner.jsx",
      "usage": "Execution events, webhook received, risk limit hit. Keep copy short; include order id + latency.",
      "testids": [
        "toast-execution-success",
        "toast-execution-failed",
        "toast-risk-limit-hit"
      ]
    }
  },

  "data_visualization": {
    "candlestick": {
      "library_options": [
        {
          "name": "lightweight-charts",
          "why": "Best for trading candles; performant; crisp",
          "styling": {
            "bg": "#0b0f14",
            "grid": "rgba(255,255,255,0.06)",
            "text": "rgba(255,255,255,0.75)",
            "bull": "hsl(var(--bull))",
            "bear": "hsl(var(--bear))"
          }
        },
        {
          "name": "Recharts (fallback)",
          "why": "Already common; easier for equity curve/DD bars",
          "note": "Prefer lightweight-charts for candles; use Recharts for risk charts."
        }
      ],
      "micro_interactions": [
        "Crosshair tooltip with OHLC + delta",
        "Click candle to pin tooltip (no animation)",
        "Hotkeys: 1m/5m/15m (optional)"
      ],
      "testids": [
        "candlestick-chart",
        "candlestick-timeframe-tabs"
      ]
    },

    "risk_charts": {
      "recommended": "Recharts",
      "charts": [
        "Equity curve (line)",
        "Daily drawdown (bar)",
        "Win rate (sparkline)"
      ],
      "styling": {
        "axis": "stroke: rgba(255,255,255,0.35)",
        "grid": "stroke: rgba(255,255,255,0.06)",
        "line": "stroke: hsl(var(--info))",
        "dd": "fill: hsl(var(--bear))"
      },
      "testids": [
        "risk-equity-curve-chart",
        "risk-daily-dd-chart"
      ]
    },

    "convergence_gauge": {
      "component": "shadcn Progress + custom ticks",
      "range": "-1 to +1 mapped to 0..100",
      "colors": {
        "bear": "hsl(var(--bear))",
        "neutral": "rgba(255,255,255,0.25)",
        "bull": "hsl(var(--bull))"
      },
      "testids": [
        "convergence-score-gauge",
        "convergence-score-value"
      ]
    },

    "edge_meter": {
      "component": "shadcn Slider (read-only) + numeric delta",
      "thresholds": [
        "<0.3%: no-trade",
        "0.3–0.8%: trade window",
        ">0.8%: caution (liquidity/lag check)"
      ],
      "colors": {
        "safe": "rgba(255,255,255,0.25)",
        "trade": "hsl(var(--edge))",
        "alert": "hsl(var(--bear))"
      },
      "testids": [
        "edge-meter",
        "edge-meter-percent"
      ]
    }
  },

  "force_graph": {
    "library": "react-force-graph-2d",
    "panel_layout": {
      "left": "Graph canvas",
      "right": "Inspector (selected node/edge details) + filters + legend",
      "mobile": "Canvas full width; inspector in Drawer/Sheet"
    },
    "styling": {
      "backgroundColor": "#0b0f14",
      "node": {
        "radius": "3–7 (based on val)",
        "stroke": "rgba(255,255,255,0.18)",
        "label": "Only show labels on hover/selected to reduce clutter",
        "cluster_palette": [
          "#00D1FF",
          "#2EE59D",
          "#FFB84D",
          "#FF4D6D",
          "#7DD3FC",
          "#A3E635"
        ],
        "note": "Avoid purple."
      },
      "link": {
        "base": "rgba(0, 209, 255, 0.22)",
        "highlight": "rgba(255,255,255,0.75)",
        "width": "1–2",
        "particles": "Directional particles only when user enables 'Flow' toggle (default off for performance)"
      }
    },
    "interactions": {
      "required": [
        "Hover: highlight node + connected edges",
        "Click: lock selection + populate inspector",
        "Controls: zoom in/out, zoom-to-fit, freeze/unfreeze physics",
        "Search: Command (shadcn Command) to jump to node"
      ],
      "testids": [
        "force-graph-canvas",
        "force-graph-freeze-toggle",
        "force-graph-zoom-in-button",
        "force-graph-zoom-out-button",
        "force-graph-zoom-to-fit-button",
        "force-graph-node-search"
      ]
    },
    "performance": {
      "defaults": {
        "cooldownTicks": 80,
        "warmupTicks": 10,
        "enableNodeDrag": true
      },
      "rules": [
        "Do not animate layout continuously once stabilized; freeze engine after cooldown.",
        "Avoid expensive shadows per frame; if glow is used, apply only to hovered/selected node.",
        "Throttle hover computations (requestAnimationFrame)."
      ]
    },
    "js_scaffold_snippet": {
      "note": "Example only; implement in .js.",
      "code": "import ForceGraph2D from 'react-force-graph-2d';\n\nexport default function MarketGraphPanel({ data, onSelect }) {\n  const fgRef = React.useRef(null);\n  const [hoverNode, setHoverNode] = React.useState(null);\n\n  return (\n    <div className=\"rounded-xl border border-border bg-card\" data-testid=\"force-graph-panel\">\n      <div className=\"flex items-center justify-between px-3 py-2 border-b border-border/70\">\n        <div className=\"text-sm font-medium\">Market Graph</div>\n        <div className=\"flex items-center gap-2\">\n          <button className=\"h-8 px-2 rounded-md hover:bg-accent/60\" data-testid=\"force-graph-zoom-to-fit-button\" onClick={() => fgRef.current?.zoomToFit?.(350, 40)}>Zoom to fit</button>\n        </div>\n      </div>\n\n      <div className=\"h-[420px] lg:h-[620px]\" data-testid=\"force-graph-canvas\">\n        <ForceGraph2D\n          ref={fgRef}\n          graphData={data}\n          backgroundColor=\"#0b0f14\"\n          nodeRelSize={4}\n          linkWidth={(l) => (l.highlighted ? 2 : 1)}\n          linkColor={(l) => (l.highlighted ? 'rgba(255,255,255,0.75)' : 'rgba(0,209,255,0.22)')}\n          onNodeHover={(n) => setHoverNode(n || null)}\n          onNodeClick={(n) => onSelect?.(n)}\n          nodeCanvasObject={(node, ctx, scale) => {\n            const r = node.val ? Math.max(3, Math.min(7, node.val / 3)) : 4;\n            const isHot = hoverNode && hoverNode.id === node.id;\n            ctx.beginPath();\n            ctx.arc(node.x, node.y, isHot ? r + 1.5 : r, 0, 2 * Math.PI);\n            ctx.fillStyle = node.color || '#00D1FF';\n            ctx.fill();\n            ctx.lineWidth = 1;\n            ctx.strokeStyle = 'rgba(255,255,255,0.18)';\n            ctx.stroke();\n          }}\n        />\n      </div>\n    </div>\n  );\n}"
    }
  },

  "motion_microinteractions": {
    "principles": [
      "No animated transitions on streaming numbers (avoid jitter).",
      "Use motion only for panel open/close, tab switches, dialogs, and hover affordances.",
      "Prefer 120–180ms durations; ease-out for entrances; linear for progress updates."
    ],
    "allowed_effects": {
      "panel_hover": "border color lift + subtle shadow (no transform on large panels)",
      "button": "hover shade shift + active scale 0.99",
      "tab": "underline/indicator slide",
      "modal": "fade + slight translateY (6–10px)"
    },
    "libraries": {
      "optional": {
        "framer_motion": {
          "why": "Clean dialog/panel transitions without affecting live data",
          "install": "npm i framer-motion",
          "usage": "AnimatePresence for modals/drawers; keep it minimal"
        }
      }
    }
  },

  "accessibility": {
    "rules": [
      "WCAG AA contrast for text on dark backgrounds.",
      "Focus visible rings must be obvious (use --focus cyan).",
      "Do not rely on color alone: add icons/labels for BULL/BEAR/NEUTRAL.",
      "Respect prefers-reduced-motion: disable non-essential transitions."
    ],
    "keyboard": [
      "Tab order: top bar -> main panels left-to-right -> tables",
      "Hotkeys (optional): K opens Command palette; Esc closes dialogs"
    ]
  },

  "telemetry_and_status_ui": {
    "latency_widget": {
      "placement": "Top bar, always visible",
      "content": [
        "WS status (Binance/Coinbase/Polymarket)",
        "P50/P95/P99 latency",
        "Tick rate (msgs/s)",
        "Clock drift"
      ],
      "visual": "Use small badges + monospace numbers; red only when disconnected.",
      "testids": [
        "ws-status-binance",
        "ws-status-coinbase",
        "ws-status-polymarket",
        "latency-p50",
        "latency-p95",
        "latency-p99"
      ]
    },
    "live_paper_mode_pill": {
      "visual": "Top-right pill: PAPER (muted) vs LIVE (edge color + subtle pulse border)",
      "pulse_rule": "Pulse only on LIVE mode indicator, not on data panels.",
      "testids": [
        "mode-pill",
        "mode-toggle"
      ]
    }
  },

  "images": {
    "image_urls": {
      "note": "Terminal app: avoid stock photos. Use abstract noise + subtle grid backgrounds only.",
      "categories": [
        {
          "category": "background_texture",
          "description": "SVG noise overlay (embedded in CSS token section)",
          "urls": []
        }
      ]
    }
  },

  "instructions_to_main_agent": [
    "Replace default shadcn tokens in /app/frontend/src/index.css with the provided dark terminal tokens (keep structure, update values).",
    "Remove CRA demo styles in /app/frontend/src/App.css (App-header centering etc). Do NOT center the app container.",
    "Implement app shell with a top command bar and Tabs-based navigation (mobile-first).",
    "Use font pairing: Space Grotesk for UI, IBM Plex Mono for numbers; apply tabular-nums widely.",
    "Use shadcn Resizable for desktop panel resizing (orderbook/chart/signals columns).",
    "Force-graph: implement react-force-graph-2d with hover highlight + inspector; labels only on hover/selected.",
    "Ensure every button/input/toggle/table row action has data-testid.",
    "Use Sonner for execution/risk toasts; keep copy short and include latency.",
    "Avoid gradients except subtle header wash; never exceed 20% viewport; never use purple/pink gradients."
  ],

  "General UI UX Design Guidelines": [
    "- You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms",
    "- You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text",
    "- NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json",
    "",
    " **GRADIENT RESTRICTION RULE**",
    "NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc",
    "NEVER use dark gradients for logo, testimonial, footer etc",
    "NEVER let gradients cover more than 20% of the viewport.",
    "NEVER apply gradients to text-heavy content or reading areas.",
    "NEVER use gradients on small UI elements (<100px width).",
    "NEVER stack multiple gradient layers in the same viewport.",
    "",
    "**ENFORCEMENT RULE:**",
    "    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors",
    "",
    "**How and where to use:**",
    "   • Section backgrounds (not content backgrounds)",
    "   • Hero section header content. Eg: dark to light to dark color",
    "   • Decorative overlays and accent elements only",
    "   • Hero section with 2-3 mild color",
    "   • Gradients creation can be done for any angle say horizontal, vertical or diagonal",
    "",
    "- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc",
    "",
    "</Font Guidelines>",
    "",
    "- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead.",
    "",
    "- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.",
    "",
    "- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.",
    "",
    "- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly",
    "    Eg: - if it implies playful/energetic, choose a colorful scheme",
    "           - if it implies monochrome/minimal, choose a black–white/neutral scheme",
    "",
    "**Component Reuse:**",
    "\t- Prioritize using pre-existing components from src/components/ui when applicable",
    "\t- Create new components that match the style and conventions of existing components when needed",
    "\t- Examine existing components to understand the project's component patterns before creating new ones",
    "",
    "**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component",
    "",
    "**Best Practices:**",
    "\t- Use Shadcn/UI as the primary component library for consistency and accessibility",
    "\t- Import path: ./components/[component-name]",
    "",
    "**Export Conventions:**",
    "\t- Components MUST use named exports (export const ComponentName = ...)",
    "\t- Pages MUST use default exports (export default function PageName() {...})",
    "",
    "**Toasts:**",
    "  - Use `sonner` for toasts\"",
    "  - Sonner component are located in `/app/src/components/ui/sonner.tsx`",
    "",
    "Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals."
  ]
}
