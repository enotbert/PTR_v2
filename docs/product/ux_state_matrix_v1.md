# UX/state matrix v1

Статус: draft v0.1
Связано с: PTR-15, PTR-34, [PRD v1](PRD_v1_public_early_access.md), [ADR-0007](../adr/0007-minimal-roles-and-skills-v1.md), [Enemy roster v1](enemy_roster_v1.md), [Weekly event v1](weekly_event_v1.md), [WebSocket protocol v1](../tech/websocket-protocol-v1.md)

## 0. Роль документа

Этот документ фиксирует UX/state matrix для public EA v1:

- первая сессия;
- регулярная raid session;
- social/share session.

Документ нужен downstream UI-задачам, чтобы они не угадывали экраны, loading/error/offline/blocked states, главный CTA,
mobile constraints и минимальные Playwright-сценарии.

Документ не реализует production UI code, не выбирает новые mechanics и не заменяет PRD. Если здесь появляется
продуктовое решение, которого нет в PRD/ADR/source docs, оно помечается как требующее human confirmation.

## 1. Источники и известные разрывы

Использованные source-of-truth документы:

- `docs/product/PRD_v1_public_early_access.md` §5, §6.1-§6.8, §7-§9;
- `docs/product/weekly_event_v1.md` §3, §5-§7, §9;
- `docs/product/enemy_roster_v1.md` §1-§6, §9;
- `docs/adr/0007-minimal-roles-and-skills-v1.md`;
- `docs/tech/websocket-protocol-v1.md`.

Linear-задачи также ссылаются на `docs/foundation/01_product_foundation.md` и
`docs/foundation/03_linear_codex_agent_workflow.md`, но этих файлов нет в текущем дереве `docs/`. При обновлении
затронутых Linear/doc references такие ссылки нужно убирать или заменять актуальными product/tech docs из текущего
репозитория.

## 2. Глобальные UX-ограничения

| Ограничение | Требование для UI-задач |
|---|---|
| Mobile-first | Основной viewport — телефонный размер iOS Safari / Android Chrome. Desktop — вторичный сценарий без desktop-only mechanics. |
| Touch-first | Любое обязательное действие доступно тапом. Нет hover-only, точного cursor aiming или keyboard-only действий. |
| Safe area/browser chrome | Главный CTA и combat controls остаются доступными с mobile browser chrome и safe-area insets. Нижние controls не прячутся за home indicator. |
| No key layout shift | Tavern, combat, reward и share states резервируют место под ключевые поверхности, чтобы loading/error не сдвигали главный CTA. |
| Server authority | UI может показывать hints, локальное выделение и disabled states, но backend/WebSocket/API остаётся source of truth для combat, rewards и progress. |
| Offline shell | Offline shell разрешён. Offline gameplay queue запрещён. Backend-dependent actions показывают blocked state. |
| No free text combat chat | Combat communication использует только predefined raid lead commands, emoji и quick phrases. |

## 3. Общий словарь состояний

| State | Смысл | Ожидание от UI |
|---|---|---|
| Empty | На поверхности ещё нет player/session/content. | Объяснить ближайшее полезное действие, а не показывать пустой экран. |
| Loading | Клиент получает начальные REST-данные или ждёт первый WebSocket snapshot. | Показать skeleton/progress без сдвига зоны главного CTA. |
| Reconnecting | WebSocket разорван, heartbeat timeout или обнаружен sequence gap. | Заморозить/disable authoritative actions и объяснить восстановление fresh snapshot. |
| Error | Запрос упал и может быть повторён без изменения продуктового состояния. | Показать user-safe copy, retry CTA и fallback-навигацию. |
| Offline | У браузера нет сети. | Оставить shell читаемым, скрыть/disable gameplay actions, не ставить raid/combat/reward commands в очередь. |
| API unavailable | Сеть есть, но API/backend недоступен. | Объяснить service issue и дать retry/return tavern там, где это уместно. |
| Blocked | Intent игрока невалиден для текущего состояния, цели, cooldown, claim status, invite status или permissions. | Оставить игрока в flow, объяснить причину и дать ближайшее валидное действие. |

## 4. Матрица первой сессии

| Шаг | Экран/state | Главный CTA | Empty/loading/error/offline/blocked states | Mobile risks |
|---|---|---|---|---|
| 1 | PWA start shell | `Start first raid`, когда online и API ready | Empty: welcome + one-line promise. Loading: проверка network/API. Offline: offline shell и disabled gameplay CTA. API unavailable: retry. | Hero copy и CTA помещаются в small viewport и не выталкивают network status ниже fold. |
| 2 | Connectivity/status surface | `Retry connection` или продолжение при healthy state | Offline/API unavailable — first-class states, а не скрытые toast. Offline gameplay queue отсутствует. | Network banner не перекрывает primary CTA и нижний browser chrome. |
| 3 | Tutorial/solo raid setup | `Enter tutorial raid` | Loading: default `vanguard` loadout и tutorial raid data. Blocked: при missing session/profile вернуть к start/retry bootstrap. | Не делать многошаговый setup перед первым combat; role details можно свернуть. |
| 4 | Tutorial combat | `Use selected skill` после target selection | Loading: ожидание `battle.snapshot`. Reconnecting: skill commands disabled. Blocked: invalid target/cooldown показывает inline feedback. | Target tap zones и до 3 skill buttons доступны большим пальцем; нет hover target inspection. |
| 5 | Raid outcome | `Claim reward` | Loading: resolving outcome. Error: retry result fetch. Failed raid всё равно показывает small contribution, если применимо. | Outcome и CTA остаются видимыми без layout jump от animation/reward reveal. |
| 6 | Reward/tavern contribution | `Add to tavern` или `Return to tavern` | Already claimed: объяснить и продолжить. Error: retry claim. Offline/API unavailable: blocked, без queued claim. | Claim/continue CTA не скрывается нижним browser UI. |
| 7 | Next CTA | `View tavern progress` | Empty: если tavern progress временно недоступен, дать retry и secondary `Return to start`. `Start next raid` и `Share result` остаются secondary. | Показан один primary CTA; secondary options явно ниже по приоритету. |

Playwright baseline для first session:

- Открыть PWA в mobile viewport и проверить shell, network status и один primary CTA без layout shift.
- Сымитировать offline до bootstrap и проверить, что gameplay CTA disabled, а copy не обещает offline gameplay.
- Пройти mocked tutorial path: выбрать enemy target, применить `vanguard_strike`, получить outcome, claim reward, увидеть tavern contribution/next CTA.
- Сымитировать invalid target или cooldown rejection и проверить user-safe blocked feedback без выхода из combat.

## 5. Матрица regular raid session

| Шаг | Экран/state | Главный CTA | Empty/loading/error/offline/blocked states | Mobile risks |
|---|---|---|---|---|
| 1 | Tavern home | `Start raid` | Empty: объяснить tavern progress и первый available raid. Loading: tavern/project skeleton. Offline: shell с disabled raid CTA. API unavailable: retry. Weekly project card всегда вторичен к main raid CTA, включая completed weekly event. | Tavern project, reward summary и raid CTA не конкурируют; один primary CTA. |
| 2 | Raid/party selection | `Join party` или `Start available raid` | Empty: no party available -> solo/available raid fallback. Loading: raid list/lobby state. Error: retry. | Party cards tappable без hover; избегать плотных таблиц. |
| 3 | Role/loadout | `Ready` / `Enter lobby` | Loading: role/loadout contract. Blocked: unavailable role/loadout падает в default `vanguard`; нет hard role gate для первого available raid. | Показать максимум 3 active skills выбранной роли; details могут раскрываться, CTA остаётся фиксированным. |
| 4 | Lobby | `Ready` / `Start raid` для raid lead | Loading: ожидание `lobby.snapshot`. Reconnecting: ready/start disabled до fresh snapshot. Blocked: lobby locked/started/full. | Presence/ready changes видны без manual refresh и мелких hover affordances. |
| 5 | Combat canvas | `Select target`, затем skill через HUD | Loading: ожидание `battle.snapshot`. Reconnecting: commands disabled. Error: return/retry snapshot. | Local player visually centered в нижней зоне canvas; enemy targets и links читаются на телефоне. |
| 6 | Combat HUD | `Use skill` / `Send command` | Blocked: invalid target, cooldown active, not raid lead, rate-limited communication. | До 3 skill buttons плюс communication controls; нет key layout shift при disabled/cooldown. |
| 7 | Outcome/result | `Claim reward` | Loading: resolving. Error: retry result. Failed raid объясняет contribution, если игрок eligible. | Result readable после удаления или collapse combat canvas. |
| 8 | Reward/progress | `Contribute to tavern` | Already claimed: continue. Weekly not eligible: explain. API unavailable: blocked retry. `Share result`, `Claim weekly cache` и `Return tavern` — secondary, если доступны. | Несколько rewards не создают несколько конкурирующих primary CTA. |
| 9 | Repeat/return/share | `Start next raid` или `Share result` | Empty: no next raid -> tavern. Error: retry share creation. | Share CTA вторичный, кроме поверхностей, явно посвящённых share/result. |

### 5.1 Tavern home — детальная state matrix v1 (PTR-34)

Назначение: конкретизировать экран **Tavern home** (шаг 1 таблицы §5) для PRD §6.2, §7 и downstream PTR-36 без добавления
UI-кода и без новых gameplay-механик вне `weekly_event_v1.md` / PRD.

#### Поверхности (IA-слоты)

| Поверхность | Роль | Связь с PRD / weekly |
|---|---|---|
| Зона главного raid CTA | Один dominant переход в raid flow (solo/party/available raid) | PRD §6.2, §6.3 |
| Weekly project card | `weekly_route_reopening`: название, shared progress, lifecycle (`active`, `completed`, `reward_claimable`, `expired`) | `weekly_event_v1.md` §3, §6; визуально **всегда secondary** к raid CTA, включая completed weekly (§8) |
| Rewards / contribution summary | Краткий снимок последнего вклада игрока и/или tavern-facing feedback после рейдов | PRD §6.2, §6.6 |
| Chronicle / recent events | Компактный список последних событий (в т.ч. weekly shared reward / chronicle entry) | PRD §6.2; пустой список не забирает primary CTA |

Все обязательные действия — **touch-first** (§2). Нет hover-only affordances. Слоты резервируют высоту до прихода данных,
чтобы skeleton/ошибка не сдвигали raid CTA из-под пальца (§2 «No key layout shift»).

#### Матрица состояний и главный CTA

| Экранное состояние | Условия | Главный CTA | Вторичные действия (не primary) | Примечания по empty/loading/error/offline/API |
|---|---|---|---|---|
| T1 Bootstrap | Первый заход на tavern home, ждём REST bundle (tavern/weekly/summary/chronicle) | Тот же label **`Start raid`**, **disabled**, в зарезервированной зоне + skeleton/короткий статус загрузки | Weekly/chronicle: skeleton или статичный placeholder без отдельной gameplay-кнопки | Loading: не менять вертикальный якорь primary CTA по сравнению с T2 |
| T2 Ready / online | API healthy, WebSocket применим к live hints (если есть), игрок может начать raid flow | **`Start raid`** | Карточка weekly (tap → деталь/hint), пункты chronicle (навигация), summary — информационно | Empty chronicle: copy «события появятся после рейдов», primary не меняется |
| T3 Raid entry заблокирован intent-ом | Backend/фича-флаг: сейчас нет валидного entry в бой с tavern home (например, все пути требуют шага party/selection) | **`Start raid`** ведёт в raid/party шаг §5.2 **с** server-driven empty/blocked copy (один primary label на tavern home) | `Join party` / быстрый переход к списку — **secondary**, если показан на этом экране | Не прятать блокировку за вторым экраном без объяснения на tavern — краткий inline рядом с disabled primary допустим |
| T4 Offline | `navigator.onLine === false` или эквивалент shell | **`Retry connection`** (восстановить сеть и обновить данные) | `Start raid` **disabled** с offline copy; weekly card — **только last-known read-only**, без claim/actions, требующих API | Offline gameplay queue запрещён (§2, §3) |
| T5 API unavailable | Сеть есть, HTTP/API недоступны для tavern bundle | **`Retry`** | Опционально secondary «к старту приложения», если deep link; без дублирующих конкурирующих primary | Copy user-safe, без технических stack trace |
| T6 Ошибка fetch tavern bundle | Retryable client/server error при загрузке tavern | **`Retry`** | `Return to start` только если уместен контекстом first-session shell | После успешного retry возврат к T1→T2 без смены layout-якоря |
| T7 Reconnecting (live hints) | WebSocket reconnecting, REST summary может быть stale для party presence | **`Start raid`** **disabled** до fresh snapshot + баннер reconnect | Weekly/chronicle read-only как при stale | Авторитетные действия заморожены (§3 «Reconnecting») |
| T8 Weekly `active` | Совпадает с T2/T3 с точки зрения CTA; карточка показывает progress | **`Start raid`** (как в T2/T3) | Weekly card: прогресс, tap за подробностями | `weekly_event_viewed` — см. `weekly_event_v1.md` §7 |
| T9 Weekly `completed` / `reward_claimable` / `expired` | Lifecycle weekly согласно `weekly_event_v1.md` | **`Start raid`** не уступает primary weekly-завершению | На карточке: hint «награда на экране рейда» / «claim в reward flow» / «неделя завершена» — **без второго равного primary** на той же высоте, что raid CTA | Claim weekly cache остаётся primary в **reward screen** §5.8; на tavern home только secondary entry через карточку |

#### Mobile и safe-area

- Primary CTA и weekly card укладываются в **small viewport** без горизонтального обязательного scroll для старта рейда.
- Primary CTA — в зоне большого пальца **выше** home indicator / нижнего browser chrome; не размещать единственный raid CTA под системной полосой.
- Статус сети / reconnecting (PTR-22 shell) **не перекрывает** зарезервированную зону raid CTA; при конфликте приоритет у доступности primary.
- Chronicle — вертикальный scroll внутри собственной области; scroll не должен маскировать raid CTA (раздельные регионы или collapse).

#### Copy: черновик v1 (на подтверждение владельцем продукта)

Строки ниже — **рекомендуемые** формулировки для согласования с @enotbert (acceptance criterion «спорные product/copy
decisions» в Linear PTR-34). До подтверждения downstream UI может использовать их как placeholder.

| Контекст | Черновик copy |
|---|---|
| T4 offline banner | «Нужна сеть, чтобы начать рейд. Таверна доступна для просмотра.» |
| T5 API unavailable | «Сервис недоступен. Попробуйте снова через минуту.» |
| T6 retry | «Не удалось загрузить таверну.» + кнопка `Retry` |
| T7 reconnecting | «Восстанавливаем соединение…» |
| Пустая chronicle (T2) | «Здесь появятся события таверны после рейдов.» |

Покрытие **PRD §6.2** и NFR §7: таблица выше явно фиксирует raid CTA, проект таверны, награды/вклад, хронику,
loading/offline/API/error/reconnecting и отсутствие hover-only / key layout shift. Ссылка на obsolete
`docs/foundation/01_product_foundation.md` в задаче PTR-34 **не используется** как source of truth; вместо неё —
PRD §6–§7 и этот документ (см. §1).

Playwright baseline для regular raid:

- Tavern home mobile smoke: raid CTA, weekly project card, reward/contribution summary и chronicle без hover-only controls.
- Lobby smoke: mocked `lobby.snapshot` обновляет ready state без manual refresh; reconnecting state disables authoritative actions.
- Combat smoke: mocked `battle.snapshot` рендерит party/enemies/target hints; target tap обновляет selection; skill command disabled при invalid target/cooldown.
- Reward smoke: completed, failed, claimable, already-claimed и API error states сохраняют понятный next CTA.

## 6. Матрица social/share session

| Шаг | Экран/state | Главный CTA | Empty/loading/error/offline/blocked states | Mobile risks |
|---|---|---|---|---|
| 1 | Invite/share open context | `Join raid` или `Open result` | Loading: resolve invite/share token. Invalid/expired: safe fallback to tavern/start. Offline: shell с disabled join. | Context объясняет, зачем игрока позвали, до просьбы действовать. |
| 2 | New/returning player gate | `Continue` / `Start tutorial` / `Return to tavern` | Empty session: lightweight bootstrap. Error: retry. Blocked: unsupported invite state. | Account/session copy короткий; invite context не теряется. |
| 3 | Join/play scenario | `Join party` или `Play available raid` | Party full/started/locked: new players получают `Start tutorial raid`, returning players получают `Return to tavern`. Reconnecting: wait for snapshot. | CTA остаётся валидным, если live lobby меняется пока игрок читает context. |
| 4 | Shared/result reward | `Claim reward` или `View tavern progress` | Not eligible: explain requirements. Already claimed: continue. API unavailable/offline: blocked retry, no queued claim. | Reward и share result copy помещаются в small viewport без modal traps. |
| 5 | Share/result follow-up | `Share result` / `Start raid` | Error creating share card: retry или continue. | Native share/web fallback tappable; Telegram-specific dependency нет. |

Playwright baseline для social/share:

- Открыть valid invite URL в mobile viewport и проверить context, join CTA и fallback при изменении lobby state.
- Открыть invalid/expired invite URL и проверить safe fallback to tavern/start без dead end.
- Открыть share/result URL и проверить shared result/reward context без Telegram-specific copy.
- Проверить, что для завершения share/invite flow не требуется free text или PII.

## 7. Acceptance criteria для downstream UI-задач

### PTR-22 — Mobile-first PWA app shell

- Shell резервирует место под network/API status и один primary CTA в small mobile viewport.
- Online, offline, API unavailable и loading states визуально различимы.
- Offline copy говорит, что shell доступен, но gameplay требует connection.
- Playwright покрывает first load mobile viewport и offline bootstrap.

### PTR-34 — Tavern home states

- Tavern home имеет один dominant raid CTA и secondary weekly/project/reward/chronicle surfaces (детализация: **§5.1**).
- State matrix включает loading, empty, offline, API unavailable и retryable error (строки T1–T7 в **§5.1**).
- Weekly project card использует `weekly_route_reopening` и показывает shared progress рядом с raid CTA.
- Weekly project card всегда secondary к main raid CTA, включая completed weekly event (T8–T9 в **§5.1**).

### PTR-42 — PixiJS CombatCanvas

- Canvas рендерит только view model: party formation, enemies, HP/effects markers, target highlights и links.
- Local player visually centered в нижней зоне canvas.
- Enemy support/link/channel states из enemy roster читаются на mobile.
- PixiJS objects не владеют authoritative combat state и не считают damage/heal/outcome.

### PTR-43 — React combat HUD и skill controls

- HUD показывает максимум 3 active skills текущей role/loadout и disabled/cooldown states.
- Invalid target, cooldown active и reconnecting states объясняются inline.
- Raid lead commands, emoji и quick phrases используют только predefined ids.
- Playwright/component smoke покрывает target selection, skill enabled/disabled state и blocked feedback.

### PTR-48 — Raid result и reward screen

- Completed и failed outcomes оба ведут к понятному reward/progress feedback.
- Claimable, claimed, already claimed, not eligible, offline/API unavailable и retryable error states покрыты.
- Видим ровно один primary next CTA. Если доступны tavern contribution и share result, primary — tavern contribution,
  share — secondary.
- Playwright/component smoke покрывает claim success, already-claimed и error retry.

### PTR-57 — Social/share session flow

- Invite/share context объясняет, к чему игрок присоединяется или что смотрит, до join/play CTA.
- Valid invite, invalid/expired invite, full/started lobby fallback и returning/new player paths покрыты.
- При expired/full invite new players получают `Start tutorial raid`, returning players получают `Return to tavern`.
- Shared/result reward handling объясняет eligibility и already-claimed states.
- Playwright покрывает valid invite, expired invite и result/share open в mobile viewport.

## 8. Подтверждённые UX/product decisions

- Weekly project card на tavern home всегда визуально вторичен к main raid CTA, включая completed weekly event.
- Primary CTA после reward в первой сессии: `View tavern progress`.
- При expired/full invite fallback зависит от player type: new players -> `Start tutorial raid`, returning players ->
  `Return to tavern`.
- Если на reward screen одновременно доступны tavern contribution и share result, primary CTA — tavern contribution,
  share result — secondary.
- Missing `docs/foundation/*` references нужно убирать или заменять текущими product/tech docs там, где затрагивается
  соответствующий Linear/doc reference.

## 9. Покрытие release gates

| Release gate | Покрытие матрицей |
|---|---|
| Первый цикл понятен без объяснения разработчика | First session matrix задаёт один primary CTA на шаг и явные offline/blocked states. |
| Игрок понимает, что делать после первого рейда | Reward/tavern contribution и next CTA states определены. |
| Игрок понимает, зачем возвращаться | Tavern home и weekly project card показывают shared progress и chronicle/reward feedback. |
| Игрок понимает, как координироваться без чата | Combat HUD покрывает predefined raid lead commands, emoji и quick phrases без free text. |
| iOS Safari / Android Chrome / small viewport | Global constraints и Playwright baselines требуют mobile viewport и safe-area/browser chrome checks. |
| Нет hover-only обязательных действий | Global constraints и downstream criteria требуют touch-first controls. |
| Offline shell работает предсказуемо | Common state vocabulary и PWA shell criteria запрещают offline gameplay queue и требуют blocked states. |
