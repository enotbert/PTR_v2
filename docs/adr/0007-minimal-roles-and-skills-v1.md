# 0007 — Принять минимальный состав ролей и навыков v1

- **Статус:** Accepted
- **Дата:** 2026-05-03
- **Авторы:** @enotbert
- **Связано с:** [PTR-11](https://linear.app/ptr-game/issue/PTR-11/prinyat-minimalnyj-nabor-rolej-i-navykov-v1), [PRD v1](../product/PRD_v1_public_early_access.md), [Lore v0.1](../product/LORE_v0.1.md)

## Контекст

Для публичной v1 Pocket Raid Tavern нужно закрыть продуктово-архитектурное решение о минимальном составе ролей,
навыков, cooldown/cost-принципов и правилах выбора цели. Без этого implementation issues по combat/backend/frontend
начинают угадывать боевую модель и расходиться между собой.

В продуктовой декомпозиции это решение называлось ADR-003. В `PTR_v2` номер `0003` уже занят решением о лицензии,
поэтому принятое решение фиксируется как следующий свободный ADR-0007.

Ограничения v1:

- бой mobile-first, без точного aim и без hover-only controls;
- не больше 4 основных активных кнопок в бою;
- backend остаётся source of truth для validation, cooldowns, effects, damage/heal и outcome;
- первый solo/tutorial raid не должен требовать идеального состава партии;
- свободного текстового чата в бою нет;
- лор задаёт тон и naming, но не расширяет механику без отдельного PRD/ADR.

## Рассмотренные варианты

- **Вариант A: 2 роли v1.** Плюс — минимальная реализация. Минус — не закрывает heal/cleanse и coordination/support,
  плохо поддерживает кооперативное обещание рейда.
- **Вариант B: 4 роли v1.** Плюс — покрывает protection, damage, heal/cleanse и coordination/support без перегруза
  mobile HUD. Минус — больше контента и валидации, чем у двух ролей.
- **Вариант C: 5 ролей v1, включая отдельного следопыта.** Плюс — полнее покрывает лор. Минус — расширяет scope,
  увеличивает балансировочную поверхность и не нужен для первого public EA.

Выбран вариант B.

## Решение

Для публичной v1 использовать **4 сменяемые роли/loadout**, по **3 активных навыка** на роль. Игрок может выбрать
роль перед рейдом или использовать дефолт. Вход в первый tutorial/solo raid не блокируется отсутствием других ролей:
состав партии влияет на удобство и устойчивость, но не является hard gate для первого опыта.

Роли являются режимами доступа к древней инфраструктуре мира, а не жёсткими профессиями героя. Лорная рамка из
`docs/product/LORE_v0.1.md`: дальнее будущее выглядит как фэнтези, защитные контуры читаются как воинская стойка,
плазменные руны как магия, священные протоколы как молитвы, а резонансные команды как бардовская поддержка.

### Роли v1

| Role id | Рабочее имя | Лорная опора | Назначение в рейде |
|---|---|---|---|
| `vanguard` | Страж контура | Воин получает доступ к защитным контурам и силовым каркасам | Держит удар, защищает союзника, даёт простой starter loadout |
| `arcweaver` | Плазморунный маг | Маг управляет плазменными рунами и вычислительными заклинаниями | Наносит урон и нарушает действия врагов |
| `machinist_priest` | Жрец-машинист | Чинит тело, броню и дух через священные протоколы | Лечит, снимает негативный эффект, стабилизирует партию |
| `signal_bard` | Бард-коммуникатор | Усиливает отряд через резонансные команды и эмоциональные паттерны | Фокусирует цель, усиливает партию, поддерживает координацию |

### Следопыт в v1

Лор также описывает следопыта, который читает сигналы мира как следы зверя. В v1 он не становится отдельной пятой
ролью, чтобы не расширять combat scope. Его функция чтения сигналов частично входит в `signal_bard` через
`mark_target`: игрок помогает партии увидеть важную цель и сфокусировать действия. Полноценный `scout`/`ranger`
остаётся post-v1 кандидатом, если позже появятся механики маршрутов, разведки, ловушек или позиционного преимущества.

### Стартовый loadout

- Дефолт для нового игрока: `vanguard`.
- Tutorial/solo raid использует `vanguard` и слабый сценарий, где игроку достаточно выбрать цель и применить
  базовый навык.
- В regular raid игрок может сменить роль до входа в бой.
- В v1 нет hard requirement вида "нужен healer/tank для старта". UI может показывать рекомендации по составу,
  но backend не блокирует первый доступный raid flow только из-за состава.

### Навыки v1

Минимальная модель навыка для downstream задач:

```text
id
name
role
intent: positive | negative
result_type: damage | heal | effect | shield | cleanse | control
target_team: ally | enemy | self | any
target_shape: single | group | all | area
cooldown
cost
effect_refs
validation_rules
```

#### `vanguard`

| Skill id | Название | intent | result_type | target_team | target_shape | cooldown | cost | Смысл |
|---|---|---|---|---|---|---|---|---|
| `vanguard_strike` | Удар силовым каркасом | negative | damage | enemy | single | short | 0 | Базовый урон по выбранной цели |
| `guard_ally` | Замкнуть контур | positive | shield | ally | single | medium | 0 | Даёт shield союзнику или себе, если выбран self |
| `taunt_signal` | Сигнал угрозы | negative | control | enemy | single | long | 0 | Вешает короткий taunt/attention marker на врага |

#### `arcweaver`

| Skill id | Название | intent | result_type | target_team | target_shape | cooldown | cost | Смысл |
|---|---|---|---|---|---|---|---|---|
| `arc_bolt` | Плазморунный разряд | negative | damage | enemy | single | short | 0 | Базовый урон по выбранной цели |
| `rune_overload` | Перегруз плазморун | negative | damage | enemy | group | long | 0 | Урон по группе врагов или ближайшим к target |
| `phase_disrupt` | Вычислительный сбой | negative | control | enemy | single | medium | 0 | Короткий interrupt/slow на выбранной цели |

#### `machinist_priest`

| Skill id | Название | intent | result_type | target_team | target_shape | cooldown | cost | Смысл |
|---|---|---|---|---|---|---|---|---|
| `mend_protocol` | Священный протокол починки | positive | heal | ally | single | short | 0 | Базовое лечение союзника или себя |
| `cleanse_routine` | Ритуал очистки сбоя | positive | cleanse | ally | single | medium | 0 | Снимает один негативный эффект |
| `stabilize_party` | Хор стабилизации | positive | shield | ally | all | long | 0 | Малый shield всей партии |

#### `signal_bard`

| Skill id | Название | intent | result_type | target_team | target_shape | cooldown | cost | Смысл |
|---|---|---|---|---|---|---|---|---|
| `signal_shot` | Резонансный сигнал | negative | damage | enemy | single | short | 0 | Базовый урон и видимый hit feedback |
| `mark_target` | Метка следа | negative | effect | enemy | single | medium | 0 | Вешает focus/vulnerability marker на врага |
| `rally_chord` | Резонансный сбор | positive | effect | ally | all | long | 0 | Короткий party buff без сложной экономики |

### Cooldown/cost

- `cooldown` в v1 backend-authoritative и выражается шкалой `short | medium | long`, которая при реализации
  мапится на конкретные server-side значения.
- UI показывает готовность навыка и disabled state, но не рассчитывает авторитетный cooldown.
- `cost` присутствует в контракте, но все стартовые навыки public v1 имеют `cost = 0`.
- Отдельный ресурс/mana/energy не вводится в v1.
- Ultimate/high-cost skills не входят в PTR-11 и требуют отдельного решения.

### Target rules

- Негативные навыки (`intent = negative`) валидны только по `enemy`, если `target_team` не `any`.
- Позитивные навыки (`intent = positive`) валидны по `ally`; `self` считается допустимым частным случаем союзника,
  если skill не запрещает self-cast.
- `target_shape = single` требует конкретный `target_id`.
- `target_shape = group` требует `target_group_id` или backend-derived группу вокруг выбранного `target_id`.
- `target_shape = all` не требует ручного выбора каждой цели; backend применяет эффект ко всей валидной party.
- При невалидной цели backend возвращает structured rejection, а UI показывает короткий blocked/invalid state.

## Последствия

### Положительные

- Implementation tasks получают стабильный roster, skill ids и target rules.
- 4 роли закрывают базовые combat needs: damage, protection, healing/cleanse и coordination/support.
- 3 активных навыка на роль укладываются в mobile-first ограничение "не больше 4 основных кнопок".
- `cost = 0` снижает сложность первой публичной версии, но сохраняет контрактное поле для будущего расширения.
- `vanguard` как дефолтный loadout позволяет сделать первый solo/tutorial raid понятным без ожидания партии.

### Отрицательные / компромиссы

- В v1 нет отдельной роли следопыта, хотя она есть в лоре.
- Балансировка 12 навыков всё ещё больше по объёму, чем минимальная двухролевая модель.
- Player-facing названия могут уточняться на UX/copy этапе, но стабильные `id` не должны меняться без нового решения.

### Что нужно сделать

- [ ] Downstream backend tasks используют перечисленные `skill_id` и target rules как input.
- [ ] Frontend HUD отображает максимум 3 active skills текущей роли, target hints и invalid target feedback.
- [ ] Combat renderer отображает target highlights, damage/heal/effect feedback и focus markers, но не считает outcome.
- [ ] Если позже нужен полноценный следопыт, создать отдельную Linear issue и PRD/ADR update.

## Ссылки

- [PRD v1 — Public Early Access](../product/PRD_v1_public_early_access.md)
- [Lore v0.1 — Pocket Raid Tavern](../product/LORE_v0.1.md)
- [PTR-11](https://linear.app/ptr-game/issue/PTR-11/prinyat-minimalnyj-nabor-rolej-i-navykov-v1)
