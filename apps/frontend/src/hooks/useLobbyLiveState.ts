import { useEffect, useMemo, useRef, useState } from "react";

type LobbyPlayerStatus = "not_ready" | "ready" | "away";

type LobbyPlayer = {
  player_id: string;
  role_id: string;
  status: LobbyPlayerStatus;
  is_raid_lead: boolean;
};

type LobbySnapshotPayload = {
  lobby_id: string;
  raid_id: string;
  phase: string;
  players: LobbyPlayer[];
  party_recommendations: unknown[];
  weekly_event: unknown | null;
};

type LobbyEventPayload = {
  event_type: string;
  player_id: string;
  status?: LobbyPlayerStatus;
};

type LobbySnapshotMessage = {
  kind: "snapshot";
  type: "lobby.snapshot";
  server_seq: number;
  payload: LobbySnapshotPayload;
};

type LobbyEventMessage = {
  kind: "event";
  type: "lobby.event";
  server_seq: number;
  payload: LobbyEventPayload;
};

export type LobbyLiveState =
  | { status: "idle" }
  | { status: "connecting" }
  | { status: "ready"; data: LobbySnapshotPayload; lastServerSeq: number }
  | {
      status: "reconnecting";
      data: LobbySnapshotPayload;
      lastServerSeq: number;
    }
  | { status: "error"; message: string };

type LobbyStoreState = {
  data: LobbySnapshotPayload;
  lastServerSeq: number;
};

function isLobbySocketMessage(
  value: unknown,
): value is LobbySnapshotMessage | LobbyEventMessage {
  if (!value || typeof value !== "object") {
    return false;
  }
  const maybe = value as { type?: unknown };
  return maybe.type === "lobby.snapshot" || maybe.type === "lobby.event";
}

export function reduceLobbyMessage(
  current: LobbyStoreState | null,
  message: LobbySnapshotMessage | LobbyEventMessage,
): LobbyStoreState | null {
  if (message.type === "lobby.snapshot") {
    return {
      data: message.payload,
      lastServerSeq: message.server_seq,
    };
  }
  if (!current) {
    return null;
  }
  if (message.server_seq <= current.lastServerSeq) {
    return current;
  }
  if (message.server_seq > current.lastServerSeq + 1) {
    return null;
  }
  if (
    message.type === "lobby.event" &&
    message.payload.event_type === "player_status_changed" &&
    message.payload.status
  ) {
    const nextStatus = message.payload.status;
    const players = current.data.players.map((player) =>
      player.player_id === message.payload.player_id
        ? { ...player, status: nextStatus }
        : player,
    );
    return {
      data: { ...current.data, players },
      lastServerSeq: message.server_seq,
    };
  }
  return {
    data: current.data,
    lastServerSeq: message.server_seq,
  };
}

function buildWsUrl(
  apiBase: string,
  lobbyId: string,
  sessionId: string,
): string {
  const base = apiBase.trim();
  const scheme = base.startsWith("https://") ? "wss://" : "ws://";
  const noProto = base.replace(/^https?:\/\//, "");
  return `${scheme}${noProto}/v1/ws/lobbies/${lobbyId}?session_id=${sessionId}`;
}

export function useLobbyLiveState(
  apiBase: string,
  lobbyId: string | null,
  sessionId: string | null,
): LobbyLiveState {
  const [state, setState] = useState<LobbyLiveState>({ status: "idle" });
  const storeRef = useRef<LobbyStoreState | null>(null);
  const wsUrl = useMemo(() => {
    if (!apiBase || !lobbyId || !sessionId) {
      return null;
    }
    return buildWsUrl(apiBase, lobbyId, sessionId);
  }, [apiBase, lobbyId, sessionId]);

  useEffect(() => {
    if (!wsUrl) {
      setState({ status: "idle" });
      storeRef.current = null;
      return;
    }
    setState({ status: "connecting" });
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const parsed: unknown = JSON.parse(event.data as string);
        if (!isLobbySocketMessage(parsed)) {
          return;
        }
        const next = reduceLobbyMessage(storeRef.current, parsed);
        if (!next) {
          if (storeRef.current) {
            setState({
              status: "reconnecting",
              data: storeRef.current.data,
              lastServerSeq: storeRef.current.lastServerSeq,
            });
          }
          return;
        }
        storeRef.current = next;
        setState({
          status: "ready",
          data: next.data,
          lastServerSeq: next.lastServerSeq,
        });
      } catch {
        setState({
          status: "error",
          message: "Failed to parse lobby message.",
        });
      }
    };
    ws.onerror = () => {
      if (storeRef.current) {
        setState({
          status: "reconnecting",
          data: storeRef.current.data,
          lastServerSeq: storeRef.current.lastServerSeq,
        });
        return;
      }
      setState({ status: "error", message: "Lobby socket connection failed." });
    };
    return () => {
      ws.close();
    };
  }, [wsUrl]);

  return state;
}
