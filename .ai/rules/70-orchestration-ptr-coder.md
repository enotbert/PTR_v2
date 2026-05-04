# 70 — Оркестрация: Cursor → ptr_coder (LM Studio)

> **Статус:** активно. Runtime и env-контракт зафиксированы в [ADR-0006](../../docs/adr/0006-python-lmstudio-coder-adapter.md). Исполнитель — пакет `packages/ptr_coder/` (`python -m ptr_coder` / CLI `ptr-coder`).
> **Решение:** Cursor вызывает **ptr_coder** как subprocess (Python) из корня репозитория. Передача задачи фиксируется письменно в `.ai/handoffs/`.

## Когда Cursor делегирует ptr_coder

Делегируем, когда задача:

- Чисто кодинговая (реализация по понятной спецификации).
- Однозначна по объёму и критериям приёмки.
- Не требует параллельных архитектурных решений посреди работы.

Не делегируем (Cursor делает сам):

- Документация и правила (`AGENTS.md`, `.ai/rules/`, ADR, README).
- Архитектурные изменения, проектирование схем данных, дизайн API.
- Триаж багов с непонятной причиной.
- Любая задача, где спецификация ещё не сформулирована.

## Хэндофф

Перед запуском ptr_coder Cursor создаёт файл:

```
.ai/handoffs/PTR-XXX-<kebab-slug>.md
```

Структура секций — **та же**, что использует `scripts/validate-handoff.sh` (девять обязательных заголовков `## …`). Полный шаблон см. в [`.ai/handoffs/README.md`](../handoffs/README.md) и в исторических примерах `PTR-*.md`.

Ключевые секции:

- `## Goal` — что сделать.
- `## Files in scope` / `## Out of scope` — границы изменений.
- `## Persona` — персона из [`65-personas.md`](65-personas.md).
- `## Commands` — команды для **независимой валидации** Cursor после прогона (lint / test / …).

Раздел `## Result` заполняет **Cursor** после завершения ptr_coder (ptr_coder **не** правит handoff).

## Запуск ptr_coder

Транспорт: **LM Studio** (или другой OpenAI-compatible сервер). Базовый URL и модель задаются переменными окружения (см. [ADR-0006](../../docs/adr/0006-python-lmstudio-coder-adapter.md) и корневой [`.env.example`](../../.env.example)).

### Env-контракт

| Переменная | Назначение | Дефолт |
|------------|------------|--------|
| `PTR_CODER_BASE_URL` | Базовый URL API (`…/v1`) | `http://localhost:1234/v1` |
| `PTR_CODER_MODEL` | Идентификатор модели на сервере | `qwen3-coder-30b-a3b-instruct` |
| `PTR_CODER_API_KEY` | Строка для заголовка авторизации (у LM Studio часто произвольная) | `lm-studio` |

### Prerequisites (проверять перед каждым запуском)

1. LM Studio запущен, **Local Server** включён.
2. Модель из `PTR_CODER_MODEL` **загружена в память**.
3. Доступность API: `curl` на `<origin>/v1/models` без `/v1` в host — т.е. если `PTR_CODER_BASE_URL=http://localhost:1234/v1`, то список моделей: `http://localhost:1234/v1/models` → HTTP 200, нужная модель в JSON.

Если проверка не прошла — ptr_coder завершится с ошибкой сети/SDK; исправить окружение и повторить.

### Канонический вызов

Из **корня репозитория** (где лежит `packages/ptr_coder/`):

POSIX:

```bash
export PTR_CODER_BASE_URL="${PTR_CODER_BASE_URL:-http://localhost:1234/v1}"
export PTR_CODER_MODEL="${PTR_CODER_MODEL:-qwen3-coder-30b-a3b-instruct}"
python -m ptr_coder \
  --handoff ".ai/handoffs/PTR-XXX-<kebab-slug>.md" \
  --root "." \
  --max-iterations 32
```

PowerShell:

```powershell
$env:PTR_CODER_BASE_URL = if ($env:PTR_CODER_BASE_URL) { $env:PTR_CODER_BASE_URL } else { "http://localhost:1234/v1" }
$env:PTR_CODER_MODEL     = if ($env:PTR_CODER_MODEL)     { $env:PTR_CODER_MODEL }     else { "qwen3-coder-30b-a3b-instruct" }
python -m ptr_coder --handoff ".ai/handoffs/PTR-XXX-<kebab-slug>.md" --root "." --max-iterations 32
```

После установки пакета доступен и entrypoint `ptr-coder` (с теми же флагами).

**Подача handoff'а:** путь к файлу передаётся только аргументом `--handoff` (явный путь). Отдельного stdin-хака не требуется.

### Ограничения v1 агента

Встроенные tools ptr_coder: `read_file`, `write_file`, `list_directory` — только JSON `function`, совместимые с LM Studio. Произвольный shell **не** вызывается.

## После завершения ptr_coder

1. Cursor заполняет `## Result` в handoff'е (время, exit code, что изменилось в `git diff`, прогон команд из `## Commands`).
2. Сравнивает диф с `## Files in scope` / `## Out of scope`.
3. При несоответствии — новая итерация (секция `## Iteration N`) или эскалация человеку.

## Troubleshooting

| Симптом | Причина | Что делать |
|---|---|---|
| `Connection refused` / сетевые ошибки | LM Studio не слушает порт | Запустить LM Studio, включить Local Server |
| `model not found` / 4xx от API | Другое имя модели в LM Studio | Выставить `PTR_CODER_MODEL` под фактический `id` из `/v1/models` |
| Долгий ответ без вывода | Большая модель на CPU/GPU | Увеличить терпение таймаута в Cursor Shell; уменьшить `--max-iterations` только если зацикливание |
| `path escapes workspace` | Модель запросила выход за `--root` | Уточнить спеку; корень должен быть корнем репозитория |

## Версионирование хэндоффов

- Хэндоффы коммитятся в репо вместе с кодом задачи.
- Один файл на задачу; итерации — дополнительные секции.
- После merge handoff **остаётся** в истории.

## Что ptr_coder **не должен** делать в рамках вызова

- Выходить за пределы `Files in scope` (инструменты ограничены `--root`; оркестратор всё равно сверяет дифф).
- Менять `.ai/rules/`, `AGENTS.md`, `.github/` по политике репозитория — как и для любого агента, без явного разрешения человека.
- Открывать PR и менять Linear — это Cursor после валидации.

## Передача управления человеку

Если после ≥ 2 итераций ptr_coder нет приемлемого результата — `Blocked` в Linear, PR в Draft, запросить вмешательство человека (как в общем workflow).

## История имени файла

Ранее правило называлось `70-orchestration-codex-cli.md` (Cursor → Codex CLI). Codex CLI снят с роли исполнителя кодинга ([ADR-0006](../../docs/adr/0006-python-lmstudio-coder-adapter.md)); актуальное правило — этот документ.
