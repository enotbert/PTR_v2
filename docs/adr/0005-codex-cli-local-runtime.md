# 0005 — Codex CLI runtime: LM Studio @ localhost + Qwen3-Coder

- **Статус:** Accepted
- **Дата:** 2026-05-03
- **Авторы:** @enotbert
- **Связано с:** [`AGENTS.md`](../../AGENTS.md), [`.ai/rules/60-agent-roles.md`](../../.ai/rules/60-agent-roles.md), [`.ai/rules/70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md), [`.cursor/skills/invoke-codex/SKILL.md`](../../.cursor/skills/invoke-codex/SKILL.md)

## Контекст

[`60-agent-roles.md`](../../.ai/rules/60-agent-roles.md) фиксирует Codex CLI в режиме `--oss` как **исполнителя кодинговых задач** (coder). Режим `--oss` подразумевает подключение к **OpenAI-совместимому endpoint'у** — никаких вшитых ключей или менеджмент-плоскости OpenAI на этом пути нет, нужен внешний сервер с моделью.

До этого ADR в [`70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md) и [`invoke-codex` skill](../../.cursor/skills/invoke-codex/SKILL.md) шаблон вызова стоял как `<placeholder>`. Это было единственным открытым пунктом в `AGENTS.md` §9 и блокировало возможность выполнить хотя бы одну реальную итерацию делегирования из Cursor → Codex CLI.

Нужно зафиксировать:

1. **Какой локальный/удалённый сервер** обслуживает endpoint.
2. **Какую модель** использовать по умолчанию.
3. **Контракт переменных окружения**, чтобы команда вызова была воспроизводимой и не вшитой в одно место.

## Рассмотренные варианты

- **Вариант A: LM Studio @ `localhost:1234` + Qwen3-Coder-30B-A3B-Instruct.** ✅ выбран. Установлено и работает у разработчика; полностью локально (приватность, отсутствие платы, отсутствие зависимости от облака); UI для swap'а моделей; OpenAI-совместимый сервер из коробки на дефолтном порту 1234.
- **Вариант B: Облачный Codex (managed OpenAI / Anthropic API).** Минусы: платно, передаём код за пределы машины (политика проекта на текущей фазе — local-first), требует ротации API-ключей, ещё один секрет в окружении. Плюсы: модели сильнее, не нужно держать GPU. Откладываем; если появится боттлнек по качеству локальной модели — отдельный ADR.
- **Вариант C: Ollama @ `localhost:11434`.** Альтернативный локальный стек, OpenAI-совместимый endpoint через `/v1/`. Минусы: другой workflow управления моделями, у разработчика уже выбран LM Studio. Не отказываемся принципиально — если когда-то перейдём, будет новый ADR с `Supersedes ADR-0005`.
- **Вариант D: llama.cpp напрямую (`./server`).** Минусы: больше ручной возни (запуск, флаги, шаблоны промптов), нет UI; OpenAI-совместимость частичная. Не оправдано на текущей фазе.

## Решение

### Runtime

- **Сервер:** [LM Studio](https://lmstudio.ai/) с включённым **Local Server** (вкладка Developer / Local Server).
- **Endpoint по умолчанию:** `http://localhost:1234` (дефолтный порт LM Studio).
- **Модель по умолчанию:** `qwen3-coder-30b-a3b-instruct` (Qwen 3 Coder 30B, MoE A3B, instruct-вариант).

### Env-контракт

Команда вызова **не хардкодит** хост и модель — обе значения параметризованы переменными окружения с дефолтами:

| Переменная   | Назначение                                                | Дефолт                          |
|--------------|-----------------------------------------------------------|---------------------------------|
| `CODEX_HOST` | OpenAI-совместимый endpoint, к которому стучится Codex CLI | `http://localhost:1234`         |
| `CODEX_MODEL`| Идентификатор модели, загруженной в `CODEX_HOST`          | `qwen3-coder-30b-a3b-instruct`  |

Канонический вызов (POSIX shell):

```bash
codex --oss \
  --model "${CODEX_MODEL:-qwen3-coder-30b-a3b-instruct}" \
  --host "${CODEX_HOST:-http://localhost:1234}"
```

PowerShell (т. к. dev-машина — Windows):

```powershell
$model     = if ($env:CODEX_MODEL) { $env:CODEX_MODEL } else { "qwen3-coder-30b-a3b-instruct" }
$codexHost = if ($env:CODEX_HOST)  { $env:CODEX_HOST }  else { "http://localhost:1234" }
codex --oss --model $model --host $codexHost
```

### Prerequisites (всегда проверять перед запуском)

1. LM Studio запущен.
2. Local Server включён в LM Studio.
3. Модель `qwen3-coder-30b-a3b-instruct` (или значение `CODEX_MODEL`) **загружена в память** (не просто скачана).
4. `curl http://localhost:1234/v1/models` отвечает 200 и в списке есть нужная модель.

### Что НЕ зафиксировано этим ADR

- **Способ передачи handoff'а Codex CLI** (`--instructions <file>`, stdin-redirect, иной флаг). Это операционная деталь, разрешится на первом реальном делегировании, отдельного ADR не требует — обновим [`70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md) и `invoke-codex` skill по факту.
- **Альтернативные модели** для конкретных классов задач (например, более тяжёлая модель для архитектурных задач). Сейчас одна модель на всё; смена → новый ADR.

## Последствия

### Положительные

- Закрывается последний открытый процессный вопрос из `AGENTS.md` §9 — `invoke-codex` skill становится исполнимым без вопросов к человеку (при условии работающего LM Studio).
- Local-first: код не покидает машину, нет платы за токены, нет внешнего токена в ротации.
- Env-контракт даёт точку расширения: можно переключиться на другой хост/модель (например, Ollama, или mock-сервер в CI) без правок документации и кода — только переменные окружения.

### Отрицательные / компромиссы

- **Жёсткая зависимость от LM Studio как процесса**: если LM Studio не запущен или модель не загружена — Codex CLI упадёт с network/timeout-ошибкой. Pre-flight в `invoke-codex` skill должен ловить это **до** вызова.
- **Ресурсы машины**: Qwen3-Coder-30B-A3B в актуальных квантизациях (Q4_K_M / MXFP4) занимает порядка 16–20 ГБ VRAM/RAM. На слабых машинах модель не загрузится — нужно будет переключаться на более лёгкую через `CODEX_MODEL`.
- **Single-machine setup**: автоматизация в CI (GitHub Actions) не сможет вызывать Codex CLI «из коробки» — там нет LM Studio. Если когда-то понадобится агентский CI — отдельный ADR (managed cloud, или self-hosted runner с моделью, или mock).
- **Привязка к UI-тулу**: LM Studio — закрытый продукт. Если он исчезнет/станет платным/неудобным — миграция через новый ADR (Ollama / vLLM / llama.cpp).

## Что нужно сделать

- [x] Убрать `<placeholder>` из [`70-orchestration-codex-cli.md`](../../.ai/rules/70-orchestration-codex-cli.md), вписать реальную команду + Prerequisites + Troubleshooting.
- [x] Обновить [`invoke-codex` skill](../../.cursor/skills/invoke-codex/SKILL.md) Step 2 (Build invocation) и Pre-flight (проверка `CODEX_HOST`).
- [x] Закрыть открытый вопрос в `AGENTS.md` §9 (перевести в таблицу «Принятые решения»).
- [x] Добавить ADR-0005 в индексы (`docs/adr/README.md`, `AGENTS.md` §6).
- [ ] **Future:** при первой реальной делегации — определить способ подачи handoff'а (`--instructions` / stdin) и обновить документацию.
- [ ] **Future:** документировать pre-flight `curl /v1/models` как часть `invoke-codex` skill, если на практике окажется, что «забытый запуск LM Studio» — частая ошибка.

## Ссылки

- [LM Studio — Local Server](https://lmstudio.ai/docs/local-server)
- [Qwen3-Coder model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)
- ADR-0001 (MADR), ADR-0004 (gates вокруг merge — Codex CLI работает в feature-ветках, никогда не мерджит)
