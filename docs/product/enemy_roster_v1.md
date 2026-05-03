# Enemy roster v1 — Public Early Access

Статус: accepted v0.1
Связано с: PTR-12, [PRD v1](PRD_v1_public_early_access.md), [Lore v0.1](LORE_v0.1.md), [ADR-0007](../adr/0007-minimal-roles-and-skills-v1.md)

## 0. Роль документа

Этот документ фиксирует минимальный набор PvE-врагов и мини-босса для public EA v1. Он задаёт игровой вектор
combat slice: враги не являются независимыми манекенами, а помогают друг другу через простые читаемые связи.

Документ является source of truth для:

- стабильных `enemy_id` и `boss_id` public EA;
- базовых ролей врагов в бою;
- минимальных state names и targetability;
- минимальной комбинаторики волн;
- boss encounter grammar с миньонами;
- границы между prototype tuning и public EA content.

Документ не фиксирует:

- точные HP/damage/cooldown/loot numbers;
- production tuning экономики;
- финальные sprites, VFX, SFX и animations;
- точные wave timings;
- backend schema или WebSocket protocol details.

Если новый враг, новая boss grammar или новая механика взаимодействия врагов расширяет scope v1, изменение проходит
через Linear issue и PRD/ADR update.

## 1. Combat vector v1

Боевая часть v1 должна развиваться в сторону **target priority через синергию врагов**.

Игрок выбирает цель не только по HP. Он читает, кто сейчас:

- усиливает другого врага;
- защищает channel или boss protocol;
- создаёт mark/pressure;
- поддерживает guard link босса;
- открывает окно `exposed`/`staggered`, если его убрать первым.

Это не hard puzzle и не action timing. Boss и обычные враги остаются targetable, но UI должен объяснять связи и
подсказывать, почему конкретная цель сейчас важна. Backend остаётся source of truth для outcome; клиент показывает
target hints, links и readable states, но не рассчитывает результат.

## 2. Synergy primitives

| Primitive | Смысл | Зачем в v1 |
|---|---|---|
| `mark` | Враг помечает цель или союзника, меняя приоритет действий | Учит фокусить источник угрозы, а не просто ближайшую цель |
| `repair` / `shield` | Support-враг продлевает жизнь другого врага | Учит сначала убирать поддержку или выбирать burst window |
| `channel` | Телеграфируемое действие, которое хочется прервать или пережить | Даёт понятный момент для control/focus skills |
| `guard_link` | Minion поддерживает защиту или протокол босса, пока жив | Делает boss encounter структурным: сначала minions, затем boss window |

## 3. Enemy roster

| Enemy id | Рабочее имя | Роль в бою | Синергия | Базовые состояния | Targetability | Rewards/progress |
|---|---|---|---|---|---|---|
| `rustbound_striker` | Ржавый налётчик | Базовый pressure/damage враг | Получает выгоду от `signal_leech.mark`; становится опаснее, если `circuit_mender` держит его shield/repair | `active`, `winding_up`, `marked`, `shielded`, `staggered`, `defeated` | Всегда валидная enemy-цель; хороший первый target tutorial | Малый salvage/materials; ремонт таверны |
| `signal_leech` | Пиявка сигнала | Debuff/channel враг | Помечает союзника или врага, создавая priority target; в паре со striker учит сначала снять источник mark/channel или пережить pressure | `active`, `channeling`, `jammed`, `staggered`, `defeated` | Валидная enemy-цель; во время `channeling` UI подсвечивает interrupt/focus hint | Signal fragments; восстановление маршрутов/связи таверны |
| `circuit_mender` | Сбойный починщик | Support-враг | Чинит или экранирует союзного врага; в паре с leech защищает channel, в паре со striker продлевает pressure | `active`, `repairing`, `shielding`, `staggered`, `defeated` | Валидная enemy-цель; target hint объясняет, кого он поддерживает | Repair cores/materials; комнаты/защитные контуры таверны |
| `route_anchor` | Маршрутный якорь | Minion/link enemy | Поддерживает `route_warden.guard_link`; пока якорь жив, босс частично защищён или заряжает протокол быстрее | `active`, `linked`, `overloaded`, `defeated` | Валидная enemy-цель; в boss encounter получает high-priority hint `break link` | Route sparks/key fragments; прогресс открытия маршрута |

## 4. Минимальная комбинаторика волн

В v1 достаточно зафиксировать reusable wave patterns без точных чисел.

| Pattern id | Состав | Что проверяет | Ожидаемое решение игрока |
|---|---|---|---|
| `tutorial_pressure` | `rustbound_striker` | Tap target -> basic skill -> reward | Бить очевидную цель |
| `mark_pressure` | `rustbound_striker` + `signal_leech` | Первый выбор приоритета: урон сейчас или источник mark/channel | Сфокусить `signal_leech`, если он `channeling`, иначе снизить pressure striker |
| `protected_channel` | `signal_leech` + `circuit_mender` | Support защищает опасный channel | Сфокусить/контролить leech или убрать mender, если shield мешает burst |
| `sustained_pressure` | `rustbound_striker` + `circuit_mender` | Support продлевает жизнь damage-врага | Часто выгоднее сначала убрать `circuit_mender` |
| `mixed_skirmish` | `rustbound_striker` + `signal_leech` + `circuit_mender` | Полная mini-combat grammar v1 | Читать связи: кто `channeling`, кто `shielded`, кто поддерживает кого |

## 5. Mini-boss roster

| Boss id | Рабочее имя | Роль в рейде | Синергия с миньонами | Базовые состояния | Targetability | Rewards/progress |
|---|---|---|---|---|---|---|
| `route_warden` | Смотритель закрытого маршрута | Первый reusable mini-boss: охраняет закрытый маршрут/узел древней сети | Начинает encounter с `route_anchor` minions. Пока хотя бы один `route_anchor` active/linked, boss в `guarded` или быстрее входит в `charging_protocol`. Уничтожение якорей переводит босса в `exposed`/`staggered` window | `active`, `guarded`, `charging_protocol`, `exposed`, `staggered`, `defeated` | Boss всегда targetable, но UI объясняет, что сначала выгоднее убрать minions; damage по boss под guard link не запрещён, но менее эффективен | Route key fragment, крупный salvage, tavern contribution, shareable result `открыт маршрут` |

## 6. Boss encounter grammar

Минимальное правило для всех boss fights v1 и будущего расширения:

1. Boss почти всегда приходит с minions.
2. Начинать зачистку оптимально с minions, потому что они поддерживают shield/channel/charge босса.
3. Boss взаимодействует с minions: усиливает, переподключает, получает от них `guard_link` или ускоряет протокол.
4. После удаления minions появляется понятное окно `exposed`/`staggered`, где party фокусит boss.
5. Это не hard puzzle: boss остаётся targetable, но target hints и эффективность подсказывают правильный приоритет.

## 7. Prototype vs public EA content

Public EA content:

- stable ids: `rustbound_striker`, `signal_leech`, `circuit_mender`, `route_anchor`, `route_warden`;
- enemy roles, targetability, базовые state names и synergy primitives;
- wave pattern ids как дизайн-контракт для downstream combat/backend/frontend задач;
- reward/progress categories: salvage/materials, signal fragments, repair cores, route sparks/key fragments,
  tavern contribution;
- boss grammar: сначала minions/links, затем boss window.

Prototype content:

- точные HP/damage/cooldown numbers;
- точные proc chances, shield values, duration tuning;
- финальные sprites, VFX, SFX и animations;
- production loot amounts;
- точные wave timings и AI tuning.

## 8. Scope guard

Не вводим в v1:

- PvP;
- сложное позиционирование;
- resistances;
- free-form AI;
- длинные raid phases;
- boss puzzle с единственным решением;
- action timing как обязательное условие победы.

Вся сложность public EA v1 в этой части — в читаемом приоритете целей и простых связях `кто кого поддерживает`.

## 9. Downstream expectations

Backend/combat задачи должны использовать этот документ как input для:

- `enemy_id` и `boss_id`;
- допустимый словарь состояний или эквивалентные backend states с тем же смыслом;
- server-authoritative расчёт синергий;
- reward/progress categories;
- wave pattern fixtures.

Frontend/combat renderer задачи должны использовать этот документ как input для:

- target hints;
- визуальные связи между support/minion и поддерживаемой целью;
- читаемые состояния channel/guard/shield;
- feedback для boss windows `exposed`/`staggered`.
