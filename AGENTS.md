# AGENTS.md — индекс правил для AI-ассистентов

> Этот файл — **точка входа** и **манифест** для всех AI-ассистентов, работающих в этом репозитории.
> Перед началом любой задачи ассистент обязан прочитать этот файл и все правила, на которые он ссылается, релевантные для задачи.
> Поддерживаемые ассистенты: Cursor, Codex CLI (`--oss` и cloud), Claude Code, GitHub Copilot и любые другие, читающие `AGENTS.md`.

---

## 1. О проекте

PTR v2 — мультиязыковая монорепа, спроектированная под **автономную AI-разработку**. Большая часть кода пишется AI-агентами; человек выполняет роль владельца продукта и финального ревьюера.

- Репозиторий: <https://github.com/enotbert/PTR_v2>
- Трекер задач: **Linear**, префикс команды — `PTR`
- Стратегия веток: **trunk-based**, единственная долгоживущая ветка — `main`
- Стратегия merge: **squash-merge** (PR → один коммит в `main`)

## 2. Языковая политика

| Артефакт | Язык |
|---|---|
| Документация (`AGENTS.md`, `.ai/rules/`, ADR, README) | Русский |
| Описания PR, обсуждения, комментарии в Linear | Русский |
| Код, имена файлов и каталогов | Английский |
| Имена веток | Английский |
| Сообщения коммитов и заголовки PR | Английский |
| Технические комментарии в коде | Английский |

## 3. Роли агентов

| Роль | Инструмент | Ответственность |
|---|---|---|
| Оркестратор / архитектор / валидатор | **Cursor** | Декомпозиция задач, проектирование, написание ADR и спецификаций, делегирование Codex CLI, валидация результатов, оформление PR |
| Кодер | **Codex CLI `--oss`** | Реализация кода по спецификации от Cursor, локальный прогон тестов и линтеров |
| Генератор изображений | **Codex CLI cloud** | Генерация графических ассетов |
| Финальный ревьюер | **Человек (`@enotbert`)** | Code review и merge PR |

Подробности взаимодействия — в [`.ai/rules/60-agent-roles.md`](.ai/rules/60-agent-roles.md) и [`.ai/rules/70-orchestration-codex-cli.md`](.ai/rules/70-orchestration-codex-cli.md).

## 4. Минимальный цикл работы агента

1. Получить задачу из Linear (`PTR-XXX`), перевести её в статус **In Progress**.
2. Прочитать `AGENTS.md` и релевантные `.ai/rules/*.md`.
3. Спланировать изменения (декомпозиция, файлы в скоупе, критерии приёмки).
4. Создать ветку `PTR-XXX-<kebab-slug>` от свежего `main`.
5. Реализовать изменения; на каждом значимом шаге — коммит в стиле Conventional Commits.
6. Прогнать локально: линтер → форматер → типы → тесты (для UI — Playwright/E2E).
7. Запушить ветку, открыть PR с заголовком `<type>(<scope>): PTR-XXX <description>`.
8. Перевести задачу в **In Review**, оставить ссылку на PR в Linear.
9. **Дождаться ревью человека.** Агент **не мерджит PR самостоятельно**.

Полная версия — в [`.ai/rules/10-workflow.md`](.ai/rules/10-workflow.md).

## 5. Индекс правил

Файлы в `.ai/rules/` пронумерованы для предсказуемого порядка чтения. Все они обязательны к прочтению на старте проекта; для конкретной задачи — релевантные.

| Файл | О чём |
|---|---|
| [`.ai/rules/00-overview.md`](.ai/rules/00-overview.md) | Принципы, термины, навигация по правилам |
| [`.ai/rules/10-workflow.md`](.ai/rules/10-workflow.md) | Полный цикл работы: от задачи до merge |
| [`.ai/rules/11-work-types.md`](.ai/rules/11-work-types.md) | Вариации цикла по типам задач: feature / bugfix / refactor / docs / infra |
| [`.ai/rules/20-git-and-branching.md`](.ai/rules/20-git-and-branching.md) | Trunk-based, имена веток, что запрещено в git |
| [`.ai/rules/30-commits-and-prs.md`](.ai/rules/30-commits-and-prs.md) | Conventional Commits, формат PR, размер PR |
| [`.ai/rules/40-code-quality.md`](.ai/rules/40-code-quality.md) | Линт, формат, типы, тесты, Playwright для UI, Definition of Done |
| [`.ai/rules/50-task-management.md`](.ai/rules/50-task-management.md) | Linear как единственный источник истины, статусы, создание задач |
| [`.ai/rules/60-agent-roles.md`](.ai/rules/60-agent-roles.md) | Кто что делает: Cursor, Codex CLI, человек |
| [`.ai/rules/65-personas.md`](.ai/rules/65-personas.md) | Персоны делегирования (backend / frontend / qa / infra / docs) и шаблоны брифов |
| [`.ai/rules/70-orchestration-codex-cli.md`](.ai/rules/70-orchestration-codex-cli.md) | Как Cursor вызывает Codex CLI как subprocess |
| [`.ai/rules/80-security-and-secrets.md`](.ai/rules/80-security-and-secrets.md) | Политика секретов, `.env`, доступ агентов к чувствительным данным |
| [`.ai/rules/90-forbidden.md`](.ai/rules/90-forbidden.md) | Чёрный список действий, всегда требующих явного разрешения человека |

## 5a. Скилы (`.cursor/skills/`)

Скилы — операционные «как это делать» инструкции, выполняющие конкретные шаги процесса. В отличие от правил `.ai/rules/`, которые описывают **что** и **зачем**, скилы описывают **как именно** агент выполняет конкретную операцию. Хранятся в `.cursor/skills/` (версионируются, видны всем).

| Скил | О чём |
|---|---|
| [`.cursor/skills/invoke-codex/SKILL.md`](.cursor/skills/invoke-codex/SKILL.md) | Один цикл вызова Codex CLI как subprocess по существующему хэндоффу: pre-flight → запуск → захват результата → независимая валидация → решение об итерации |
| [`.cursor/skills/linear-flow/SKILL.md`](.cursor/skills/linear-flow/SKILL.md) | Жизненный цикл задачи в Linear (PTR): pickup, статус-переходы, комментарии, follow-up задачи, обработка неоднозначности |

**Правила добавления скилов:**

- Только в `.cursor/skills/` (не в `~/.cursor/skills/` — это персональное).
- Формат — Cursor SKILL.md с YAML frontmatter (`name`, `description`).
- `name` — kebab-case, `description` — третье лицо, явные триггеры.
- SKILL.md не длиннее ~500 строк; детали — в дополнительных файлах рядом.
- Любой новый скил, оркеструющий процесс, ссылается на соответствующие правила в `.ai/rules/` (а не дублирует их).

## 6. Архитектурные решения (ADR)

Архитектурные и процессные решения фиксируются в формате [MADR](https://adr.github.io/madr/) в каталоге [`docs/adr/`](docs/adr/).

- Шаблон: [`docs/adr/template.md`](docs/adr/template.md)
- Индекс ADR: [`docs/adr/README.md`](docs/adr/README.md)

| № | Заголовок | Статус |
|---|---|---|
| [0001](docs/adr/0001-record-architecture-decisions.md) | Использовать MADR для записи архитектурных решений | Accepted |
| [0002](docs/adr/0002-use-release-please-for-versioning.md) | Использовать release-please для CHANGELOG и версионирования | Accepted |
| [0003](docs/adr/0003-license-proprietary.md) | Использовать проприетарную лицензию (All Rights Reserved) | Accepted |
| [0004](docs/adr/0004-relax-required-review.md) | Снять обязательный approving review в branch protection (solo-dev) | Accepted |
| [0005](docs/adr/0005-codex-cli-local-runtime.md) | Codex CLI runtime: LM Studio @ localhost + Qwen3-Coder | Accepted |

## 7. Definition of Done (краткая версия)

PR может быть смерджен **только если**:

- [ ] Заголовок PR соответствует формату `<type>(<scope>): PTR-XXX <description>`
- [ ] Линтер и форматер проходят без ошибок
- [ ] Проверка типов (где применимо) проходит
- [ ] Тесты добавлены/обновлены и зелёные локально
- [ ] **Для PR, затрагивающих UI — добавлен/обновлён Playwright (или эквивалент) тест, подтверждающий поведение в браузере**
- [ ] CI зелёный
- [ ] Документация обновлена при необходимости (README, ADR, `.ai/rules/`)
- [ ] PR смерджен **человеком** (`@enotbert`); approving review **рекомендован** для нетривиальных PR (`feat`, `fix`, `infra`), но не enforced branch protection — см. [ADR-0004](docs/adr/0004-relax-required-review.md). Агент **никогда не мерджит свой PR** ([`.ai/rules/90-forbidden.md`](.ai/rules/90-forbidden.md)).

Развёрнутая версия — в [`.ai/rules/40-code-quality.md`](.ai/rules/40-code-quality.md).

## 8. Что агент НЕ делает без явного разрешения

Краткий список (полный — в [`.ai/rules/90-forbidden.md`](.ai/rules/90-forbidden.md)):

- Прямой push в `main`, merge собственного PR
- `force-push`, удаление веток на `origin`, переписывание истории
- Изменение `.github/`, CI workflows, branch protection, `CODEOWNERS`
- Изменение `.ai/rules/`, `AGENTS.md`, существующих ADR
- Изменение зависимостей и lockfiles (`package.json`, `pyproject.toml`, `go.mod` и т.п.)
- Изменение миграций БД
- Публикация пакетов, создание GitHub Releases, тегов
- Чтение или вывод содержимого файлов с секретами (`.env`, `*.key`, `credentials.*`)
- Деструктивные shell-команды за пределами рабочего дерева репозитория
- Обход CI-гейтов (`--no-verify`, force-merge)

## 9. Открытые вопросы

На данный момент **процессных открытых вопросов нет** — все основные решения зафиксированы либо в ADR (см. [§6](#6-архитектурные-решения-adr)), либо в правилах `.ai/rules/`. Любой новый вопрос фиксируется здесь и закрывается через ADR / правки в `.ai/rules/`.

Мелкие операционные детали, которые разрешатся по факту первой реальной работы (не требуют ADR):

- **Способ подачи handoff'а в Codex CLI** (`--instructions <file>` vs stdin vs иное) — определится на первой делегации; обновим [`.ai/rules/70-orchestration-codex-cli.md`](.ai/rules/70-orchestration-codex-cli.md) и `invoke-codex` skill маленьким docs-PR.

### Принятые решения (для справки)

| Тема | Решение | Где зафиксировано |
|---|---|---|
| Секреты в репо | Только `.env.example`; полагаемся на GitHub Secret Scanning + Push Protection; `gitleaks` отложен до появления внешних интеграций | [`.ai/rules/80-security-and-secrets.md`](.ai/rules/80-security-and-secrets.md) |
| CHANGELOG и релизы | release-please (manifest mode, `release-type: simple` на корне, расширяется по пакетам) | [ADR-0002](docs/adr/0002-use-release-please-for-versioning.md) |
| Лицензия | Proprietary / All Rights Reserved, явный `LICENSE` | [ADR-0003](docs/adr/0003-license-proprietary.md), [`LICENSE`](LICENSE) |
| Status checks в branch protection | Один зонтичный `ci`; разбиение появится с первым реальным стеком | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| Approving review на PR | Не enforced branch protection (`required_approving_review_count: 0`); merge — обязательно человеком, agent self-merge запрещён правилом | [ADR-0004](docs/adr/0004-relax-required-review.md), [`.ai/rules/90-forbidden.md`](.ai/rules/90-forbidden.md) |
| Codex CLI runtime / модель | LM Studio @ `localhost:1234`, `qwen3-coder-30b-a3b-instruct`, env-контракт `CODEX_HOST` / `CODEX_MODEL` с дефолтами | [ADR-0005](docs/adr/0005-codex-cli-local-runtime.md), [`.ai/rules/70-orchestration-codex-cli.md`](.ai/rules/70-orchestration-codex-cli.md) |
| Локальные git-хуки | Husky+lint-staged+commitlint отложены до первого JS/TS пакета в монорепе | [`.ai/rules/40-code-quality.md`](.ai/rules/40-code-quality.md) |

## 10. Как обновлять эти правила

Правила в `AGENTS.md` и `.ai/rules/` — критическая инфраструктура процесса. **Агент не меняет их без явного запроса пользователя**. Любое изменение проходит обычным PR с особым вниманием в ревью; крупные изменения сопровождаются ADR.
