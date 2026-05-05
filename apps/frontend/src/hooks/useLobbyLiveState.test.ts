import { describe, expect, it } from "vitest";

import { reduceLobbyMessage } from "./useLobbyLiveState";

const baseSnapshot = {
  kind: "snapshot" as const,
  type: "lobby.snapshot" as const,
  server_seq: 1,
  payload: {
    lobby_id: "lobby-1",
    raid_id: "raid-1",
    phase: "waiting",
    players: [
      {
        player_id: "p1",
        role_id: "vanguard",
        status: "not_ready" as const,
        is_raid_lead: true,
      },
    ],
    party_recommendations: [],
    weekly_event: null,
  },
};

describe("reduceLobbyMessage", () => {
  it("applies snapshot as source of truth", () => {
    const state = reduceLobbyMessage(null, baseSnapshot);
    expect(state).not.toBeNull();
    expect(state?.lastServerSeq).toBe(1);
    expect(state?.data.players[0]?.status).toBe("not_ready");
  });

  it("applies status event when sequence is monotonic", () => {
    const afterSnapshot = reduceLobbyMessage(null, baseSnapshot);
    const next = reduceLobbyMessage(afterSnapshot, {
      kind: "event",
      type: "lobby.event",
      server_seq: 2,
      payload: {
        event_type: "player_status_changed",
        player_id: "p1",
        status: "ready",
      },
    });
    expect(next?.lastServerSeq).toBe(2);
    expect(next?.data.players[0]?.status).toBe("ready");
  });

  it("ignores duplicated or stale sequence", () => {
    const afterSnapshot = reduceLobbyMessage(null, baseSnapshot);
    const stale = reduceLobbyMessage(afterSnapshot, {
      kind: "event",
      type: "lobby.event",
      server_seq: 1,
      payload: {
        event_type: "player_status_changed",
        player_id: "p1",
        status: "ready",
      },
    });
    expect(stale?.lastServerSeq).toBe(1);
    expect(stale?.data.players[0]?.status).toBe("not_ready");
  });

  it("returns null on sequence gap to trigger reconnect flow", () => {
    const afterSnapshot = reduceLobbyMessage(null, baseSnapshot);
    const withGap = reduceLobbyMessage(afterSnapshot, {
      kind: "event",
      type: "lobby.event",
      server_seq: 5,
      payload: {
        event_type: "player_status_changed",
        player_id: "p1",
        status: "ready",
      },
    });
    expect(withGap).toBeNull();
  });
});
