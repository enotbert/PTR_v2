# PTR-6 — Handoff validator script

## Goal

Реализовать скрипт `scripts/validate-handoff.sh`, который проверяет, что переданный markdown-файл (handoff из `.ai/handoffs/PTR-XXX-<slug>.md`) содержит **все девять обязательных секций** по протоколу из `.ai/rules/70-orchestration-codex-cli.md`. Сопроводить простым тест-раннером и фикстурами **без внешних зависимостей**.

Это **первая реальная делегация** Cursor → Codex CLI в проекте PTR. Помимо самого деливерэбла, побочно проверяется работоспособность канонической команды Codex CLI (ADR-0005) и удобство handoff-протокола.

## Context

- Протокол хэндоффов и список обязательных секций: [`.ai/rules/70-orchestration-codex-cli.md`](../rules/70-orchestration-codex-cli.md).
- Как Cursor вызывает Codex и валидирует результат: [`.cursor/skills/invoke-codex/SKILL.md`](../../.cursor/skills/invoke-codex/SKILL.md).
- Глобальные правила и DoD: [`AGENTS.md`](../../AGENTS.md), [`.ai/rules/40-code-quality.md`](../rules/40-code-quality.md).
- Forbidden список: [`.ai/rules/90-forbidden.md`](../rules/90-forbidden.md). Особенно: **не трогать `.github/`, `.ai/rules/`, `AGENTS.md`, lockfiles, секреты**.
- Существующих handoff-файлов кроме этого в репо нет — `.ai/handoffs/` содержит только `README.md`. Этот файл (`PTR-6-handoff-validator.md`) **сам должен пройти валидацию** после реализации.

## Files in scope

Codex создаёт **только** эти файлы:

- `scripts/validate-handoff.sh` `[NEW]` — основной скрипт валидатора.
- `scripts/tests/test-validate-handoff.sh` `[NEW]` — тест-раннер на чистом bash.
- `scripts/tests/fixtures/valid-handoff.md` `[NEW]` — фикстура: все 9 секций присутствуют, проходит валидацию.
- `scripts/tests/fixtures/missing-section.md` `[NEW]` — фикстура: отсутствует одна секция (например, `## Persona`), валидация фейлится.
- `scripts/tests/fixtures/whitespace-headers.md` `[NEW]` — фикстура: заголовки секций с trailing whitespace (например, `## Goal   ` с пробелами в конце), всё равно валидируются.
- `scripts/tests/fixtures/empty.md` `[NEW]` — фикстура: пустой файл, фейлится с перечислением всех 9 отсутствующих секций.

Все скрипты должны иметь shebang `#!/usr/bin/env bash` и быть исполняемыми (`chmod +x`).

## Out of scope

Codex **не трогает**:

- Этот handoff-файл (`.ai/handoffs/PTR-6-handoff-validator.md`). Раздел `## Result` будет заполнен Cursor'ом после Codex run'а.
- `.github/workflows/ci.yml` — Cursor добавит CI job `validate-handoff` отдельным коммитом в этой же ветке (запрещено персоне `infra` через делегирование, см. `90-forbidden.md`).
- Любые файлы вне списка `Files in scope`.
- Документацию (`README.md`, `.ai/rules/*`, `AGENTS.md`, ADR).
- Зависимости, lockfiles, package manifests.

Если по ходу работы выявляется проблема, требующая правок вне `Files in scope` — **зафиксировать в `## Result` → `Issues out of scope`**, не править.

## Persona

**infra**

You are working as the **infra** persona. Apply rules from `.ai/rules/65-personas.md#infra` in addition to the global rules and the constraints in this handoff.

Constraints specific to this brief:

- Scope: только файлы из секции `## Files in scope` выше.
- Forbidden in this brief (на всякий случай повторно):
  - `.github/`, `.ai/rules/`, `AGENTS.md`, ADR.
  - Any package manifests / lockfiles / version pin files.
  - Network/external calls in scripts (валидатор работает строго локально на тексте файла).
- Rollback plan: всё новое — single PR `PTR-6`, ничего из существующего не модифицируется, откат = revert PR.
- Validation: на feature-ветке всё должно проходить (см. `## Commands` и `## Test plan`).

## Acceptance criteria

### Скрипт `scripts/validate-handoff.sh`

- [ ] **CLI:** `validate-handoff.sh <path-to-handoff.md>` (один обязательный позиционный аргумент).
- [ ] **Exit 0:** все девять обязательных секций (см. ниже) присутствуют в файле. На stdout — одна строка вида `OK: all required sections present in <path>`.
- [ ] **Exit 1:** одна или больше обязательных секций отсутствует. На stderr — одна строка `MISSING: <section header>` для каждой отсутствующей (точно в том виде, в каком она ожидалась, например `MISSING: ## Persona`). Порядок строк = порядок секций в списке ниже. На stdout ничего не печатается.
- [ ] **Exit 2:** аргумент не передан, или файл по указанному пути не существует, или путь — не файл (директория и т. п.). На stderr — usage-строка вида `Usage: validate-handoff.sh <path-to-handoff.md>`. На stdout ничего.
- [ ] Любой другой exit code (например 3+) — недопустим. Скрипт не должен крашиться на пустом / бинарном входе — должен корректно сообщать MISSING для всех секций или возвращать ненулевой код.
- [ ] Скрипт не делает сетевых вызовов и не пишет в файлы (read-only).
- [ ] Использует `set -euo pipefail` (bash) или эквивалент для надёжности.

### Список обязательных секций (точно в этом порядке)

```
## Goal
## Context
## Files in scope
## Out of scope
## Persona
## Acceptance criteria
## Test plan
## Constraints
## Commands
```

**Правила matching'а:**

- Сравнение построчное: ищем строку, которая **после удаления leading и trailing whitespace** равна одной из ожидаемых.
- Регистр учитывается (case-sensitive). `## goal` ≠ `## Goal`.
- Допускается ровно один уровень `##` (не `###`, не `#`).
- Секция считается «present» при наличии **хотя бы одного** matching-заголовка.
- Содержимое секций НЕ проверяется — только наличие самих заголовков.

### Тест-раннер `scripts/tests/test-validate-handoff.sh`

- [ ] CLI: `test-validate-handoff.sh` (без аргументов).
- [ ] Exit 0 если все тесты прошли. Exit 1 если хоть один зафейлился.
- [ ] Печатает по строке на тест: `PASS <name>` или `FAIL <name>: <reason>`.
- [ ] В конце — итоговая строка вида `RESULT: <passed>/<total> passed`.
- [ ] Покрывает минимум следующие сценарии (по одному тесту на каждый):
  1. **fixture `valid-handoff.md`**: exit 0, stdout содержит `OK:`.
  2. **fixture `missing-section.md`**: exit 1, stderr содержит `MISSING: ## Persona` (если убрана именно Persona; иначе — соответствующая).
  3. **fixture `whitespace-headers.md`**: exit 0 (whitespace в заголовках не должен ломать matching).
  4. **fixture `empty.md`**: exit 1, stderr содержит **все девять** строк `MISSING: ...`.
  5. **отсутствующий файл**: вызов с путём `/nonexistent/path.md` → exit 2.
  6. **без аргументов**: exit 2.
- [ ] Не зависит от `bats`, `shunit2` или других внешних shell-test фреймворков. Только bash + coreutils.

### Фикстуры

- [ ] `valid-handoff.md` — содержит все девять заголовков. Содержимое секций может быть placeholder-ом (`<placeholder>` или короткие фразы); единственное требование — проходит валидацию.
- [ ] `missing-section.md` — копия `valid-handoff.md` минус **ровно одна** секция. Какая именно — на твоё усмотрение, но тест должен проверять корректное конкретное сообщение `MISSING: ...`.
- [ ] `whitespace-headers.md` — копия `valid-handoff.md`, но в каждом заголовке секции добавлен trailing whitespace (один-два пробела или таб в конце строки `## Goal`). Должна проходить валидацию.
- [ ] `empty.md` — пустой файл (нулевой размер или одна-две пустые строки).

### Качество

- [ ] **shellcheck** чистый по обоим `.sh` файлам (zero warnings, zero errors). На фикстуры (`.md`) shellcheck не запускается.
- [ ] Никаких хардкода путей с разделителями специфичными для Windows.
- [ ] Скрипты работают из любого CWD (используют пути относительно расположения скрипта или абсолютные через первый аргумент).

## Test plan

### Юнит / поведенческие тесты

Покрыты в `scripts/tests/test-validate-handoff.sh` (см. список из 6 сценариев в Acceptance criteria).

### Интеграция (E2E)

После реализации Codex прогоняет валидатор против самого этого handoff-файла:

```bash
bash scripts/validate-handoff.sh .ai/handoffs/PTR-6-handoff-validator.md
```

Ожидание: exit 0, stdout `OK: all required sections present in .ai/handoffs/PTR-6-handoff-validator.md`. Если не проходит — handoff-файл не соответствует протоколу, **остановиться и сообщить в `## Result`**, не пытаться править handoff.

### Линтер

```bash
shellcheck scripts/validate-handoff.sh scripts/tests/test-validate-handoff.sh
```

Должен пройти без warnings.

## Constraints

- **Совместимость:** bash 3.2+ (макос-дефолт). Никаких bash 4+ specifics (associative arrays через `declare -A`, `mapfile`/`readarray`). Если без bash 4 неудобно — **сообщить в `## Result`**, не использовать тихо.
- **Зависимости:** только то, что есть на любом современном Linux runner'е и macOS из коробки: `bash`, `grep`, `sed`, `awk`, `cat`, `printf`, `tr`, `wc`. Никаких `jq`, `yq`, `pandoc`, `python`, `node` и т. п.
- **Стиль:** `set -euo pipefail`; кавычки везде где это меняет поведение; одиночные кавычки для литералов, двойные — для интерполяции; никаких `eval`; функции вместо повторяющихся inline-блоков.
- **Производительность:** валидатор работает на одном файле размером единицы килобайт. Никаких premature optimizations — читаемость важнее.
- **Локали:** не предполагать `LANG=en_US.UTF-8`. Pattern-matching должен быть устойчив к разным locale (использовать `LC_ALL=C` где имеет смысл — например, перед `grep`).
- **Без побочных эффектов:** валидатор не пишет, не меняет permissions, не создаёт temp-файлов (если без них действительно никак — создать в `mktemp` и удалить через `trap`).

## Commands

| Тип | Команда |
|---|---|
| Lint | `shellcheck scripts/validate-handoff.sh scripts/tests/test-validate-handoff.sh` |
| Test | `bash scripts/tests/test-validate-handoff.sh` |
| Format | N/A (универсального форматера для shell у нас нет; `shfmt` не установлен) |
| Typecheck | N/A |
| E2E | `bash scripts/validate-handoff.sh .ai/handoffs/PTR-6-handoff-validator.md` |

## Result

<!-- Заполняется Cursor'ом после Codex run'а на основании stdout/stderr/exit-code Codex'а и независимой валидации. -->
