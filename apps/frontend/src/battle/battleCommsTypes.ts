export type BattleFeedEntry =
  | {
      id: string;
      kind: "raid_lead_command";
      playerId: string;
      commandId: string;
      targetEntityId: string | null;
    }
  | {
      id: string;
      kind: "emoji";
      playerId: string;
      emojiId: string;
    }
  | {
      id: string;
      kind: "phrase";
      playerId: string;
      phraseId: string;
    };

export type RaidOutcomePayloadWire = {
  event_type?: string;
  raid_id?: string;
  status?: string;
  approved_failed_progress?: boolean;
  reward_points_per_member?: number;
  claim_status?: string;
  reward_record_ids?: string[];
  newly_issued_reward_record_ids?: string[];
  existing_reward_record_ids?: string[];
};

export type SnapshotEntityWire = {
  entity_id: string;
  kind: string;
  hp: { current: number; max: number } | null;
};

export type BattleSnapshotPayloadWire = {
  battle_id: string;
  raid_lead_player_id: string;
  party_order: string[];
  entities: SnapshotEntityWire[];
  last_raid_lead_command: {
    command_id: string;
    player_id: string;
    target?: { kind?: string; entity_id?: string } | null;
    sent_at?: string;
  } | null;
  phase: string;
};

export type BattleLiveMessage =
  | {
      kind: "snapshot";
      type: "battle.snapshot";
      server_seq: number;
      payload: BattleSnapshotPayloadWire;
    }
  | {
      kind: "event";
      type: "battle.event";
      server_seq: number;
      payload: {
        event_type: string;
        player_id?: string;
        command_id?: string;
        target?: { entity_id?: string } | null;
        emoji_id?: string;
        phrase_id?: string;
      } & Partial<RaidOutcomePayloadWire>;
    };
