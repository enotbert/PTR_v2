# 30 — Коммиты и Pull Requests

## Конвенция коммитов

Используется [Conventional Commits](https://www.conventionalcommits.org/) с **обязательным `scope`**.

### Формат

```
<type>(<scope>): <subject>

<body — опционально>

<footer — опционально>
```

### Типы

| Тип | Когда использовать |
|---|---|
| `feat` | Новая функциональность |
| `fix` | Исправление бага |
| `docs` | Только документация (включая `AGENTS.md`, `.ai/rules/`, ADR) |
| `style` | Форматирование, не влияющее на логику |
| `refactor` | Рефакторинг без изменения поведения |
| `perf` | Оптимизация производительности |
| `test` | Добавление/правка тестов |
| `build` | Сборка, зависимости, инструменты сборки |
| `ci` | GitHub Actions и прочая CI-инфра |
| `chore` | Прочее: housekeeping, конфиги, не подходящее под остальные типы |
| `revert` | Откат коммита |

### Scope

Обязателен. Отражает область изменения. На старте монорепы — имя приложения/пакета/сервиса. До появления формальной структуры `apps/`/`packages/`:

- `repo` — изменения корневой инфраструктуры репозитория
- `ci` — изменения в `.github/workflows/`
- `docs` — изменения в документации (`README`, `AGENTS.md`, `.ai/rules/`, `docs/adr/`)
- `meta` — изменения в `.gitignore`, `.editorconfig`, `CODEOWNERS`, прочих мета-файлах

С появлением структуры монорепы scope меняется на конкретное имя пакета (`web`, `api`, `worker`, …).

### Subject

- Императив, настоящее время: `add`, `fix`, `update`, **не** `added`/`adds`.
- Без точки в конце.
- Без капитализации первой буквы.
- ≤ 72 символов.

### Примеры

Хорошо:

- `feat(api): add user auth endpoint`
- `fix(web): correct login redirect on Safari`
- `docs(repo): describe agent orchestration model`
- `chore(meta): widen gitignore for Node and Go`
- `ci(repo): require lint and test in branch protection`

Плохо:

- `Update stuff` — нет типа, нет scope
- `feat: add auth` — нет scope
- `feat(api): Added user auth.` — прошедшее время, точка, капитализация
- `feat(api): add user authentication system with full RBAC and audit logging` — длиннее 72

### Body и Footer

Body — *что* и *зачем* (а не *как* — это видно в diff). Перенос строки ≤ 100 символов.

Footer — связи и breaking changes:

- `Refs: PTR-123` — упоминание задачи (не закрывает её)
- `BREAKING CHANGE: <описание>` — в теле или footer

> **Связку с Linear на уровне коммитов делать необязательно** — она уже есть в имени ветки и заголовке PR. Достаточно `Refs:` для дополнительных задач, если коммит затрагивает их.

## Pull Requests

### Заголовок PR

```
<type>(<scope>): PTR-XXX <description>
```

Примеры:

- `feat(api): PTR-123 add user auth endpoint`
- `fix(web): PTR-456 correct login redirect on Safari`
- `docs(repo): PTR-789 describe agent orchestration model`

> При squash-merge заголовок PR становится сообщением коммита в `main`. Поэтому он должен соответствовать **тем же требованиям**, что и обычный CC-коммит, плюс содержать `PTR-XXX`.

#### Исключение: автогенерируемые release-PR

Release-PR, создаваемые автоматически workflow `release-please` (см. [ADR-0002](../../docs/adr/0002-use-release-please-for-versioning.md)), **освобождаются от требования содержать `PTR-XXX`**. Их заголовок имеет фиксированный формат:

```
chore(repo): release <version>
```

Это валидный CC-коммит (тип `chore`, scope `repo`); привязка к Linear-задаче не требуется, потому что release-PR агрегирует все ранее смерджанные изменения.

### Тело PR

Заполняется по [`pull_request_template.md`](../../.github/pull_request_template.md). Обязательные секции:

- **Что меняется** — суть изменений (1–3 абзаца).
- **Зачем** — связь с задачей и бизнес/техническая причина.
- **Как тестировал** — что прогонял локально, какие сценарии проверял.
- **Связанная задача** — `Closes PTR-XXX` (если PR полностью закрывает задачу) или `Refs PTR-XXX`.
- **Чек-лист DoD** — обязательно проставить галочки или явно отметить «не применимо».

### Размер PR

- **Цель:** ≤ 400 строк изменений (без учёта lockfiles и автогенерации).
- При превышении — обоснование в теле PR (почему дробление невозможно/нецелесообразно).
- Generated файлы (`*.lock`, миграции, snapshots) указываются в теле PR с пометкой «автогенерация».

### Метки

Опционально, на момент написания меток нет; будут добавлены через ADR при необходимости (`ai-generated`, `infra`, `docs-only`, `breaking`, …).

### Draft vs Ready

- Открывай PR как **Draft**, если работа ещё не завершена, но нужен ранний отклик или CI-проверка.
- Перевод в **Ready for review** — только после прохождения локального DoD.

### Что делает агент vs человек

| Действие | Агент | Человек |
|---|---|---|
| Открыть PR | ✅ | — |
| Обновлять PR (push в feature) | ✅ | — |
| Отвечать на комментарии | ✅ | ✅ |
| Менять статус Draft ↔ Ready | ✅ | ✅ |
| Approve / Request changes | ❌ | ✅ |
| Merge | ❌ | ✅ |
| Закрыть PR без merge | ⚠️ только с явного запроса | ✅ |
