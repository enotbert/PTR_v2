type CombatSkillState = "ready" | "cooldown" | "no-resource" | "invalid-target";

export type CombatSkillViewModel = {
  id: string;
  label: string;
  resourceCost: number;
  cooldownRemainingMs: number;
  state: CombatSkillState;
  reason?: string;
};

export type CombatTargetViewModel = {
  id: string;
  label: string;
  hp: number;
  maxHp: number;
  canBeTargeted: boolean;
  invalidReason?: string;
};

type CombatHudProps = {
  resource: number;
  resourceLabel: string;
  target: CombatTargetViewModel | null;
  skills: CombatSkillViewModel[];
  feedback: string;
  onSkillPress: (skillId: string) => void;
};

function formatCooldown(ms: number): string {
  if (ms <= 0) {
    return "Ready";
  }
  return `${Math.ceil(ms / 1000)}s`;
}

export function CombatHud({
  resource,
  resourceLabel,
  target,
  skills,
  feedback,
  onSkillPress,
}: CombatHudProps) {
  return (
    <section className="combat-hud" aria-labelledby="combat-hud-title">
      <h2 id="combat-hud-title" className="tavern-card__title">
        Combat controls
      </h2>

      <p className="tavern-card__meta" data-testid="combat-resource">
        {resourceLabel}: {resource}
      </p>

      <div className="combat-hud__target" data-testid="combat-target">
        <p className="tavern-card__meta">
          Target:{" "}
          {target
            ? `${target.label} (${target.hp}/${target.maxHp} HP)`
            : "No target selected"}
        </p>
        {target && !target.canBeTargeted ? (
          <p className="combat-hud__hint" data-testid="combat-target-hint">
            {target.invalidReason ?? "Target cannot be selected right now."}
          </p>
        ) : null}
      </div>

      <div className="combat-hud__skills" data-testid="combat-skill-bar">
        {skills.map((skill) => {
          const disabled = skill.state !== "ready";
          return (
            <button
              key={skill.id}
              type="button"
              className="combat-hud__skill"
              data-testid={`combat-skill-${skill.id}`}
              data-skill-state={skill.state}
              disabled={disabled}
              aria-disabled={disabled}
              onClick={() => {
                onSkillPress(skill.id);
              }}
            >
              <span className="combat-hud__skill-label">{skill.label}</span>
              <span className="combat-hud__skill-meta">
                Cost {skill.resourceCost}
              </span>
              <span className="combat-hud__skill-meta">
                CD {formatCooldown(skill.cooldownRemainingMs)}
              </span>
              {skill.reason ? (
                <span className="combat-hud__skill-meta">{skill.reason}</span>
              ) : null}
            </button>
          );
        })}
      </div>

      <p className="combat-hud__feedback" data-testid="combat-feedback">
        {feedback}
      </p>
    </section>
  );
}
