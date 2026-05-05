import type {
  BattleFeedEntry,
  BattleLiveMessage,
  BattleSnapshotPayloadWire,
} from "./battleCommsTypes";

export type BattleLiveStore = {
  snapshot: BattleSnapshotPayloadWire | null;
  lastServerSeq: number;
  feed: BattleFeedEntry[];
  raidLeadHighlightEntityId: string | null;
};

const MAX_FEED = 40;

function nextFeed(
  feed: BattleFeedEntry[],
  entry: BattleFeedEntry,
): BattleFeedEntry[] {
  return [...feed, entry].slice(-MAX_FEED);
}

function raidTargetFromSnapshot(
  snapshot: BattleSnapshotPayloadWire | null,
): string | null {
  const cmd = snapshot?.last_raid_lead_command;
  const entityId = cmd?.target?.entity_id;
  return entityId && typeof entityId === "string" ? entityId : null;
}

export function reduceBattleLiveMessage(
  current: BattleLiveStore | null,
  message: BattleLiveMessage,
): BattleLiveStore | null {
  if (message.type === "battle.snapshot") {
    const highlight = raidTargetFromSnapshot(message.payload);
    return {
      snapshot: message.payload,
      lastServerSeq: message.server_seq,
      feed: current?.feed ?? [],
      raidLeadHighlightEntityId: highlight,
    };
  }

  if (!current?.snapshot) {
    return null;
  }
  if (message.server_seq <= current.lastServerSeq) {
    return current;
  }
  if (message.server_seq > current.lastServerSeq + 1) {
    return null;
  }

  const payload = message.payload;
  let feed = current.feed;
  let highlight = current.raidLeadHighlightEntityId;

  if (payload.event_type === "raid_lead_command_sent") {
    const targetId = payload.target?.entity_id ?? null;
    highlight = targetId;
    feed = nextFeed(feed, {
      id: `ev-${message.server_seq}`,
      kind: "raid_lead_command",
      playerId: String(payload.player_id ?? ""),
      commandId: String(payload.command_id ?? ""),
      targetEntityId: targetId,
    });
  } else if (payload.event_type === "emoji_sent") {
    feed = nextFeed(feed, {
      id: `ev-${message.server_seq}`,
      kind: "emoji",
      playerId: String(payload.player_id ?? ""),
      emojiId: String(payload.emoji_id ?? ""),
    });
  } else if (payload.event_type === "quick_phrase_sent") {
    feed = nextFeed(feed, {
      id: `ev-${message.server_seq}`,
      kind: "phrase",
      playerId: String(payload.player_id ?? ""),
      phraseId: String(payload.phrase_id ?? ""),
    });
  }

  return {
    snapshot: current.snapshot,
    feed,
    raidLeadHighlightEntityId: highlight,
    lastServerSeq: message.server_seq,
  };
}
