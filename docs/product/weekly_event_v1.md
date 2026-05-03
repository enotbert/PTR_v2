# Weekly event v1 — Route Reopening

Статус: accepted v0.1
Связано с: PTR-13, [PRD v1](PRD_v1_public_early_access.md), [Lore v0.1](LORE_v0.1.md), [Enemy roster v1](enemy_roster_v1.md)

## 0. Роль документа

Этот документ фиксирует первый weekly event/modifier для public EA v1. Он является product source of truth для
reward/progress/tavern/share задач, которым нужно знать, какой weekly loop реализовывать.

Документ фиксирует:

- выбранный `weekly_event_id`;
- минимальную механику weekly contribution;
- reward/progress effect;
- UX entry points;
- analytics events;
- границу prototype/tuning content.

Документ не фиксирует:

- точные contribution numbers;
- точные reward quantities;
- окончательные weekly reset timezone/timestamp правила;
- backend schema, migration или API contract;
- финальный art/copy для route beacon.

Если implementation требует новых persistent fields, API endpoints или WebSocket events, это оформляется в
соответствующей backend/API/live task и при необходимости отдельным ADR.

## 1. Рассмотренные варианты

| Option id | Название | Суть | Плюсы | Минусы |
|---|---|---|---|---|
| `weekly_route_reopening` | Неделя закрытого маршрута | Игроки стабилизируют один закрытый маршрут через обычные рейды; каждый raid outcome даёт вклад в общий weekly progress, `route_warden`/`route_anchor` дают тематический бонус | Лучше всего связывает лор таверны-маяка, enemy roster и общий вклад; минимально для v1 | Требует простой weekly progress state и reward eligibility |
| `weekly_unstable_circuits` | Нестабильные контуры | Все рейды недели получают лёгкий combat modifier: больше shield/guard-link связей, враги чаще поддерживают друг друга | Хорошо показывает combat vector enemy synergy | Риск рано усложнить combat tuning; хуже объясняет общий вклад |
| `weekly_role_call` | Зов ролей | Неделя просит закрывать рейды разными ролями/loadout; вклад зависит от разнообразия ролей в партии | Поддерживает роли и social invite | Требует больше party/loadout analytics и может конфликтовать с правилом “нет hard role gate” |

Выбран `weekly_route_reopening`.

## 2. Решение v1

Первый weekly event public EA:

```text
weekly_event_id = weekly_route_reopening
display_name = Неделя закрытого маршрута
```

Игровая формула события:

```text
рейды недели -> вклад в общий маршрут -> visible tavern progress -> reward/share reason
```

Игроки помогают таверне стабилизировать закрытый маршрут. Любой завершённый raid добавляет вклад в общий weekly
project. Неудачный raid тоже даёт малый вклад, чтобы сохранить принцип “почти всегда есть награда”. Рейды, где
побеждены `route_anchor` или `route_warden`, дают тематический bonus contribution.

## 3. Минимальная механика

- В tavern home есть текущий weekly project: “Стабилизировать закрытый маршрут”.
- Weekly project отображается рядом с главным raid CTA, а не как отдельная тяжёлая live-ops страница.
- У weekly event есть server-authoritative lifecycle state: `active`, `completed`, `reward_claimable`, `expired`.
- Любой завершённый raid даёт weekly contribution.
- Неудачный raid даёт `raid_failed_small` contribution.
- `route_anchor_defeated` и `route_warden_defeated` дают тематический bonus contribution.
- Shared progress отображается как общий progress bar таверны.
- При достижении цели таверна получает visible state: маршрут стабилизирован, запись в хронике, shareable result.
- Игрок получает personal reward, только если сделал хотя бы один eligible contribution за неделю.
- Точный reset schedule, time zone и итоговые contribution numbers являются implementation/tuning details, а не
  продуктовой механикой этого документа.

## 4. Contribution sources

| Source | Когда возникает | Product meaning |
|---|---|---|
| `raid_completed` | Raid завершён успехом | Основной weekly contribution |
| `raid_failed_small` | Raid завершён неуспехом, но player участвовал | Малый вклад, чтобы не обнулять сессию |
| `route_anchor_defeated` | В raid побеждён `route_anchor` | Тематический вклад в стабилизацию маршрута |
| `route_warden_defeated` | В raid побеждён `route_warden` | Крупный тематический вклад и хороший share hook |

## 5. Rewards/progress effect

Public EA content:

- shared progress: tavern weekly project progress;
- personal eligibility: игрок сделал хотя бы один eligible contribution в текущем weekly event;
- personal reward: small weekly cache/materials после claim;
- shared reward: tavern chronicle entry и visible route beacon/progress state;
- share hook: “Мы стабилизировали маршрут на X%” или “Маршрут открыт”.

Prototype/tuning content:

- exact contribution numbers;
- exact reward quantities;
- exact cache content;
- final copy/art for route beacon state;
- exact reset timestamp/timezone rules.

## 6. UX entry points

| Surface | Что показывать |
|---|---|
| Tavern home | Weekly project card рядом с главным raid CTA: название, progress, next action |
| Raid setup | Короткий hint: этот raid помогает weekly route |
| Post-raid result | Вклад игрока и изменение общего progress |
| Reward screen | Claim weekly cache, если player eligible |
| Share/result card | Progress или completion weekly result |

## 7. Analytics

Используем существующие funnel events и добавляем минимальные weekly events.

| Event | Назначение | Минимальный payload |
|---|---|---|
| `weekly_event_viewed` | Понять, видят ли игроки weekly project | `weekly_event_id`, `surface` |
| `weekly_contribution_made` | Измерить вклад и источники progress | `weekly_event_id`, `source`, `raid_id`, `contribution_bucket`, `progress_bucket_after` |
| `weekly_reward_claimed` | Проверить, забирают ли weekly reward | `weekly_event_id`, `reward_type` |
| `share_card_created` | Уже существующее событие; добавить weekly context | `context = weekly_event`, `weekly_event_id`, `completion_state` |

Privacy note: payload не должен содержать свободный пользовательский текст или PII. `contribution_bucket` и
`progress_bucket_after` можно агрегировать, если точные значения не нужны для v1 analytics.

## 8. Scope guard

Не вводим в v1:

- battle pass;
- сезонную монетизацию;
- магазин;
- FOMO-косметику;
- полноценный live-ops календарь;
- daily quests;
- PvP leaderboard;
- сложную экономику;
- обязательный идеальный состав партии.

## 9. Downstream expectations

Reward/progress/backend задачи должны использовать этот документ как input для:

- `weekly_event_id`;
- lifecycle states: `active`, `completed`, `reward_claimable`, `expired`;
- contribution sources;
- personal eligibility rule;
- reward/progress categories.

Tavern/frontend/share задачи должны использовать этот документ как input для:

- tavern weekly project card;
- raid setup hint;
- post-raid weekly contribution feedback;
- weekly reward claim surface;
- share/result context.
