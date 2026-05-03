# PTR-smoke — LM Studio invoke smoke (fixture)

## Goal

Проверка связки **ptr_coder → LM Studio**: модель должна ответить **одной строкой текста** без вызова инструментов.

Скопируй в ответ (в поле обычного assistant message, без tool_calls) **ровно** эту строку и ничего больше:

`LMSTUDIO_INVOKE_OK`

Не вызывай read_file, write_file и list_directory для этой задачи.

## Context

Локальный smoke-тест после merge PR с пакетом `ptr_coder`.

## Files in scope

- (нет изменений файлов — только текстовый ответ модели)

## Out of scope

- Любые изменения в репозитории через tools.

## Persona

**qa**

Минимальная проверка интеграции; персона формальна.

## Acceptance criteria

- [ ] Финальный ответ модели содержит подстроку `LMSTUDIO_INVOKE_OK`.
- [ ] В ходе ответа не требуется изменять файлы.

## Test plan

- Запуск: `python -m ptr_coder --handoff <этот файл> --root <корень репо> --max-iterations 5`
- Успех: exit 0 и stdout содержит `LMSTUDIO_INVOKE_OK`.

## Constraints

- Только OpenAI-compatible chat; без shell.

## Commands

| Тип | Команда |
|---|---|
| Lint | N/A |
| Format | N/A |
| Typecheck | N/A |
| Test | `pytest packages/ptr_coder/tests -q` |
| E2E | `python -m ptr_coder --handoff packages/ptr_coder/tests/fixtures/lmstudio_invoke_smoke.md --root .` |

## Result

(заполняет Cursor после прогона)
