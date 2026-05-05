import type { BattleFeedEntry } from "../battle/battleCommsTypes";

const EMOJI_IDS = ["thumbs_up", "on_my_way", "danger", "nice", "help"] as const;

const PHRASE_IDS = [
  "need_heal",
  "shield_me",
  "focus_marked",
  "cooldown_ready",
  "good_job",
  "retreat",
] as const;

type Props = {
  connected: boolean;
  viewerIsRaidLead: boolean;
  feed: BattleFeedEntry[];
  selectedEnemyEntityId: string | null;
  onSendEmoji: (id: (typeof EMOJI_IDS)[number]) => void;
  onSendPhrase: (id: (typeof PHRASE_IDS)[number]) => void;
  onSendRaidLead: (
    commandId:
      | "focus_target"
      | "interrupt_channel"
      | "break_link"
      | "hold_defense"
      | "rally",
    targetEntityId?: string | null,
  ) => void;
};

function formatFeedLine(entry: BattleFeedEntry): string {
  if (entry.kind === "raid_lead_command") {
    const tail = entry.targetEntityId ? ` -> ${entry.targetEntityId}` : "";
    return `RL ${entry.commandId}${tail}`;
  }
  if (entry.kind === "emoji") {
    return `Emoji ${entry.emojiId}`;
  }
  return `Phrase ${entry.phraseId}`;
}

export function CombatCommsPanel({
  connected,
  viewerIsRaidLead,
  feed,
  selectedEnemyEntityId,
  onSendEmoji,
  onSendPhrase,
  onSendRaidLead,
}: Props) {
  return (
    <section className="combat-comms" data-testid="combat-comms-panel">
      <h2 className="tavern-card__title">Battle communications</h2>
      <p className="tavern-card__meta" data-testid="combat-comms-status">
        {connected
          ? "Live channel connected — messages sync without refresh."
          : "Connect by finishing raid setup (session + party)."}
      </p>

      <div className="combat-comms__strip" data-testid="combat-comms-emoji-row">
        {EMOJI_IDS.map((id) => (
          <button
            key={id}
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid={`combat-emoji-${id}`}
            disabled={!connected}
            onClick={() => {
              onSendEmoji(id);
            }}
          >
            {id.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <div
        className="combat-comms__strip"
        data-testid="combat-comms-phrase-row"
      >
        {PHRASE_IDS.map((id) => (
          <button
            key={id}
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid={`combat-phrase-${id}`}
            disabled={!connected}
            onClick={() => {
              onSendPhrase(id);
            }}
          >
            {id.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      {viewerIsRaidLead ? (
        <div className="combat-comms__strip" data-testid="combat-comms-rl-row">
          <button
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid="rl-focus-target"
            disabled={!connected || !selectedEnemyEntityId}
            onClick={() => {
              onSendRaidLead("focus_target", selectedEnemyEntityId);
            }}
          >
            Focus target
          </button>
          <button
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid="rl-interrupt-channel"
            disabled={!connected || !selectedEnemyEntityId}
            onClick={() => {
              onSendRaidLead("interrupt_channel", selectedEnemyEntityId);
            }}
          >
            Interrupt
          </button>
          <button
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid="rl-break-link"
            disabled={!connected || !selectedEnemyEntityId}
            onClick={() => {
              onSendRaidLead("break_link", selectedEnemyEntityId);
            }}
          >
            Break link
          </button>
          <button
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid="rl-hold-defense"
            disabled={!connected}
            onClick={() => {
              onSendRaidLead("hold_defense");
            }}
          >
            Hold defense
          </button>
          <button
            type="button"
            className="btn btn--secondary combat-comms__chip"
            data-testid="rl-rally"
            disabled={!connected}
            onClick={() => {
              onSendRaidLead("rally");
            }}
          >
            Rally
          </button>
        </div>
      ) : (
        <p className="tavern-card__meta" data-testid="combat-comms-rl-hint">
          Raid lead commands are available only to the raid leader.
        </p>
      )}

      <ul
        className="combat-comms__feed"
        data-testid="combat-comms-feed"
        aria-label="Combat communication log"
      >
        {feed.length === 0 ? (
          <li className="tavern-card__meta">No recent comms yet.</li>
        ) : (
          feed.map((entry) => (
            <li key={entry.id} className="combat-comms__feed-item">
              {formatFeedLine(entry)}
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
