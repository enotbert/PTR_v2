# 20 — Git и ветвление

## Модель

**Trunk-based development.** Единственная долгоживущая ветка — `main`. Всё остальное — короткоживущие feature-ветки, существующие на время работы над одной задачей.

## Имя ветки

Формат:

```
PTR-XXX-<kebab-slug>
```

Где:

- `PTR-XXX` — ID задачи в Linear (обязательно, ровно один).
- `<kebab-slug>` — короткое описание на английском, в нижнем регистре, через дефис, ≤ 50 символов.

Примеры:

- `PTR-123-add-auth`
- `PTR-456-fix-login-redirect`
- `PTR-789-refactor-user-service`

**Запрещено:**

- Префиксы по типу (`feat/`, `fix/`) — тип фиксируется в коммите/PR.
- Имена без `PTR-XXX`.
- Подчёркивания, camelCase, кириллица, пробелы.

## Создание ветки

Всегда от свежего `main`:

```bash
git checkout main
git pull --ff-only
git checkout -b PTR-XXX-<slug>
```

## Синхронизация с `main`

Если `main` ушёл вперёд во время работы:

```bash
git fetch origin
git rebase origin/main
```

**Только rebase, не merge.** История feature-ветки должна быть линейной до момента squash-merge в `main`.

При конфликтах — разрешить, продолжить rebase. Если конфликт сложный или непонятный — остановиться и спросить пользователя.

## Merge в `main`

- Стратегия: **squash-merge через PR**.
- Прямой push в `main` запрещён branch protection и [`90-forbidden.md`](90-forbidden.md).
- Имя squash-коммита = заголовок PR (см. [`30-commits-and-prs.md`](30-commits-and-prs.md)).

## Что запрещено

- `git push --force` (включая `--force-with-lease`) на любые удалённые ветки, кроме своих feature-веток в *крайних* случаях с явного разрешения пользователя. По умолчанию — нельзя.
- `git push origin :branch` — удаление веток на `origin` (кроме своей feature-ветки **после** успешного merge).
- Переписывание истории `main` (`rebase`, `reset`, `commit --amend` для уже запушенных коммитов в `main`) — категорически.
- Создание тегов и GitHub Releases — выходит за пределы автономии агента (см. [`90-forbidden.md`](90-forbidden.md)).
- Слияние одной feature-ветки в другую без явного основания.

## Размер и время жизни ветки

- Ветка живёт от **часов до 1–2 дней**. Долгоживущие ветки — антипаттерн.
- Если задача распухает — декомпозировать на подзадачи и подветки `PTR-XXX-<slug>-<part>`.
- Перед открытием PR — последний раз `git fetch && git rebase origin/main`.

## После merge

```bash
git checkout main
git pull --ff-only
git branch -d PTR-XXX-<slug>
```

Удалённую ветку чистит GitHub автоматически (включено `Automatically delete head branches`).
