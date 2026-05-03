# 0002 — Использовать release-please для CHANGELOG и версионирования

- **Статус:** Accepted
- **Дата:** 2026-05-03
- **Авторы:** @enotbert
- **Связано с:** [.ai/rules/30-commits-and-prs.md](../../.ai/rules/30-commits-and-prs.md), [release-please-config.json](../../release-please-config.json), [.github/workflows/release-please.yml](../../.github/workflows/release-please.yml)

## Контекст

Репозиторий — мультиязыковая монорепа под автономную AI-разработку. Принята конвенция [Conventional Commits](https://www.conventionalcommits.org/) с обязательным `scope` (см. `.ai/rules/30-commits-and-prs.md`). Чтобы:

- Не вести CHANGELOG вручную (источник дрейфа и забытых записей у соло-разработчика и AI-агентов).
- Иметь воспроизводимые версии и релиз-ноты, выводимые из коммитов.
- Автоматизировать процесс bump'а версии при squash-merge'ах в `main`.

…нужен инструмент автоматической генерации CHANGELOG и тегирования.

## Рассмотренные варианты

- **Вариант A: release-please (Google).** Создаёт release-PR, обновляющий CHANGELOG и версии, на основе CC-коммитов в `main`. Поддерживает manifest-режим для монорепы (несколько пакетов с независимыми версиями). Активно поддерживается. ✅ выбран.
- **Вариант B: changesets (Atlassian/pnpm-экосистема).** Требует явного `.changeset/*.md` в каждом PR. Хорош для крупных монореп с осознанной командой; для AI-агентов — лишний шаг с правом ошибки.
- **Вариант C: Keep a Changelog вручную.** Минимальная инфраструктура, максимальный человеческий труд и риск дрейфа.
- **Вариант D: semantic-release.** Релизит на каждый коммит в `main`. Слишком агрессивно для нашего ритма; меньше контроля чем release-PR.

## Решение

Принимаем **release-please** в monorepo-manifest-режиме:

- `release-please-config.json` — конфигурация.
- `.release-please-manifest.json` — состояние версий по пакетам (на старте: `"."`: `0.0.0`).
- `.github/workflows/release-please.yml` — workflow на `push: main`.
- Тип релиза на корне — `simple` (нет публикуемого артефакта; release = тег + GH Release + CHANGELOG).
- `bootstrap-sha` указывает на `c04fb0d` (текущий `main` HEAD на момент принятия решения), чтобы release-please игнорировал предшествующие не-CC коммиты.
- `pull-request-title-pattern: "chore(repo): release${component} ${version}"` — release-PR создаётся с заголовком, валидным под нашу CC-конвенцию (тип `chore`, scope `repo`).
- При появлении публикуемых пакетов — добавляем их в `packages` секцию config с подходящим `release-type` (`node`, `python`, `rust`, `go` и т. п.) и независимым версионированием.

## Последствия

### Положительные

- CHANGELOG генерируется автоматически из коммитов; ручной труд исключён.
- Версии и теги создаются предсказуемо; история релизов восстановима.
- При росте монорепы каждый пакет получает независимую версию без переписывания процесса.

### Отрицательные / компромиссы и известные проблемы

- **Release-PR не триггерит CI по умолчанию.** PR'ы, созданные `GITHUB_TOKEN`, по политике GitHub *не* запускают другие workflow runs. Наш обязательный status check `ci` не отработает на release-PR без вмешательства. Возможные пути:
  1. **Текущий минимальный (принят):** мейнтейнер закрывает и заново открывает release-PR (или пушит пустой коммит), чтобы CI отработал. Приемлемо при низкой частоте релизов.
  2. **PAT (Personal Access Token):** токен с правами `repo` хранится в `secrets.RELEASE_PLEASE_TOKEN`, передаётся в action. PR'ы тогда триггерят workflow. Минус — PAT привязан к человеку, требует ротации.
  3. **GitHub App:** официальный путь. Больше initial setup, но решает все trigger-проблемы и даёт чистый identity для бота.
  Решение: начать с пути (1), при росте частоты релизов мигрировать на (3). Это решение пересмотрим отдельным ADR.
- **Release-PR — исключение из правила `<type>(<scope>): PTR-XXX <description>`.** Release-PR не привязан к задаче в Linear (он автогенерируется). Зафиксировано в `.ai/rules/30-commits-and-prs.md`.
- **CODEOWNERS требует review.** Release-PR будут проходить review @enotbert (PR создан ботом, поэтому self-approve не блокирует).
- **На старте (при отсутствии `feat:` коммитов) релиза не будет.** Это ожидаемо: первая запись в CHANGELOG появится после первого `feat:` или явного triggering tag.

## Что нужно сделать

- [x] Добавить `LICENSE`, `release-please-config.json`, `.release-please-manifest.json`, `.github/workflows/release-please.yml`.
- [x] Обновить [.ai/rules/30-commits-and-prs.md](../../.ai/rules/30-commits-and-prs.md): зафиксировать исключение для release-PR.
- [ ] При появлении первого публикуемого пакета — расширить `packages` в config, добавить релевантный `release-type`, описать в новом ADR.
- [ ] При росте частоты релизов или болевых ощущений с close+reopen — мигрировать на GitHub App (новый ADR).

## Ссылки

- [release-please documentation](https://github.com/googleapis/release-please)
- [release-please-action v4](https://github.com/googleapis/release-please-action)
- [GitHub: events from GITHUB_TOKEN do not trigger workflows](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)
