import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { BattleLiveMessage } from "../battle/battleCommsTypes";
import {
  type BattleLiveStore,
  reduceBattleLiveMessage,
} from "../battle/battleFeedReducer";

const PROTOCOL = "ptr.ws.v1";
const ROOM_KIND = "battle";

function buildBattleWsUrl(
  apiBase: string,
  battleId: string,
  sessionId: string,
): string {
  const base = apiBase.trim();
  const scheme = base.startsWith("https://") ? "wss://" : "ws://";
  const noProto = base.replace(/^https?:\/\//, "");
  return `${scheme}${noProto}/v1/ws/battles/${battleId}?session_id=${sessionId}`;
}

function isoSentAt(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, ".000Z");
}

function randomCommandId(): string {
  return `cmd_${crypto.randomUUID()}`;
}

function isBattleLiveMessage(value: unknown): value is BattleLiveMessage {
  if (!value || typeof value !== "object") {
    return false;
  }
  const typed = value as { type?: unknown };
  return typed.type === "battle.snapshot" || typed.type === "battle.event";
}

export type BattleLiveConnection =
  | { status: "idle" }
  | { status: "connecting" }
  | { status: "ready"; store: BattleLiveStore; lastSocketError: string | null }
  | { status: "reconnecting"; store: BattleLiveStore }
  | { status: "error"; message: string };

type UseBattleLiveStateResult = {
  live: BattleLiveConnection;
  sendEmoji: (emojiId: string) => void;
  sendQuickPhrase: (phraseId: string) => void;
  sendRaidLeadCommand: (
    commandId: string,
    targetEntityId?: string | null,
  ) => void;
};

export function useBattleLiveState(
  apiBase: string,
  battlePartyId: string | null,
  sessionId: string | null,
): UseBattleLiveStateResult {
  const [live, setLive] = useState<BattleLiveConnection>({ status: "idle" });
  const storeRef = useRef<BattleLiveStore | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const wsUrl = useMemo(() => {
    if (!apiBase.trim() || !battlePartyId || !sessionId) {
      return null;
    }
    return buildBattleWsUrl(apiBase, battlePartyId, sessionId);
  }, [apiBase, battlePartyId, sessionId]);

  const sendEnvelope = useCallback(
    (type: string, payload: Record<string, unknown>) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN || !battlePartyId) {
        return;
      }
      ws.send(
        JSON.stringify({
          protocol: PROTOCOL,
          kind: "command",
          type,
          room: { kind: ROOM_KIND, id: battlePartyId },
          client_command_id: randomCommandId(),
          sent_at: isoSentAt(),
          payload,
        }),
      );
    },
    [battlePartyId],
  );

  const sendEmoji = useCallback(
    (emojiId: string) => {
      sendEnvelope("combat.send_emoji", { emoji_id: emojiId });
    },
    [sendEnvelope],
  );

  const sendQuickPhrase = useCallback(
    (phraseId: string) => {
      sendEnvelope("combat.send_quick_phrase", { phrase_id: phraseId });
    },
    [sendEnvelope],
  );

  const sendRaidLeadCommand = useCallback(
    (commandId: string, targetEntityId?: string | null) => {
      const targeted = [
        "focus_target",
        "interrupt_channel",
        "break_link",
      ].includes(commandId);
      const payload: Record<string, unknown> = { command_id: commandId };
      if (targeted) {
        if (!targetEntityId) {
          return;
        }
        payload.target = { kind: "entity", entity_id: targetEntityId };
      }
      sendEnvelope("combat.send_raid_lead_command", payload);
    },
    [sendEnvelope],
  );

  useEffect(() => {
    if (!wsUrl) {
      setLive({ status: "idle" });
      storeRef.current = null;
      wsRef.current = null;
      return;
    }
    const wsConnectUrl = wsUrl;

    let cancelled = false;
    let socket: WebSocket | null = null;

    function connect() {
      setLive((prev) =>
        prev.status === "ready" || prev.status === "reconnecting"
          ? { status: "reconnecting", store: prev.store }
          : { status: "connecting" },
      );

      const ws = new WebSocket(wsConnectUrl);
      wsRef.current = ws;
      socket = ws;

      ws.onmessage = (event) => {
        try {
          const parsed: unknown = JSON.parse(event.data as string);
          if (!isBattleLiveMessage(parsed)) {
            return;
          }
          const next = reduceBattleLiveMessage(storeRef.current, parsed);
          if (!next) {
            if (storeRef.current) {
              setLive({
                status: "reconnecting",
                store: storeRef.current,
              });
            }
            ws.close();
            return;
          }
          storeRef.current = next;
          setLive({
            status: "ready",
            store: next,
            lastSocketError: null,
          });
        } catch {
          setLive({
            status: "error",
            message: "Failed to parse battle socket message.",
          });
        }
      };

      ws.onerror = () => {
        if (storeRef.current) {
          setLive({
            status: "reconnecting",
            store: storeRef.current,
          });
          return;
        }
        setLive({
          status: "error",
          message: "Battle socket connection failed.",
        });
      };

      ws.onclose = () => {
        if (cancelled) {
          return;
        }
        setTimeout(() => {
          if (!cancelled && wsRef.current === ws) {
            connect();
          }
        }, 900);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      wsRef.current = null;
    };
  }, [wsUrl]);

  return { live, sendEmoji, sendQuickPhrase, sendRaidLeadCommand };
}
