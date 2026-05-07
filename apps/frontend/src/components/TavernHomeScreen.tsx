import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createBearerApiClient } from "../api/client";
import { mapBattleSnapshotToCanvas } from "../battle/mapBattleSnapshotToCanvas";
import type { components } from "../generated/api-types";
import { useBattleLiveState } from "../hooks/useBattleLiveState";
import type { GameplaySession } from "../hooks/useGameplaySession";
import type { ConnectivityState } from "../hooks/useNetworkAndApiStatus";
import { useTavernHomeState } from "../hooks/useTavernHomeState";
import {
  CombatCanvas,
  type CombatUnitViewModel,
  combatCanvasAspectRatio,
  useDemoCombatViewModel,
} from "./CombatCanvas";
import { CombatCommsPanel } from "./CombatCommsPanel";
import {
  CombatHud,
  type CombatSkillViewModel,
  type CombatTargetViewModel,
} from "./CombatHud";

type Props = {
  connectivity: ConnectivityState;
  gameplaySession: GameplaySession;
};

type RaidDetail = components["schemas"]["RaidDetailOut"];

type EntryState =
  | { status: "idle"; message: string | null }
  | { status: "creating"; message: string }
  | { status: "error"; message: string }
  | { status: "ready"; message: string; raid: RaidDetail };

type RewardClaimUiState =
  | { status: "idle"; message: null }
  | { status: "claimable"; message: string }
  | { status: "claiming"; message: string }
  | { status: "claimed"; message: string }
  | { status: "already_claimed"; message: string }
  | { status: "error"; message: string };

const DEFAULT_TAVERN_ID = "00000000-0000-0000-0000-000000000001";
const DEFAULT_FEEDBACK = "Select a skill, then tap a target in the arena.";

type SkillTargetRule = {
  allowedSides: Array<"party" | "enemy">;
  invalidReason: string;
};

const SKILL_TARGET_RULES: Record<string, SkillTargetRule> = {
  "quick-shot": {
    allowedSides: ["enemy"],
    invalidReason: "Quick Shot can only target enemies.",
  },
  "heavy-slash": {
    allowedSides: ["party"],
    invalidReason: "Heavy Slash is lane-locked and cannot reach that target.",
  },
  "focus-stance": {
    allowedSides: ["party", "enemy"],
    invalidReason: "Focus Stance does not require a target right now.",
  },
};

function getTavernId(): string {
  return import.meta.env.VITE_TAVERN_ID?.trim() || DEFAULT_TAVERN_ID;
}

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "No recent contributions yet";
  }
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return "Recently";
  }
  return dt.toLocaleString();
}

function formatSource(source: string | null | undefined): string {
  if (!source) {
    return "Not available";
  }
  return source.replaceAll("_", " ");
}

function initialClaimUiState(
  claimStatus: string,
  rewardPointsPerMember: number,
): RewardClaimUiState {
  if (claimStatus === "already_claimed") {
    return {
      status: "already_claimed",
      message: "Reward was already claimed earlier for this raid.",
    };
  }
  if (claimStatus === "claimed") {
    return {
      status: "claimed",
      message: "Reward has been claimed and added to tavern contribution.",
    };
  }
  if (rewardPointsPerMember > 0) {
    return {
      status: "claimable",
      message: "Reward is available. Claim to add it to your account.",
    };
  }
  return { status: "idle", message: null };
}

export function TavernHomeScreen({ connectivity, gameplaySession }: Props) {
  const { state: home, refresh: refreshTavernState } = useTavernHomeState(
    connectivity,
    gameplaySession,
  );
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [invalidTargetReason, setInvalidTargetReason] = useState<string | null>(
    null,
  );
  const demoCombatViewModel = useDemoCombatViewModel(selectedTargetId);
  const [resource, setResource] = useState(5);
  const [feedback, setFeedback] = useState(DEFAULT_FEEDBACK);
  const [entry, setEntry] = useState<EntryState>({
    status: "idle",
    message: null,
  });
  const [rewardClaim, setRewardClaim] = useState<RewardClaimUiState>({
    status: "idle",
    message: null,
  });
  const contributionEventRaidIdsRef = useRef<Set<string>>(new Set());

  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL?.trim() ?? "",
    [],
  );
  const battlePartyId = entry.status === "ready" ? entry.raid.party_id : null;
  const battleSessionId =
    gameplaySession.status === "ready" ? gameplaySession.sessionId : null;
  const { live, sendEmoji, sendQuickPhrase, sendRaidLeadCommand } =
    useBattleLiveState(apiBaseUrl, battlePartyId, battleSessionId);

  const combatViewModel = useMemo(() => {
    if (
      live.status === "ready" &&
      live.store.snapshot &&
      gameplaySession.status === "ready"
    ) {
      return mapBattleSnapshotToCanvas(
        live.store.snapshot,
        gameplaySession.playerId,
        selectedTargetId,
        live.store.raidLeadHighlightEntityId,
      );
    }
    return demoCombatViewModel;
  }, [demoCombatViewModel, gameplaySession, live, selectedTargetId]);

  const selectedTarget = useMemo(
    () =>
      [...combatViewModel.party, ...combatViewModel.enemies].find(
        (unit) => unit.id === selectedTargetId,
      ) ?? null,
    [combatViewModel.enemies, combatViewModel.party, selectedTargetId],
  );
  const demoTarget: CombatTargetViewModel | null = useMemo(() => {
    if (!selectedTarget) {
      return null;
    }
    return {
      id: selectedTarget.id,
      label: selectedTarget.label,
      hp: selectedTarget.hp,
      maxHp: selectedTarget.maxHp,
      canBeTargeted: !invalidTargetReason,
      invalidReason: invalidTargetReason ?? undefined,
    };
  }, [invalidTargetReason, selectedTarget]);
  const demoSkills: CombatSkillViewModel[] = useMemo(
    () => [
      {
        id: "quick-shot",
        label: "Quick Shot",
        resourceCost: 2,
        cooldownRemainingMs: 0,
        state: resource >= 2 ? "ready" : "no-resource",
        reason: resource >= 2 ? undefined : "Not enough energy.",
      },
      {
        id: "heavy-slash",
        label: "Heavy Slash",
        resourceCost: 4,
        cooldownRemainingMs: 0,
        state: "ready",
      },
      {
        id: "focus-stance",
        label: "Focus Stance",
        resourceCost: 1,
        cooldownRemainingMs: 6500,
        state: "cooldown",
        reason: "Cooling down.",
      },
    ],
    [resource],
  );

  const selectedEnemyEntityId = useMemo(() => {
    if (!selectedTargetId) {
      return null;
    }
    const unit = [...combatViewModel.party, ...combatViewModel.enemies].find(
      (candidate) => candidate.id === selectedTargetId,
    );
    return unit?.side === "enemy" ? unit.id : null;
  }, [combatViewModel, selectedTargetId]);

  const viewerIsRaidLead =
    live.status === "ready" &&
    live.store.snapshot !== null &&
    gameplaySession.status === "ready" &&
    live.store.snapshot.raid_lead_player_id === gameplaySession.playerId;

  const commsFeed = live.status === "ready" ? live.store.feed : [];
  const raidOutcome = live.status === "ready" ? live.store.raidOutcome : null;
  const combatCommsConnected = live.status === "ready";

  useEffect(() => {
    if (!raidOutcome) {
      return;
    }
    setRewardClaim(
      initialClaimUiState(
        raidOutcome.claimStatus,
        raidOutcome.rewardPointsPerMember,
      ),
    );
    if (
      raidOutcome.rewardPointsPerMember > 0 &&
      !contributionEventRaidIdsRef.current.has(raidOutcome.raidId)
    ) {
      contributionEventRaidIdsRef.current.add(raidOutcome.raidId);
      refreshTavernState();
      window.dispatchEvent(
        new CustomEvent("tavern_contribution_made", {
          detail: {
            raidId: raidOutcome.raidId,
            status: raidOutcome.status,
            points: raidOutcome.rewardPointsPerMember,
            claimStatus: raidOutcome.claimStatus,
          },
        }),
      );
    }
  }, [raidOutcome, refreshTavernState]);

  const handleStartFirstRaid = useCallback(async () => {
    if (home.status !== "ready") {
      return;
    }

    if (!apiBaseUrl) {
      setEntry({
        status: "error",
        message:
          "Gameplay API is not configured. Cannot create the first raid session.",
      });
      return;
    }

    if (gameplaySession.status !== "ready") {
      setEntry({
        status: "error",
        message:
          "Session is still starting. Please wait a moment and try again.",
      });
      return;
    }

    setEntry({
      status: "creating",
      message: "Creating first tutorial raid session…",
    });

    const client = createBearerApiClient(apiBaseUrl, gameplaySession.sessionId);
    try {
      const { data, error, response } = await client.POST("/v1/raids", {
        body: {
          raid_template_id: "tutorial_solo_v1",
          tavern_id: getTavernId(),
        },
      });

      if (error || !response?.ok || !data) {
        setEntry({
          status: "error",
          message:
            "Unable to create first raid setup right now. Please retry in a moment.",
        });
        return;
      }

      setEntry({
        status: "ready",
        message:
          "First raid setup is ready. Continue to combat when you are ready.",
        raid: data,
      });
    } catch {
      setEntry({
        status: "error",
        message:
          "Unable to create first raid setup right now. Please retry in a moment.",
      });
    }
  }, [apiBaseUrl, gameplaySession, home.status]);

  const handleSkillPress = useCallback(
    (skillId: string) => {
      const skill = demoSkills.find((value) => value.id === skillId);
      if (!skill) {
        return;
      }
      if (skill.state !== "ready") {
        setFeedback(skill.reason ?? "This skill is unavailable right now.");
        return;
      }
      setSelectedSkillId(skill.id);
      setInvalidTargetReason(null);
      setFeedback(`Selected ${skill.label}. Tap a target in the arena.`);
    },
    [demoSkills],
  );

  const handleTargetTap = useCallback(
    (unit: CombatUnitViewModel) => {
      if (!selectedSkillId) {
        setSelectedTargetId(unit.id);
        setInvalidTargetReason(null);
        setFeedback("Target selected. Choose a skill to continue.");
        return;
      }

      const skill = demoSkills.find((value) => value.id === selectedSkillId);
      const rule = SKILL_TARGET_RULES[selectedSkillId];
      if (!skill || !rule) {
        setFeedback("Selected skill is not available anymore.");
        setSelectedSkillId(null);
        return;
      }

      setSelectedTargetId(unit.id);
      if (!rule.allowedSides.includes(unit.side)) {
        setInvalidTargetReason(rule.invalidReason);
        setFeedback(`Invalid target for ${skill.label}. Choose another one.`);
        return;
      }

      setInvalidTargetReason(null);
      setResource((current) => Math.max(0, current - skill.resourceCost));
      setFeedback(`${skill.label} used on ${unit.label}.`);
      window.dispatchEvent(
        new CustomEvent("skill_target_selected", {
          detail: {
            skillId: skill.id,
            targetId: unit.id,
            targetSide: unit.side,
          },
        }),
      );
      setSelectedSkillId(null);
    },
    [demoSkills, selectedSkillId],
  );

  const handleClaimReward = useCallback(async () => {
    if (!raidOutcome || rewardClaim.status !== "claimable") {
      return;
    }
    if (!apiBaseUrl) {
      setRewardClaim({
        status: "error",
        message: "Gameplay API is not configured. Cannot claim reward.",
      });
      return;
    }
    if (gameplaySession.status !== "ready") {
      setRewardClaim({
        status: "error",
        message: "Session is unavailable. Reconnect and try claiming again.",
      });
      return;
    }
    const rewardRecordId = raidOutcome.rewardRecordIds[0];
    if (!rewardRecordId) {
      setRewardClaim({
        status: "error",
        message: "No reward reference found for this raid outcome.",
      });
      return;
    }
    setRewardClaim({
      status: "claiming",
      message: "Claiming reward…",
    });
    const client = createBearerApiClient(apiBaseUrl, gameplaySession.sessionId);
    try {
      const { response } = await client.POST("/v1/rewards/{reward_id}/claims", {
        params: { path: { reward_id: rewardRecordId } },
      });
      if (response?.ok) {
        setRewardClaim({
          status: "claimed",
          message: "Reward successfully claimed.",
        });
        refreshTavernState();
        return;
      }
      if (response?.status === 409) {
        setRewardClaim({
          status: "already_claimed",
          message: "Reward was already claimed earlier.",
        });
        return;
      }
      setRewardClaim({
        status: "error",
        message: "Reward claim failed. Please retry in a moment.",
      });
    } catch {
      setRewardClaim({
        status: "error",
        message: "Reward claim failed. Please retry in a moment.",
      });
    }
  }, [apiBaseUrl, gameplaySession, raidOutcome, refreshTavernState, rewardClaim.status]);

  if (home.status === "blocked") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-blocked">
          {home.message}
        </p>
        <button
          type="button"
          className="btn btn--primary"
          data-testid="primary-cta"
          disabled
          aria-disabled="true"
        >
          Start first raid
        </button>
      </section>
    );
  }

  if (home.status === "loading") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-loading">
          {home.message}
        </p>
      </section>
    );
  }

  if (home.status === "error") {
    return (
      <section className="tavern-home" aria-labelledby="tavern-home-title">
        <h1 id="tavern-home-title" className="tavern-home__title">
          Pocket Raid Tavern
        </h1>
        <p className="tavern-home__status" data-testid="tavern-error">
          {home.message}
        </p>
        <button
          type="button"
          className="btn btn--primary"
          data-testid="primary-cta"
          disabled
          aria-disabled="true"
        >
          Start first raid
        </button>
      </section>
    );
  }

  const { data } = home;
  const percent =
    data.current_project.target_points > 0
      ? Math.min(
          100,
          Math.round(
            (data.current_project.progress_points /
              data.current_project.target_points) *
              100,
          ),
        )
      : 0;

  return (
    <section className="tavern-home" aria-labelledby="tavern-home-title">
      <h1 id="tavern-home-title" className="tavern-home__title">
        Pocket Raid Tavern
      </h1>
      <p className="tavern-home__lede">
        Gather your party for quick raids and keep the tavern project moving.
      </p>

      <button
        type="button"
        className="btn btn--primary"
        data-testid="primary-cta"
        onClick={() => {
          void handleStartFirstRaid();
        }}
        disabled={entry.status === "creating"}
      >
        {entry.status === "creating"
          ? "Preparing first raid…"
          : "Start first raid"}
      </button>

      <article className="tavern-card" data-testid="first-session-setup">
        <h2 className="tavern-card__title">First raid setup</h2>
        <p className="tavern-card__meta">
          Default role: <strong>Vanguard</strong>
        </p>
        <p className="tavern-card__meta">
          Starter loadout focuses on steady damage and survivability for a first
          solo encounter.
        </p>
        {entry.message ? (
          <p
            className={
              entry.status === "error"
                ? "tavern-home__status tavern-home__status--error"
                : "tavern-home__status"
            }
            data-testid="first-session-message"
          >
            {entry.message}
          </p>
        ) : (
          <p
            className="tavern-home__status"
            data-testid="first-session-message"
          >
            Start the setup to begin a short tutorial solo raid before combat.
          </p>
        )}
        {entry.status === "ready" ? (
          <>
            <p
              className="tavern-card__meta"
              data-testid="first-session-raid-id"
            >
              Raid ID: {entry.raid.id}
            </p>
            <button
              type="button"
              className="btn btn--secondary"
              data-testid="next-cta"
            >
              Continue to combat
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn btn--secondary"
            data-testid="next-cta"
            disabled
            aria-disabled="true"
          >
            Continue to combat
          </button>
        )}
      </article>

      {raidOutcome ? (
        <article className="tavern-card" data-testid="raid-result-reward">
          <h2 className="tavern-card__title">Raid result and reward</h2>
          <p className="tavern-card__strong">
            {raidOutcome.status === "completed"
              ? "Raid completed"
              : "Raid failed"}
          </p>
          <p className="tavern-card__meta">
            Contribution: +{raidOutcome.rewardPointsPerMember} points per member
          </p>
          <p className="tavern-card__meta">Raid ID: {raidOutcome.raidId}</p>
          {rewardClaim.message ? (
            <p
              className={
                rewardClaim.status === "error"
                  ? "tavern-home__status tavern-home__status--error"
                  : "tavern-home__status"
              }
              data-testid="reward-claim-state"
            >
              {rewardClaim.message}
            </p>
          ) : null}
          {rewardClaim.status === "claimable" ? (
            <button
              type="button"
              className="btn btn--primary"
              data-testid="claim-reward-cta"
              onClick={() => {
                void handleClaimReward();
              }}
            >
              Claim reward
            </button>
          ) : rewardClaim.status === "claiming" ? (
            <button
              type="button"
              className="btn btn--primary"
              data-testid="claim-reward-cta"
              disabled
              aria-disabled="true"
            >
              Claiming reward…
            </button>
          ) : null}
          <div className="raid-result-actions">
            <button
              type="button"
              className="btn btn--secondary"
              data-testid="cta-repeat-raid"
            >
              Repeat raid
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              data-testid="cta-contribute"
            >
              Contribute in tavern
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              data-testid="cta-invite-share"
            >
              Invite and share
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              data-testid="cta-return-tavern"
            >
              Return to tavern
            </button>
          </div>
        </article>
      ) : null}

      <article className="tavern-card" data-testid="tavern-project">
        <h2 className="tavern-card__title">Current project</h2>
        <p className="tavern-card__strong">{data.current_project.title}</p>
        <p className="tavern-card__meta">
          {data.current_project.progress_points} /{" "}
          {data.current_project.target_points} points
        </p>
        <div
          className="tavern-progress"
          role="progressbar"
          aria-label="Project progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div
            className="tavern-progress__fill"
            style={{ width: `${percent}%` }}
          />
        </div>
      </article>

      <article className="tavern-card" data-testid="tavern-contribution">
        <h2 className="tavern-card__title">Rewards and contribution</h2>
        <p className="tavern-card__meta">Weekly points: {data.weekly_points}</p>
        <p className="tavern-card__meta">Reputation: {data.reputation}</p>
        <p className="tavern-card__meta">
          Latest contribution: {data.contribution_summary.latest_amount ?? 0} (
          {formatSource(data.contribution_summary.latest_source_type)})
        </p>
        <p className="tavern-card__meta">
          Updated: {formatTime(data.contribution_summary.latest_at ?? null)}
        </p>
      </article>

      <article className="tavern-card" data-testid="tavern-chronicle">
        <h2 className="tavern-card__title">Chronicle</h2>
        {data.chronicle && data.chronicle.length > 0 ? (
          <ul className="tavern-chronicle">
            {data.chronicle.map((entry) => (
              <li className="tavern-chronicle__item" key={entry.id}>
                +{entry.amount} from {formatSource(entry.source_type)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="tavern-card__meta">
            No events yet. Complete your first raid.
          </p>
        )}
      </article>

      <article className="tavern-card" data-testid="combat-canvas-card">
        <h2 className="tavern-card__title">Combat arena preview</h2>
        <p className="tavern-card__meta">
          Presentation-only canvas view model for party and enemy formation.
        </p>
        <p className="tavern-card__meta">
          Visual authority only: combat decisions stay on backend side.
        </p>
        <div style={{ aspectRatio: `${1 / combatCanvasAspectRatio}` }}>
          <CombatCanvas
            viewModel={combatViewModel}
            onUnitTap={handleTargetTap}
          />
        </div>
      </article>

      <article className="tavern-card" data-testid="combat-hud-card">
        <CombatHud
          resource={resource}
          resourceLabel="Energy"
          target={demoTarget}
          skills={demoSkills}
          feedback={feedback}
          onSkillPress={handleSkillPress}
        />
      </article>

      <article className="tavern-card" data-testid="combat-comms-card">
        <CombatCommsPanel
          connected={combatCommsConnected}
          viewerIsRaidLead={viewerIsRaidLead}
          feed={commsFeed}
          selectedEnemyEntityId={selectedEnemyEntityId}
          onSendEmoji={sendEmoji}
          onSendPhrase={sendQuickPhrase}
          onSendRaidLead={sendRaidLeadCommand}
        />
      </article>
    </section>
  );
}
