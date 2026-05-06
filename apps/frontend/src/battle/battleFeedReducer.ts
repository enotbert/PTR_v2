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
  raidOutcome: {
    raidId: string;
    status: string;
    approvedFailedProgress: boolean;
    rewardPointsPerMember: number;
    claimStatus: string;
    rewardRecordIds: string[];
    newlyIssuedRewardRecordIds: string[];
    existingRewardRecordIds: string[];
  } | null;
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
      raidOutcome: current?.raidOutcome ?? null,
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
  let raidOutcome = current.raidOutcome;

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
  } else if (payload.event_type === "raid_outcome_resolved") {
    raidOutcome = {
      raidId: String(payload.raid_id ?? ""),
      status: String(payload.status ?? "unknown"),
      approvedFailedProgress: Boolean(payload.approved_failed_progress),
      rewardPointsPerMember: Number(payload.reward_points_per_member ?? 0),
      claimStatus: String(payload.claim_status ?? "not_applicable"),
      rewardRecordIds: Array.isArray(payload.reward_record_ids)
        ? payload.reward_record_ids.map(String)
        : [],
      newlyIssuedRewardRecordIds: Array.isArray(
        payload.newly_issued_reward_record_ids,
      )
        ? payload.newly_issued_reward_record_ids.map(String)
        : [],
      existingRewardRecordIds: Array.isArray(payload.existing_reward_record_ids)
        ? payload.existing_reward_record_ids.map(String)
        : [],
    };
  }

  return {
    snapshot: current.snapshot,
    feed,
    raidLeadHighlightEntityId: highlight,
    raidOutcome,
    lastServerSeq: message.server_seq,
  };
}
