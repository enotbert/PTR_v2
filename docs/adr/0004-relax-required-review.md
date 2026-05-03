# 0004 — Снять обязательный approving review в branch protection (solo-dev)

- **Статус:** Accepted
- **Дата:** 2026-05-03
- **Авторы:** @enotbert
- **Связано с:** [`AGENTS.md`](../../AGENTS.md), [`.ai/rules/40-code-quality.md`](../../.ai/rules/40-code-quality.md), [`.ai/rules/10-workflow.md`](../../.ai/rules/10-workflow.md), [`.ai/rules/90-forbidden.md`](../../.ai/rules/90-forbidden.md)

## Контекст

На этапе bootstrap branch protection на `main` был настроен по «полной» схеме (см. ранние коммиты): требование PR + **1 approving review** + status checks + запрет force-push/удаления + линейная история (`enforce_admins=false`).

В реальности проект в фазе solo-разработки: единственный человек-разработчик (`@enotbert`) одновременно автор почти всех PR. GitHub политически блокирует **self-approve** собственных PR. Это приводит к одному из трёх сценариев:

1. Каждый раз делать admin-bypass (`gh pr merge --admin` или галочка в UI). Шумно, размывает смысл «approve обязателен».
2. Завести бот-аккаунт-ревьюера, давать ему PAT, автоматизировать approve. Реализуемо, но вводит постоянный operational overhead и ещё один токен в ротацию ради одной галочки.
3. Снять требование approve, оставив остальные гейты. Признать, что review — **рекомендация**, а не инфра-энфорсмент, на текущей фазе.

PR #1 и PR #2 на практике подтвердили: friction есть, и он не несёт защитной ценности — single human review невозможен физически.

## Рассмотренные варианты

- **Вариант A: Status quo + admin-bypass на каждый PR.** Минус — шум, лишний клик/флаг, риск забыть и не помержить вовремя; плюс — формально гейт остаётся.
- **Вариант B: Bot-account как ревьюер.** Минус — operational overhead, ещё один секрет, ещё одна identity для аудита; плюс — формальный approve сохранён.
- **Вариант C: Снять обязательный approve, оставить остальные гейты.** ✅ выбран.
- **Вариант D: Полностью отключить branch protection.** Никогда — теряем PR-обязательность, status checks, защиту от force-push.

## Решение

Изменить branch protection на `main`:

- `required_approving_review_count: 1 → 0`
- `require_code_owner_reviews: true → false`

Сохранить **без изменений**:

- `required_pull_request_reviews` блок присутствует → **PR по-прежнему обязателен**, прямой push в `main` запрещён.
- `required_status_checks: { strict: true, contexts: ["ci"] }` → CI обязателен и ветка должна быть актуальной.
- `dismiss_stale_reviews: true` → если кто-то всё-таки оставил approve и потом был push, approve сбрасывается (актуально, когда появится второй ревьюер).
- `required_linear_history: true`, `allow_force_pushes: false`, `allow_deletions: false`, `required_conversation_resolution: true`.
- `enforce_admins: false` → admin может bypass на крайний случай (например, неработающий status check).

**Критически важно:** процедурное правило **«агент не мерджит свой PR»** сохраняется в [`.ai/rules/90-forbidden.md`](../../.ai/rules/90-forbidden.md) как ограничение поведения агентов. Branch protection больше не обеспечивает это технически — агент мог бы (теоретически) открыть PR и тут же его смерджить. Запрет остаётся **правилом поведения**, и это **главный гейт автономии** на текущей фазе.

Соответственно, **факт merge человеком** становится более значимым, чем «approve»: именно решение нажать «Squash and merge» — точка контроля.

## Последствия

### Положительные

- Solo-разработчик мерджит свои PR без admin-bypass. Меньше friction, меньше шанс забытых PR.
- Workflow остаётся «PR + CI», все защиты от случайных деструктивных действий — на месте.
- Когда появится второй человек/агент — он естественно становится ревьюером, и можно безболезненно вернуть `required_approving_review_count: 1` обратно (новый ADR).

### Отрицательные / компромиссы

- **Human review больше не enforced инфраструктурой.** Положенность гейта переезжает в дисциплину агента: «не мерджу свой PR». Если правило обойти намеренно/случайно — никто кроме человека этого не остановит.
- **Риск авто-merge** через `gh pr merge --auto` или auto-merge UI button. На текущей фазе **agent self-merge запрещён правилом**; auto-merge кнопкой пользуется человек осознанно.
- **CODEOWNERS больше не enforced.** Файл `CODEOWNERS` остаётся (для будущего), но GitHub не блокирует merge при отсутствии review code owner'а. Это просто справочный документ, пока режим solo.

## Что нужно сделать

- [x] Применить изменение branch protection через `gh api` (выполнено до открытия PR).
- [x] Обновить `AGENTS.md` §7 (DoD): «approve обязателен» → «merge человеком».
- [x] Обновить `.ai/rules/40-code-quality.md` пункт 9: «Human review» → «Human merge», с примечанием про рекомендованный review.
- [x] Обновить `.ai/rules/10-workflow.md` Шаг 8: переименовать «Ожидание review» → «Передача человеку для merge», смягчить формулировки.
- [x] Обновить `.ai/rules/30-commits-and-prs.md`: уточнить, что approve опционален.
- [x] Усилить `.ai/rules/90-forbidden.md`: явно отметить, что «agent self-merge запрещён» — **процедурное правило, не зависит от настроек protection**.
- [x] Добавить ADR-0004 в индексы (`docs/adr/README.md`, `AGENTS.md` §6).
- [ ] **Future:** при появлении второго ревьюера — новый ADR, возвращающий `required_approving_review_count: 1`.
- [ ] **Future:** рассмотреть бот-аккаунт-ревьюера, если нужны формальные approve'ы (например, для compliance) — отдельный ADR.

## Ссылки

- GitHub Docs: [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- GitHub Docs: [Restrict who can merge — bypass and admin override](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- ADR-0002 — release-please (контекст по гейтам CI на release-PR)
