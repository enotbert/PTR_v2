import { useEffect, useMemo, useRef } from "react";

type CombatSide = "party" | "enemy";

type CombatUnitViewModel = {
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

type CombatCanvasViewModel = {
  party: CombatUnitViewModel[];
  enemies: CombatUnitViewModel[];
};

type Props = {
  viewModel: CombatCanvasViewModel;
};

const ARENA_ASPECT_RATIO = 0.62;

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + safeRadius, y);
  ctx.arcTo(x + width, y, x + width, y + height, safeRadius);
  ctx.arcTo(x + width, y + height, x, y + height, safeRadius);
  ctx.arcTo(x, y + height, x, y, safeRadius);
  ctx.arcTo(x, y, x + width, y, safeRadius);
  ctx.closePath();
}

function drawUnit(
  ctx: CanvasRenderingContext2D,
  unit: CombatUnitViewModel,
  x: number,
  y: number,
  radius: number,
) {
  const hpRatio =
    unit.maxHp > 0 ? Math.max(0, Math.min(1, unit.hp / unit.maxHp)) : 0;
  const coreColor = unit.side === "party" ? "#60a5fa" : "#f97316";
  const ringColor =
    unit.highlight === "targeted"
      ? "#facc15"
      : unit.highlight === "selected"
        ? "#a78bfa"
        : "#334155";

  ctx.save();
  ctx.lineWidth = Math.max(2, radius * 0.12);
  ctx.strokeStyle = ringColor;
  ctx.fillStyle = coreColor;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  if (unit.isLocalPlayer) {
    ctx.fillStyle = "#ffffff";
    ctx.font = `${Math.max(10, radius * 0.42)}px system-ui`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("YOU", x, y - radius * 1.35);
  }

  const hpWidth = radius * 1.75;
  const hpHeight = Math.max(4, radius * 0.22);
  const hpX = x - hpWidth / 2;
  const hpY = y + radius + 8;
  drawRoundedRect(ctx, hpX, hpY, hpWidth, hpHeight, hpHeight / 2);
  ctx.fillStyle = "#1e293b";
  ctx.fill();
  drawRoundedRect(ctx, hpX, hpY, hpWidth * hpRatio, hpHeight, hpHeight / 2);
  ctx.fillStyle = hpRatio > 0.35 ? "#22c55e" : "#ef4444";
  ctx.fill();

  if (unit.effects.length > 0) {
    ctx.fillStyle = "#f8fafc";
    ctx.font = `${Math.max(10, radius * 0.38)}px system-ui`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(unit.effects[0], x + radius * 0.98, y - radius * 0.98);
  }

  ctx.fillStyle = "#f8fafc";
  ctx.font = `${Math.max(11, radius * 0.4)}px system-ui`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(unit.label, x, y);
  ctx.restore();
}

function renderArena(ctx: CanvasRenderingContext2D, vm: CombatCanvasViewModel) {
  const width = ctx.canvas.width;
  const height = ctx.canvas.height;

  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#0f172a");
  gradient.addColorStop(1, "#111827");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(width * 0.08, height * 0.48);
  ctx.lineTo(width * 0.92, height * 0.48);
  ctx.stroke();

  const radius = Math.max(18, Math.min(width, height) * 0.075);
  const partyY = height * 0.74;
  const enemyY = height * 0.22;
  const spacing = width / 4;
  const start = width * 0.2;

  for (const unit of vm.party) {
    const x = start + spacing * unit.laneIndex;
    drawUnit(ctx, unit, x, partyY, radius);
  }
  for (const unit of vm.enemies) {
    const x = start + spacing * unit.laneIndex;
    drawUnit(ctx, unit, x, enemyY, radius);
  }
}

export function CombatCanvas({ viewModel }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const cssWidth = canvas.clientWidth;
    const cssHeight = canvas.clientHeight;
    canvas.width = Math.floor(cssWidth * dpr);
    canvas.height = Math.floor(cssHeight * dpr);
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.scale(dpr, dpr);
    renderArena(context, viewModel);
  }, [viewModel]);

  return (
    <div className="combat-canvas">
      <canvas
        ref={canvasRef}
        className="combat-canvas__surface"
        data-testid="combat-canvas"
        aria-label="Combat arena presentation"
      />
    </div>
  );
}

export function useDemoCombatViewModel(): CombatCanvasViewModel {
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
          highlight: "selected",
        },
        {
          id: "party-ranger",
          label: "RG",
          side: "party",
          hp: 55,
          maxHp: 100,
          effects: ["B"],
          laneIndex: 1,
          highlight: "none",
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
          highlight: "none",
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
          highlight: "targeted",
        },
        {
          id: "enemy-caster",
          label: "C1",
          side: "enemy",
          hp: 63,
          maxHp: 100,
          effects: ["!"],
          laneIndex: 1,
          highlight: "none",
        },
        {
          id: "enemy-brute",
          label: "B1",
          side: "enemy",
          hp: 88,
          maxHp: 100,
          effects: [],
          laneIndex: 2,
          highlight: "none",
        },
      ],
    }),
    [],
  );
}

export const combatCanvasAspectRatio = ARENA_ASPECT_RATIO;
