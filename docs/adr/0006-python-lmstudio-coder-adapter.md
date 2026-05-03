# 0006 — Исполнитель кодинга: Python-адаптер к LM Studio (OpenAI API) вместо Codex CLI

- **Статус:** Accepted
- **Дата:** 2026-05-03
- **Авторы:** @enotbert
- **Связано с:** [ADR-0005](0005-codex-cli-local-runtime.md) (supersedes), [PTR-6](https://linear.app/ptr-game/issue/PTR-6/), [PTR-7](https://linear.app/ptr-game/issue/PTR-7/) (реализация кода), [`AGENTS.md`](../../AGENTS.md), [`.ai/rules/60-agent-roles.md`](../../.ai/rules/60-agent-roles.md), [`.ai/rules/70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md) (будет переписан под новый адаптер)

## Контекст

В [`.ai/rules/60-agent-roles.md`](../../.ai/rules/60-agent-roles.md) зафиксировано: **Cursor** — оркестратор, **Codex CLI `--oss`** — исполнитель кодинговых задач по handoff'у. [ADR-0005](0005-codex-cli-local-runtime.md) закрепил транспорт: **LM Studio** на `localhost:1234`, модель по умолчанию через `CODEX_HOST` / `CODEX_MODEL`.

Первая реальная попытка делегирования ([PTR-6](https://linear.app/ptr-game/issue/PTR-6/)) показала блокер: **Codex CLI 0.128** при работе через LM Studio отправляет в API массив `tools`, часть которых имеет типы/схемы, которые **LM Studio local server** отвергает на этапе валидации запроса (`invalid_request_error`, `param: tools.<N>.type`, `code: invalid_string`). Это **известная несовместимость** (см. [lmstudio-bug-tracker#1812](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1812)); частичные workarounds (отключение MCP, плагинов, фич в профиле) **не устраняют** проблему полностью — остаётся набор «жёстких» встроенных tools Codex CLI, которые нельзя отключить конфигурацией. Смена модели не помогает: отказ происходит **до** вызова модели.

При этом:

- **LM Studio** как локальный OpenAI-совместимый endpoint и **local-first** политика остаются желательными.
- Формат **handoff** (`.ai/handoffs/PTR-*.md`) и валидатор `scripts/validate-handoff.sh` уже введены и **не зависят** от Codex CLI — их нужно сохранить как контракт между Cursor и исполнителем.
- Нужен исполнитель, который умеет **агентно** менять файлы в рабочем дереве под контролем оркестратора, но **не ломает** LM Studio своим proprietary tool payload'ом.

## Рассмотренные варианты

- **Вариант A: Оставить Codex CLI и ждать фикса LM Studio / Codex.** Минусы: нет контроля над сроками; блокирует автономный цикл «Cursor → coder → PR». Плюсы: нулевая разработка. **Отклонён** как основной путь на текущей фазе.

- **Вариант B: Перейти на Ollama как backend для Codex CLI.** В сообществе встречаются отчёты, что связка работает стабильнее. Минусы: смена стека у разработчика, дублирование управления моделями, не снимает риск снова упереться в tool-schema при эволюции Codex CLI. **Откладываем** как возможный эксперимент; не заменяет потребность в **собственном** тонком контроле над tools.

- **Вариант C: Тонкий HTTP-клиент без агентности (curl / один запрос `chat.completions`).** Плюсы: минимум кода. Минусы: нет цикла tool → исполнение → повтор; оркестратор вынужден вручную парсить ответы и применять патчи. **Не подходит** как замена «coder» роли.

- **Вариант D: Собственный **Python**-адаптер к LM Studio — агентный цикл `chat.completions` + только те `tools`, которые мы сами описали в JSON Schema в совместимом с LM Studio подмножестве (`type: function`).** Плюсы: полный контроль над payload'ом, local-first сохраняется, один язык для будущего расширения (тесты, логирование, политики песочницы). Минусы: поддержка и развитие своего кода. **Выбран.**

## Решение

### Роль в архитектуре агентов

- **Cursor** остаётся оркестратором: планирование, handoff, независимая валидация, PR.
- **Codex CLI** **снимается** с роли исполнителя кодинга в этом репозитории (см. supersession [ADR-0005](0005-codex-cli-local-runtime.md)).
- **Python-адаптер** (`ptr_coder` — рабочее имя пакета) становится **исполнителем кодинга**: читает handoff (или инструкции от Cursor), ведёт **агентный** цикл запросов к LM Studio, вызывает **только разрешённые** tools, вносит изменения в файлы в пределах политики workspace.

### Транспорт и endpoint

- **Сервер:** LM Studio, Local Server, OpenAI-совместимый API (как и в ADR-0005).
- **Базовый URL для HTTP-клиента:** по умолчанию `http://localhost:1234/v1` (явный суффикс `/v1` — контракт для клиентов в духе OpenAI SDK; если реализация использует официальный `openai` Python SDK, `base_url` указывает именно так).

### Контракт переменных окружения (без хардкода в PR)

Идентификаторы **не** используют префикс `CODEX_*`, чтобы не путать с устаревшим Codex CLI.

| Переменная | Назначение | Дефолт (если не задана) |
|------------|------------|-------------------------|
| `PTR_CODER_BASE_URL` | Базовый URL OpenAI-совместимого API (LM Studio) | `http://localhost:1234/v1` |
| `PTR_CODER_MODEL` | Идентификатор модели в LM Studio | `gemma-4-26b-a4b-it` |

Разработчик может задать значения в **локальном** `.env` / `.env.local` (не коммитится) или в shell-профиле — **смена модели не требует PR** в репозиторий.

### Размещение кода в монорепе

- Каталог реализации: **`packages/ptr_coder/`** (Python package, импорт `ptr_coder`).
- Точка входа CLI (для вызова из Cursor / CI / руками): **`python -m ptr_coder`** или скрипт-обёртка, зафиксированная в README пакета после реализации.

### Агентность (v1 и эволюция)

- **v1:** цикл «модель вернула `tool_calls` → адаптер исполняет разрешённый tool → результат в следующем сообщении `role: tool` → снова запрос к модели» до лимита итераций или явного стоп-сигнала от модели.
- **Tools v1 (минимальный набор, совместимый с LM Studio):** только JSON Schema с `type: function` (без `namespace`, без web_search и прочих типов Codex). Конкретный список функций фиксируется в коде первого PR (ожидаемо: чтение файла, запись файла, листинг каталога; **без** произвольного shell по умолчанию — shell при необходимости отдельным флагом политики в последующих итерациях).
- **Границы workspace:** все пути относительно корня репозитория (или явно переданного `--root`); выход за пределы — ошибка.

### Связь с handoff-протоколом

- Вход адаптера: путь к markdown handoff'у, прошедшему `scripts/validate-handoff.sh`, **или** эквивалентный inline-набор секций (деталь CLI — в коде/README пакета).
- Адаптер **не** правит `.ai/handoffs/*.md` в части `## Result` — это остаётся за Cursor после прогона (как с Codex).

### Supersedes

- [ADR-0005](0005-codex-cli-local-runtime.md) **больше не определяет** runtime исполнителя кодинга. Полезные части ADR-0005 (LM Studio, local-first, порт) остаются **интуитивным контекстом**; команды `codex --oss` из ADR-0005 считаются **устаревшими** для роли coder в этом репозитории.

## Последствия

### Положительные

- Воспроизводимый локальный coder без зависимости от несовместимого tool-stack стороннего CLI.
- Контролируемая поверхность attack / surprise: только явно реализованные tools.
- Env-контракт `PTR_CODER_*` — смена модели и URL без коммитов.

### Отрицательные / компромиссы

- **Собственная поддержка:** баги, совместимость с новыми версиями LM Studio — на команде репозитория.
- **Нет готового «всё из коробки» UX** Codex CLI (TUI, сессии) — проще, но меньше «магии».
- **CI GitHub Actions** по-прежнему не сможет дергать LM Studio на hosted runner без self-hosted / mock — это не регрессия, а то же ограничение, что и у ADR-0005.

### Что нужно сделать (follow-up, вне этого ADR-текста)

- [x] Реализовать пакет `packages/ptr_coder/` (зависимости, тесты; lockfile не вводим на первом шаге).
- [ ] Переписать [`.ai/rules/70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md) под вызов Python-адаптера (возможно переименование файла — отдельное обсуждение).
- [ ] Обновить / переименовать [`.cursor/skills/invoke-codex/SKILL.md`](../../.cursor/skills/invoke-codex/SKILL.md) → процесс `invoke-coder` (или аналог).
- [ ] Обновить [`.ai/rules/60-agent-roles.md`](../../.ai/rules/60-agent-roles.md): убрать Codex CLI как coder, описать адаптер.
- [x] Добавить `.env.example` корневые ключи `PTR_CODER_BASE_URL` / `PTR_CODER_MODEL` (без секретов).
- [ ] Обновить `AGENTS.md` §6 таблицу ADR и §9 «Принятые решения» (строка про Codex CLI → адаптер).

## Ссылки

- [LM Studio — Local Server](https://lmstudio.ai/docs/local-server)
- [lmstudio-bug-tracker#1812 — Codex + LM Studio `tools.N.type invalid_string`](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1812)
- [OpenAI API — Chat completions](https://platform.openai.com/docs/api-reference/chat/create) (контракт, который эмулирует LM Studio)
- ADR-0001 (MADR), ADR-0005 (исторический runtime Codex CLI + LM Studio)
- PR [#6](https://github.com/enotbert/PTR_v2/pull/6) — handoff validator + фиксация причины pivot'а в `## Result`
