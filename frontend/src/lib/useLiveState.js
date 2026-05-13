import { useEffect, useRef } from "react";
import { useStateStore } from "@/lib/store";
import { api, wsUrl } from "@/lib/api";

/**
 * Subscribes to /api/ws/state WebSocket and falls back to /api/state polling.
 * Updates useStateStore.snapshot at ~2 Hz.
 */
export function useLiveState() {
  const setSnapshot = useStateStore((s) => s.setSnapshot);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    let stopped = false;

    const startPolling = () => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const r = await api.get("/state");
          if (!stopped) setSnapshot(r.data);
        } catch {
          /* swallow */
        }
      }, 1000);
    };

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const connect = () => {
      try {
        const url = wsUrl("/api/ws/state");
        const ws = new WebSocket(url);
        wsRef.current = ws;
        let opened = false;
        ws.onopen = () => {
          opened = true;
          stopPolling();
        };
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (!stopped) setSnapshot(data);
          } catch {}
        };
        ws.onerror = () => {
          if (!opened) startPolling();
        };
        ws.onclose = () => {
          startPolling();
          if (!stopped) setTimeout(connect, 3000);
        };
      } catch {
        startPolling();
      }
    };

    connect();
    // also do an immediate fetch
    api.get("/state").then((r) => !stopped && setSnapshot(r.data)).catch(() => {});

    return () => {
      stopped = true;
      try { wsRef.current && wsRef.current.close(); } catch {}
      stopPolling();
    };
  }, [setSnapshot]);
}
