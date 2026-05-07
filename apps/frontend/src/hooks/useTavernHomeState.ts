import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { createBearerApiClient } from "../api/client";
import type { components } from "../generated/api-types";
import { useGameplayActionGate } from "./useGameplayActionGate";
import type { GameplaySession } from "./useGameplaySession";
import type { ConnectivityState } from "./useNetworkAndApiStatus";

type TavernState = components["schemas"]["PlayerTavernStateOut"];

type TavernHomeState =
  | { status: "loading"; message: string }
  | { status: "blocked"; message: string }
  | { status: "error"; message: string }
  | { status: "ready"; data: TavernState };

const DEFAULT_TAVERN_ID = "00000000-0000-0000-0000-000000000001";
const REQUEST_TIMEOUT_MS = 6000;

function getApiBase(): string {
  return import.meta.env.VITE_API_BASE_URL?.trim() ?? "";
}

function getTavernId(): string {
  return import.meta.env.VITE_TAVERN_ID?.trim() || DEFAULT_TAVERN_ID;
}

function toErrorMessage(code: number | null): string {
  if (code === 401) {
    return "Sign-in is required to load tavern progress.";
  }
  if (code === 404) {
    return "Tavern state is not available yet.";
  }
  return "Unable to load tavern data right now. Please retry.";
}

export function useTavernHomeState(
  connectivity: ConnectivityState,
  gameplaySession: GameplaySession,
): { state: TavernHomeState; refresh: () => void } {
  const apiBase = useMemo(() => getApiBase(), []);
  const tavernId = useMemo(() => getTavernId(), []);
  const gate = useGameplayActionGate(connectivity);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const refresh = useCallback(() => {
    setRefreshVersion((value) => value + 1);
  }, []);

  const [state, setState] = useState<TavernHomeState>({
    status: "loading",
    message: "Loading tavern state…",
  });

  const runIdRef = useRef(0);

  useEffect(() => {
    runIdRef.current += 1;
    const runId = runIdRef.current;

    if (gate.blocked) {
      setState({
        status: "blocked",
        message: gate.message ?? "Gameplay actions are temporarily blocked.",
      });
      return;
    }

    if (!apiBase) {
      setState({
        status: "error",
        message:
          "Gameplay API is not configured. Set VITE_API_BASE_URL for live data.",
      });
      return;
    }

    if (
      gameplaySession.status === "pending_network" ||
      gameplaySession.status === "booting"
    ) {
      setState({
        status: "loading",
        message:
          gameplaySession.status === "pending_network"
            ? "Waiting for network…"
            : "Establishing session…",
      });
      return;
    }

    if (gameplaySession.status === "no_api_base") {
      setState({
        status: "error",
        message:
          "Gameplay API is not configured. Set VITE_API_BASE_URL for live data.",
      });
      return;
    }

    if (gameplaySession.status === "error") {
      setState({
        status: "error",
        message: gameplaySession.message,
      });
      return;
    }

    setState({
      status: "loading",
      message:
        refreshVersion > 0
          ? "Refreshing tavern state…"
          : "Loading tavern state…",
    });

    const client = createBearerApiClient(apiBase, gameplaySession.sessionId);
    const ac = new AbortController();
    const timeoutId = window.setTimeout(() => ac.abort(), REQUEST_TIMEOUT_MS);

    (async () => {
      try {
        const { data, error, response } = await client.GET(
          "/v1/taverns/{tavern_id}/state",
          {
            params: {
              path: {
                tavern_id: tavernId,
              },
            },
            signal: ac.signal,
          },
        );

        if (runIdRef.current !== runId) {
          return;
        }

        if (error || !response?.ok || !data) {
          setState({
            status: "error",
            message: toErrorMessage(response?.status ?? null),
          });
          return;
        }

        setState({
          status: "ready",
          data,
        });
      } catch {
        if (runIdRef.current !== runId) {
          return;
        }
        setState({
          status: "error",
          message: "Unable to load tavern data right now. Please retry.",
        });
      } finally {
        window.clearTimeout(timeoutId);
      }
    })();

    return () => {
      ac.abort();
      window.clearTimeout(timeoutId);
    };
  }, [
    apiBase,
    gate.blocked,
    gate.message,
    tavernId,
    gameplaySession,
    refreshVersion,
  ]);

  return { state, refresh };
}
