import { useEffect, useMemo, useRef, useState } from "react";

import { createApiClient } from "../api/client";
import type { ConnectivityState } from "./useNetworkAndApiStatus";

const SESSION_STORAGE_KEY = "prt.session_id";

export type GameplaySession =
  | { status: "no_api_base" }
  | { status: "pending_network" }
  | { status: "booting" }
  | { status: "ready"; sessionId: string; playerId: string }
  | { status: "error"; message: string };

function getApiBase(): string {
  return import.meta.env.VITE_API_BASE_URL?.trim() ?? "";
}

export function useGameplaySession(
  connectivity: ConnectivityState,
): GameplaySession {
  const apiBase = useMemo(() => getApiBase(), []);
  const [state, setState] = useState<GameplaySession>(
    apiBase ? { status: "pending_network" } : { status: "no_api_base" },
  );
  const runIdRef = useRef(0);

  useEffect(() => {
    if (!apiBase) {
      setState({ status: "no_api_base" });
      return;
    }
    if (connectivity !== "ready") {
      setState({ status: "pending_network" });
      return;
    }

    runIdRef.current += 1;
    const runId = runIdRef.current;
    setState({ status: "booting" });

    const client = createApiClient(apiBase);
    const ac = new AbortController();

    (async () => {
      try {
        const stored = sessionStorage.getItem(SESSION_STORAGE_KEY);
        if (stored) {
          const current = await client.GET("/v1/sessions/current", {
            headers: { Authorization: `Bearer ${stored}` },
            signal: ac.signal,
          });
          if (runIdRef.current !== runId) {
            return;
          }
          if (
            current.response?.ok &&
            current.data?.session?.id &&
            current.data.player?.id
          ) {
            sessionStorage.setItem(
              SESSION_STORAGE_KEY,
              current.data.session.id,
            );
            setState({
              status: "ready",
              sessionId: current.data.session.id,
              playerId: current.data.player.id,
            });
            return;
          }
          sessionStorage.removeItem(SESSION_STORAGE_KEY);
        }

        const created = await client.POST("/v1/sessions", {
          body: { display_name: "Tavern guest" },
          signal: ac.signal,
        });
        if (runIdRef.current !== runId) {
          return;
        }
        if (
          created.response?.ok &&
          created.data?.session?.id &&
          created.data.player?.id
        ) {
          sessionStorage.setItem(SESSION_STORAGE_KEY, created.data.session.id);
          setState({
            status: "ready",
            sessionId: created.data.session.id,
            playerId: created.data.player.id,
          });
          return;
        }
        setState({
          status: "error",
          message: "Unable to establish a player session. Please retry.",
        });
      } catch {
        if (runIdRef.current !== runId) {
          return;
        }
        setState({
          status: "error",
          message: "Unable to establish a player session. Please retry.",
        });
      }
    })();

    return () => {
      ac.abort();
    };
  }, [apiBase, connectivity]);

  return state;
}
