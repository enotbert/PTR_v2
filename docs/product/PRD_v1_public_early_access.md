# PRD v1 — Public Early Access

Статус: draft v0.4
Owner: human product owner
Назначение: описать публичную v1 версию, которую можно отдавать внешним игрокам.

## 0. Модель документации и source of truth

- **`AGENTS.md`** — правила работы агента и ссылки на документы; без дублирования фактов о продукте, стеке и протоколах.
- **`docs/foundation/01_product_foundation.md`** — продуктовая формула, продуктовый scope v1, UX/PWA-принципы и продуктовое описание боя/live-ощущения.
- **Этот PRD** — source of truth по **публичному early access**: цели релиза, ключевые user flows, функциональные и нефункциональные требования, acceptance criteria и release gates для внешних игроков.
- **`docs/foundation/02_technical_foundation.md`** — tech stack, техконтракты (REST/OpenAPI, WebSocket-поведение, границы клиент/сервер), Docker и quality gates на уровне инженерии.
- **Архитектурные решения** — полный текст в `docs/architecture/adrs/ADR-*.md`; актуальный перечень принятых решений — в `docs/architecture/ADR_LOG.md` (только актуальные `Accepted`; при `Superseded` старый ADR из лога убирается).
- **`docs/foundation/03_linear_codex_agent_workflow.md`** — как оформлять Linear-задачи и handoff между ролями.

Правило обновления: меняется «что должно быть в публичной v1 для игрока и как это проверить» — правим этот PRD; меняется продуктовая рамка целиком — синхронизируем с `01_product_foundation.md`; меняется стек или техконтракт — `02_technical_foundation.md` и при необходимости ADR.

## 1. Цель v1

Запустить играбельную публичную PWA-версию Pocket Raid Tavern в формате early access.

v1 должна доказать, что работает базовая формула:

```text
Таверна + короткий рейд + инвайт/share + видимый общий вклад + weekly-событие
```

## 2. Не цель v1

v1 не должна доказывать:

- Telegram viral loop;
- native mobile distribution;
- сложную экономику;
- долгосрочную сезонную монетизацию;
- глубокий action combat;
- полноценную MMO-инфраструктуру;
- свободный текстовый чат в бою.

## 3. Целевая аудитория v1

- Игроки, которым нравится RPG-прогресс, но нет времени на длинные MMORPG-сессии.
- Игроки, готовые играть короткими заходами на телефоне.
- Друзья/маленькие группы, которым легко скинуть ссылку и сыграть вместе.
- Early adopters, готовые простить ограниченный контент, если core loop уже цепляет.

## 4. Игровое обещание v1

Открой таверну, собери короткий рейд, выбери цель и навыки, координируйся через команды/emoji без чата, победи мобов или босса, получи лут, вложи вклад в таверну и вернись за следующим улучшением.

## 5. Ключевые user flows

### 5.1. First session

1. Игрок открывает PWA.
2. Видит понятный стартовый экран и состояние сети.
3. Проходит короткое обучение или первый solo raid.
4. Понимает, как выбирать цель и применять навык.
5. Получает награду.
6. Видит, как награда влияет на таверну.
7. Получает следующий CTA.

### 5.2. Regular raid session

1. Игрок открывает таверну.
2. Выбирает рейд или пати.
3. Проверяет роль/loadout.
4. Заходит в бой.
5. Тапает цель и применяет навыки.
6. Видит live-изменения боя через server push.
7. Использует или получает RL-команды, emoji и быстрые фразы.
8. Получает результат рейда.
9. Забирает награды.
10. Вносит вклад или начинает следующий рейд.

### 5.3. Social/share session

1. Игрок получает ссылку или share-card.
2. Открывает PWA в релевантном контексте.
3. Понимает, зачем его позвали.
4. Присоединяется или играет доступный сценарий.
5. Получает shared/result reward, если условия выполнены.

## 6. Functional requirements

### 6.1. PWA shell

Продуктовые границы платформы и PWA: `docs/foundation/01_product_foundation.md` §4, §8, §10; ADR-0002 (PWA-only v1); обновление доков в задачах — ADR-0006.

- **Целевые платформы v1:** приложение открывается и поддерживается на **iOS Safari** и **Android Chrome** как основных клиентах; **desktop web** — поддерживаемый вторичный сценарий (тот же core flow, без desktop-only mechanics), в соответствии с product foundation §4.
- **Installable PWA:** приложение installable; есть Web App Manifest и service worker (инженерные проверки — `docs/foundation/02_technical_foundation.md`, в т.ч. матрица валидации браузеров).
- **Manifest — отображаемые имена:** поле `name` (полное имя при установке) — **`Pocket Raid Tavern`**; `short_name` — **`PRT`**. Визуальное направление иконки и отделение prototype/final assets — `docs/product/LORE_v0.1.md` и Assets Policy в product foundation §11.
- **Manifest — цвета темы:** `theme_color` и `background_color` фиксируются в задаче на реализацию manifest (вехи M3), если отдельное продуктовое значение не задано ранее; в PRD hex-значения не задаются без явного owner decision.
- **Offline shell:** shell открывается без сети и **не обещает** offline gameplay (product foundation §8, §10).
- **Нет offline gameplay queue:** действия, требующие API/backend, при отсутствии сети или недоступности API показывают **понятный blocked state**, а не очередь офлайн-действий и не подменяют server-authoritative outcome.

Вне scope v1 (не путать с требованиями PWA shell): Telegram Mini App, нативные iOS/Android клиенты, Capacitor/wrapper, Steam/desktop wrapper — product foundation §4.

### 6.2. Tavern

- Таверна является главным экраном.
- Видны: главный raid CTA, текущий проект таверны, награды/вклад, последние события или краткая хроника.
- Игрок понимает, что его действия меняют общий прогресс.

### 6.3. Raid setup

- Игрок может начать доступный raid flow.
- Игрок видит роль/loadout на уровне, достаточном для первого боя.
- Игра не требует идеального состава партии для первого опыта.
- Live party/lobby state обновляется без ручного refresh.

### 6.4. Combat

- Бой отображается как 2D party-view arena.
- Combat canvas реализован на PixiJS.
- HUD, skill controls, emoji и быстрые фразы реализованы в React.
- Локальный персонаж закреплён в центре нижней части canvas.
- Party order фиксирован для всех игроков.
- Мобы/босс находятся в дальней части арены.
- Игрок выбирает цель тапом.
- Навыки имеют понятные valid/invalid targets.
- Backend валидирует действие и рассчитывает результат.
- UI показывает результат навыка, cooldown/state и изменения HP/effects.
- Live-обновления боя приходят через WebSocket server push.
- PixiJS не содержит правил боя и не считает authoritative outcome.

### 6.5. Live communication in combat

- В бою нет свободного текстового чата.
- Raid lead может отправлять заранее заданные команды.
- Игроки могут отправлять emoji и быстрые фразы.
- RL-команда с целью визуально подсвечивает target на арене.
- Коммуникация проходит через WebSocket и отображается без ручного refresh.

### 6.6. Rewards and progress

- Backend выдаёт награды.
- Игрок видит награду после raid outcome.
- Игрок видит вклад в таверну или персональный прогресс.
- Повторный запрос не должен дублировать reward.

### 6.7. Share/invite

- Игрок может поделиться результатом или ссылкой.
- Share не зависит от Telegram-specific mechanics.
- Ссылка/карточка должна вести в понятный контекст.

### 6.8. Analytics

Минимальные события:

- app_opened;
- offline_shell_opened;
- tutorial_started;
- tutorial_completed;
- raid_started;
- skill_target_selected;
- skill_cast_requested;
- skill_cast_resolved;
- raid_lead_command_sent;
- quick_phrase_sent;
- emoji_sent;
- raid_completed;
- raid_failed;
- reward_claimed;
- tavern_contribution_made;
- invite_created;
- invite_opened;
- share_card_created.

## 7. Non-functional requirements

- Основной UX — mobile-first.
- Нет hover-only controls.
- Нет desktop-only mechanics.
- Нет key layout shift в бою, наградах и таверне.
- Backend является source of truth для игрового состояния.
- REST API contracts генерируются из backend OpenAPI schema.
- WebSocket protocol schemas документируются отдельно.
- Local dev запускается через Docker Compose.
- Generated/prototype assets отделены от final assets.

## 8. Public early access acceptance criteria

v1 можно считать готовой к публичному early access, если:

- [ ] Новый игрок может открыть PWA на iOS Safari и Android Chrome.
- [ ] Offline shell открывается без сети и не обещает gameplay.
- [ ] Игрок может пройти первый end-to-end raid loop.
- [ ] Игрок может выбрать цель тапом и применить навык.
- [ ] Combat canvas работает через PixiJS без переноса combat rules на клиент.
- [ ] Изменения battle state пушатся backend → client через WebSocket.
- [ ] RL-команды, emoji и быстрые фразы работают без свободного чата.
- [ ] Невалидная цель объясняется UI, а не ломает flow.
- [ ] Backend валидирует combat action и rewards.
- [ ] Reward нельзя получить повтором одного и того же запроса.
- [ ] Видно, как результат рейда влияет на таверну или прогресс.
- [ ] Есть базовый share/invite result.
- [ ] Есть минимальная аналитика core funnel.
- [ ] Есть smoke-набор Playwright для ключевого flow.
- [ ] Backend tests покрывают reward/combat validation для ключевого сценария.
- [ ] README и foundation docs актуальны.

## 9. Release gates

### Product gate

- Первый цикл понятен без объяснения разработчика.
- Игрок понимает, что делать после первого рейда.
- Игрок понимает, зачем возвращаться.
- Игрок понимает, как координироваться без чата.

### Technical gate

- Docker Compose поднимает проект.
- Backend tests проходят.
- Frontend typecheck/tests проходят.
- OpenAPI client актуален.
- WebSocket protocol для combat/lobby задокументирован и покрывает snapshot/event/command/error flow.
- Миграции применяются на чистую БД.

### UX/PWA gate

- Проверены iOS Safari и Android Chrome.
- Проверены small viewport и browser chrome.
- Нет hover-only обязательных действий.
- Offline shell работает предсказуемо.

## 10. Решения, которые должны быть закрыты до реализации полного combat slice

Уже принято:

- Renderer для 2D combat canvas: PixiJS + React HUD.
- Transport/realtime модель боя: WebSocket для live lobby/combat, REST/OpenAPI для обычного API.

Осталось закрыть:

- Минимальный набор ролей и навыков v1.
- Минимальный набор врагов/боссов v1.
- Минимальный WebSocket protocol contract для battle/lobby events.
