import { Application, Container, Graphics, Text, TextStyle } from "pixi.js";
import { useEffect, useMemo, useRef } from "react";

type CombatSide = "party" | "enemy";

export type CombatUnitViewModel = {
  id: string;
  label: string;
  side: CombatSide;
  hp: number;
  maxHp: number;
  effects: string[];
  laneIndex: number;
  highlight: "none" | "selected" | "targeted";
  isLocalPlayer?: boolean;
};

export type CombatCanvasViewModel = {
  party: CombatUnitViewModel[];
  enemies: CombatUnitViewModel[];
};

type Props = {
  viewModel: CombatCanvasViewModel;
  onUnitTap?: (unit: CombatUnitViewModel) => void;
};

const ARENA_ASPECT_RATIO = 0.62;

function pickUnitFromPoint(
  vm: CombatCanvasViewModel,
  x: number,
  y: number,
  width: number,
  height: number,
): CombatUnitViewModel | null {
  const radius = Math.max(18, Math.min(width, height) * 0.075);
  const spacing = width / 4;
  const start = width * 0.2;
  const placements: Array<{ unit: CombatUnitViewModel; x: number; y: number }> =
    [];
  for (const unit of vm.party) {
    placements.push({
      unit,
      x: start + spacing * unit.laneIndex,
      y: height * 0.74,
    });
  }
  for (const unit of vm.enemies) {
    placements.push({
      unit,
      x: start + spacing * unit.laneIndex,
      y: height * 0.22,
    });
  }
  let nearest: (typeof placements)[number] | null = null;
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (const placement of placements) {
    const dx = placement.x - x;
    const dy = placement.y - y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = placement;
    }
  }
  if (!nearest || nearestDistance > radius * 2) {
    return null;
  }
  return nearest.unit;
}

function drawUnit(
  unit: CombatUnitViewModel,
  x: number,
  y: number,
  radius: number,
  onUnitTap?: (unit: CombatUnitViewModel) => void,
): Container {
  const hpRatio =
    unit.maxHp > 0 ? Math.max(0, Math.min(1, unit.hp / unit.maxHp)) : 0;
  const coreColor = unit.side === "party" ? 0x60a5fa : 0xf97316;
  const ringColor =
    unit.highlight === "targeted"
      ? 0xfacc15
      : unit.highlight === "selected"
        ? 0xa78bfa
        : 0x334155;

  const root = new Container({ x, y });

  const body = new Graphics()
    .circle(0, 0, radius)
    .fill(coreColor)
    .stroke({ width: Math.max(2, radius * 0.12), color: ringColor });
  root.addChild(body);
  if (onUnitTap) {
    body.eventMode = "static";
    body.cursor = "pointer";
    body.on("pointertap", (event: import("pixi.js").FederatedPointerEvent) => {
      event.stopPropagation();
      onUnitTap(unit);
    });
  }

  const hpBarWidth = radius * 1.75;
  const hpBarHeight = Math.max(4, radius * 0.22);
  const hpBarY = radius + 8;
  const hpBase = new Graphics()
    .roundRect(
      -hpBarWidth / 2,
      hpBarY,
      hpBarWidth,
      hpBarHeight,
      hpBarHeight / 2,
    )
    .fill(0x1e293b);
  const hpFill = new Graphics()
    .roundRect(
      -hpBarWidth / 2,
      hpBarY,
      hpBarWidth * hpRatio,
      hpBarHeight,
      hpBarHeight / 2,
    )
    .fill(hpRatio > 0.35 ? 0x22c55e : 0xef4444);
  root.addChild(hpBase, hpFill);

  const label = new Text({
    text: unit.label,
    style: new TextStyle({
      fill: 0xf8fafc,
      fontSize: Math.max(11, radius * 0.4),
      fontFamily: "system-ui",
      fontWeight: "700",
      align: "center",
    }),
  });
  label.anchor.set(0.5);
  root.addChild(label);

  if (unit.effects.length > 0) {
    const effectLabel = new Text({
      text: unit.effects[0],
      style: new TextStyle({
        fill: 0xf8fafc,
        fontSize: Math.max(10, radius * 0.38),
        fontFamily: "system-ui",
        fontWeight: "600",
      }),
    });
    effectLabel.anchor.set(0.5);
    effectLabel.x = radius * 0.98;
    effectLabel.y = -radius * 0.98;
    root.addChild(effectLabel);
  }

  if (unit.isLocalPlayer) {
    const youLabel = new Text({
      text: "YOU",
      style: new TextStyle({
        fill: 0xffffff,
        fontSize: Math.max(10, radius * 0.42),
        fontFamily: "system-ui",
        fontWeight: "700",
      }),
    });
    youLabel.anchor.set(0.5);
    youLabel.y = -radius * 1.35;
    root.addChild(youLabel);
  }

  return root;
}

function renderArena(
  app: Application,
  root: Container,
  vm: CombatCanvasViewModel,
  width: number,
  height: number,
  onUnitTap?: (unit: CombatUnitViewModel) => void,
) {
  root.removeChildren();
  const placements: Array<{ unit: CombatUnitViewModel; x: number; y: number }> =
    [];

  const background = new Graphics()
    .rect(0, 0, width, height)
    .fill({ color: 0x0f172a, alpha: 1 });
  if (onUnitTap) {
    background.eventMode = "static";
    background.on(
      "pointertap",
      (event: import("pixi.js").FederatedPointerEvent) => {
        const point = event.getLocalPosition(root);
        let nearest: (typeof placements)[number] | null = null;
        let nearestDistance = Number.POSITIVE_INFINITY;
        for (const placement of placements) {
          const dx = placement.x - point.x;
          const dy = placement.y - point.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          if (distance < nearestDistance) {
            nearestDistance = distance;
            nearest = placement;
          }
        }
        if (nearest && nearestDistance <= radius * 2) {
          onUnitTap(nearest.unit);
        }
      },
    );
  }
  root.addChild(background);

  const separator = new Graphics()
    .moveTo(width * 0.08, height * 0.48)
    .lineTo(width * 0.92, height * 0.48)
    .stroke({ color: 0x334155, width: 2 });
  root.addChild(separator);

  const radius = Math.max(18, Math.min(width, height) * 0.075);
  const partyY = height * 0.74;
  const enemyY = height * 0.22;
  const spacing = width / 4;
  const start = width * 0.2;

  for (const unit of vm.party) {
    const x = start + spacing * unit.laneIndex;
    placements.push({ unit, x, y: partyY });
    root.addChild(drawUnit(unit, x, partyY, radius, onUnitTap));
  }
  for (const unit of vm.enemies) {
    const x = start + spacing * unit.laneIndex;
    placements.push({ unit, x, y: enemyY });
    root.addChild(drawUnit(unit, x, enemyY, radius, onUnitTap));
  }

  app.renderer.render({ container: app.stage });
  (app.canvas as HTMLCanvasElement).dataset.renderState = "ready";
}

export function CombatCanvas({ viewModel, onUnitTap }: Props) {
  const hostRef = useRef<HTMLButtonElement | null>(null);
  const appRef = useRef<Application | null>(null);
  const rootRef = useRef<Container | null>(null);

  useEffect(() => {
    let isDisposed = false;

    async function setupPixi() {
      const host = hostRef.current;
      if (!host || appRef.current) {
        return;
      }

      const app = new Application();
      await app.init({
        antialias: true,
        autoDensity: true,
        backgroundAlpha: 1,
        resizeTo: host,
      });
      if (isDisposed) {
        app.destroy(true);
        return;
      }

      const canvas = app.canvas as HTMLCanvasElement;
      canvas.className = "combat-canvas__surface";
      canvas.dataset.testid = "combat-canvas";
      canvas.ariaLabel = "Combat arena presentation";
      host.appendChild(canvas);

      const root = new Container();
      app.stage.addChild(root);
      appRef.current = app;
      rootRef.current = root;
      renderArena(
        app,
        root,
        { party: [], enemies: [] },
        host.clientWidth,
        host.clientHeight,
        onUnitTap,
      );
    }

    void setupPixi();

    return () => {
      isDisposed = true;
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
        rootRef.current = null;
      }
    };
  }, [onUnitTap]);

  useEffect(() => {
    const host = hostRef.current;
    const app = appRef.current;
    const root = rootRef.current;
    if (!host || !app || !root) {
      return;
    }
    renderArena(
      app,
      root,
      viewModel,
      host.clientWidth,
      host.clientHeight,
      onUnitTap,
    );
  }, [onUnitTap, viewModel]);

  const handleCanvasInteraction = (
    clientX: number,
    clientY: number,
  ): CombatUnitViewModel | null => {
    const host = hostRef.current;
    if (!host) {
      return null;
    }
    const rect = host.getBoundingClientRect();
    return pickUnitFromPoint(
      viewModel,
      clientX - rect.left,
      clientY - rect.top,
      rect.width,
      rect.height,
    );
  };

  return (
    <button
      type="button"
      ref={hostRef}
      className="combat-canvas"
      aria-label="Combat arena interactive preview"
      onClick={(event) => {
        if (!onUnitTap) {
          return;
        }
        const picked = handleCanvasInteraction(event.clientX, event.clientY);
        if (picked) {
          onUnitTap(picked);
        }
      }}
      onKeyDown={(event) => {
        if (!onUnitTap || (event.key !== "Enter" && event.key !== " ")) {
          return;
        }
        const host = hostRef.current;
        if (!host) {
          return;
        }
        const rect = host.getBoundingClientRect();
        const picked = pickUnitFromPoint(
          viewModel,
          rect.left + rect.width * 0.2,
          rect.top + rect.height * 0.22,
          rect.width,
          rect.height,
        );
        if (picked) {
          onUnitTap(picked);
          event.preventDefault();
        }
      }}
    />
  );
}

export function useDemoCombatViewModel(
  selectedTargetId: string | null = "enemy-sentry",
): CombatCanvasViewModel {
  return useMemo(
    () => ({
      party: [
        {
          id: "party-vanguard",
          label: "VG",
          side: "party",
          hp: 78,
          maxHp: 100,
          effects: ["S"],
          laneIndex: 0,
          highlight:
            selectedTargetId === "party-vanguard" ? "targeted" : "selected",
        },
        {
          id: "party-ranger",
          label: "RG",
          side: "party",
          hp: 55,
          maxHp: 100,
          effects: ["B"],
          laneIndex: 1,
          highlight: selectedTargetId === "party-ranger" ? "targeted" : "none",
          isLocalPlayer: true,
        },
        {
          id: "party-medic",
          label: "MD",
          side: "party",
          hp: 92,
          maxHp: 100,
          effects: ["H"],
          laneIndex: 2,
          highlight: selectedTargetId === "party-medic" ? "targeted" : "none",
        },
      ],
      enemies: [
        {
          id: "enemy-sentry",
          label: "S1",
          side: "enemy",
          hp: 44,
          maxHp: 100,
          effects: [],
          laneIndex: 0,
          highlight: selectedTargetId === "enemy-sentry" ? "targeted" : "none",
        },
        {
          id: "enemy-caster",
          label: "C1",
          side: "enemy",
          hp: 63,
          maxHp: 100,
          effects: ["!"],
          laneIndex: 1,
          highlight: selectedTargetId === "enemy-caster" ? "targeted" : "none",
        },
        {
          id: "enemy-brute",
          label: "B1",
          side: "enemy",
          hp: 88,
          maxHp: 100,
          effects: [],
          laneIndex: 2,
          highlight: selectedTargetId === "enemy-brute" ? "targeted" : "none",
        },
      ],
    }),
    [selectedTargetId],
  );
}

export const combatCanvasAspectRatio = ARENA_ASPECT_RATIO;
