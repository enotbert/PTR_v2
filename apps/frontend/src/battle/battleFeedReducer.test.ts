import { describe, expect, it } from "vitest";

import type { BattleLiveMessage } from "./battleCommsTypes";
import { reduceBattleLiveMessage } from "./battleFeedReducer";

const BASE_SNAPSHOT: BattleLiveMessage = {
  kind: "snapshot",
  type: "battle.snapshot",
  server_seq: 1,
  payload: {
    battle_id: "b1",
    phase: "active",
    raid_lead_player_id: "lead-1",
    party_order: [],
    entities: [],
    last_raid_lead_command: null,
  },
};

describe("reduceBattleLiveMessage", () => {
  it("applies snapshot and derives highlight from last raid lead command", () => {
    const snap: BattleLiveMessage = {
      ...BASE_SNAPSHOT,
      payload: {
        ...BASE_SNAPSHOT.payload,
        last_raid_lead_command: {
          command_id: "focus_target",
          player_id: "lead-1",
          target: { kind: "entity", entity_id: "enemy:a" },
        },
      },
    };
    const next = reduceBattleLiveMessage(null, snap);
    expect(next?.raidLeadHighlightEntityId).toBe("enemy:a");
    expect(next?.lastServerSeq).toBe(1);
  });

  it("appends emoji event when sequence is contiguous", () => {
    const afterSnap = reduceBattleLiveMessage(null, BASE_SNAPSHOT);
    expect(afterSnap).not.toBeNull();
    const ev: BattleLiveMessage = {
      kind: "event",
      type: "battle.event",
      server_seq: 2,
      payload: {
        event_type: "emoji_sent",
        player_id: "p1",
        emoji_id: "nice",
      },
    };
    const next = reduceBattleLiveMessage(afterSnap, ev);
    expect(next?.feed).toHaveLength(1);
    expect(next?.feed[0]).toMatchObject({ kind: "emoji", emojiId: "nice" });
  });

  it("returns null on sequence gap", () => {
    const afterSnap = reduceBattleLiveMessage(null, BASE_SNAPSHOT);
    const ev: BattleLiveMessage = {
      kind: "event",
      type: "battle.event",
      server_seq: 5,
      payload: { event_type: "emoji_sent", player_id: "p1", emoji_id: "help" },
    };
    expect(reduceBattleLiveMessage(afterSnap, ev)).toBeNull();
  });
});
