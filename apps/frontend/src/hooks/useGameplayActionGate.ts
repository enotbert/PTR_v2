import { useCallback, useMemo } from "react";
import type { ConnectivityState } from "./useNetworkAndApiStatus";

export type GameplayActionBlockReason =
  | "offline"
  | "checking"
  | "api-unavailable"
  | "no-api-base";

type GameplayActionGate = {
  blocked: boolean;
  reason: GameplayActionBlockReason | null;
  message: string | null;
  runIfAllowed: (action: () => void) => boolean;
};

const BLOCK_MESSAGES: Record<GameplayActionBlockReason, string> = {
  offline: "You are offline. Gameplay actions require network connection.",
  checking: "Checking backend availability before gameplay action.",
  "api-unavailable":
    "Game server is temporarily unavailable. Shell stays available.",
  "no-api-base":
    "Gameplay API is not configured. Shell is available, gameplay is blocked.",
};

function toBlockReason(
  connectivity: ConnectivityState,
): GameplayActionBlockReason | null {
  if (connectivity === "ready") {
    return null;
  }
  return connectivity;
}

export function useGameplayActionGate(
  connectivity: ConnectivityState,
): GameplayActionGate {
  const reason = useMemo(() => toBlockReason(connectivity), [connectivity]);
  const blocked = reason !== null;
  const message = reason ? BLOCK_MESSAGES[reason] : null;

  const runIfAllowed = useCallback(
    (action: () => void) => {
      if (blocked) {
        return false;
      }
      action();
      return true;
    },
    [blocked],
  );

  return {
    blocked,
    reason,
    message,
    runIfAllowed,
  };
}
