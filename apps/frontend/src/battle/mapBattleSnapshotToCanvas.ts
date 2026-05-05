import type {
  CombatCanvasViewModel,
  CombatUnitViewModel,
} from "../components/CombatCanvas";
import type { BattleSnapshotPayloadWire } from "./battleCommsTypes";

function shortEntityLabel(entityId: string): string {
  const tail = entityId.includes(":")
    ? (entityId.split(":").pop() ?? entityId)
    : entityId;
  const compact = tail.replaceAll("_", "").slice(0, 3);
  return compact.length > 0 ? compact.toUpperCase() : "???";
}

export function mapBattleSnapshotToCanvas(
  payload: BattleSnapshotPayloadWire,
  localPlayerId: string,
  selectedUnitId: string | null,
  raidLeadHighlightEntityId: string | null,
): CombatCanvasViewModel {
  const byId = new Map(
    payload.entities.map((entity) => [entity.entity_id, entity]),
  );

  const party: CombatUnitViewModel[] = payload.party_order.map(
    (entityId, laneIndex) => {
      const row = byId.get(entityId);
      const hp = row?.hp;
      const maxHp = hp?.max ?? 1;
      const current = hp?.current ?? 0;
      const highlight =
        raidLeadHighlightEntityId === entityId
          ? "targeted"
          : selectedUnitId === entityId
            ? "selected"
            : "none";
      return {
        id: entityId,
        label: shortEntityLabel(entityId),
        side: "party",
        hp: current,
        maxHp,
        effects: [],
        laneIndex,
        highlight,
        isLocalPlayer: entityId === `player:${localPlayerId}`,
      };
    },
  );

  const enemiesRaw = payload.entities.filter(
    (e) => e.kind === "enemy" || e.kind === "boss",
  );
  enemiesRaw.sort((a, b) => a.entity_id.localeCompare(b.entity_id));

  const enemies: CombatUnitViewModel[] = enemiesRaw.map((row, laneIndex) => {
    const hp = row.hp;
    const maxHp = hp?.max ?? 1;
    const current = hp?.current ?? 0;
    const highlight =
      raidLeadHighlightEntityId === row.entity_id
        ? "targeted"
        : selectedUnitId === row.entity_id
          ? "selected"
          : "none";
    return {
      id: row.entity_id,
      label: shortEntityLabel(row.entity_id),
      side: "enemy",
      hp: current,
      maxHp,
      effects: [],
      laneIndex,
      highlight,
    };
  });

  return { party, enemies };
}
