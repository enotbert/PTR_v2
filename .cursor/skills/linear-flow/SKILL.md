---
name: linear-flow
description: Manage Linear issue lifecycle in the PTR team — pick up tasks, transition statuses (Todo, In Progress, In Review, Blocked, Done), link PRs and commits, leave structured comments, and create sub-tasks or follow-ups. Use when the user asks to start, update, block, comment on, or close a Linear task, when opening a PR that should move the issue to In Review, or when a follow-up issue needs to be created from current work.
---

# linear-flow

Operate Linear (team `PTR`, prefix `PTR-XXX`) per the rules in [`.ai/rules/50-task-management.md`](../../../.ai/rules/50-task-management.md). All actions go through the Linear MCP server.

## Allowed actions (per `.ai/rules/50`)

| Action | Allowed without explicit user confirmation? |
|---|---|
| Read issues, comments, statuses | ✅ |
| Set status: `Todo` → `In Progress` (when starting) | ✅ |
| Set status: `In Progress` → `In Review` (when PR opened) | ✅ |
| Set status: → `Blocked` with comment-cause | ✅ |
| Add comments (PR link, status updates, blockers) | ✅ |
| Add `links` attachments (PR, commits) | ✅ |
| Create new issues (sub-tasks or follow-ups) | ✅ — see "Creating issues" below |
| Set status to `Done` or `Cancelled` | ❌ — left to human or GitHub-Linear integration on PR merge |
| Delete issues or comments | ❌ |
| Change priority/estimate of others' issues | ❌ |
| Reassign issues to other people | ❌ |

## MCP tools

The Linear MCP server provides tools used by this skill. Always **read the tool descriptor first** under `mcps/plugin-linear-linear/tools/<tool>.json` before calling.

| Need | Tool |
|---|---|
| Find team / list teams | `list_teams` |
| List issues (filters by team, status, etc.) | `list_issues` |
| Get a specific issue | `get_issue` |
| Create or update issue | `save_issue` |
| Available statuses for a team | `list_issue_statuses` |
| Comment on issue | `save_comment` |
| Attach a URL (PR, commit) | `create_attachment` (or `links` field on `save_issue`) |
| Create label (only with user OK) | `create_issue_label` |

## Workflow: pick up a task

```
- [ ] Step 1: Read the issue
- [ ] Step 2: Verify acceptance criteria
- [ ] Step 3: Move to In Progress + assign to "me"
- [ ] Step 4: Comment with planned approach
```

### Step 1: Read the issue

```
Tool: get_issue
Arg: { "id": "PTR-XXX" }
```

Verify the description has clear acceptance criteria and a test plan. If absent — go to "Workflow: clarify ambiguous task" below before changing status.

### Step 2: Verify acceptance criteria

If criteria look incomplete:
- Do **not** start work.
- Use `save_comment` to ask a structured question, listing what's missing.
- Wait for human input.

### Step 3: Move to In Progress + assign to "me"

```
Tool: save_issue
Args: { "id": "PTR-XXX", "state": "In Progress", "assignee": "me" }
```

If the assignee is already someone else and that person isn't the current agent identity, **stop and ask** — do not steal someone else's work.

### Step 4: Comment with planned approach

```
Tool: save_comment
Args: {
  "issueId": "PTR-XXX",
  "body": "**План работы**\n\n- Тип: <feat|fix|refactor|docs|infra>\n- Ветка: `PTR-XXX-<slug>`\n- Скоуп: <короткий список файлов/областей>\n- Тест-план: <буллеты>\n- Оценка: <если есть>"
}
```

## Workflow: open a PR (transition to In Review)

After `gh pr create` returns a PR URL:

```
Tool: save_issue
Args: {
  "id": "PTR-XXX",
  "state": "In Review",
  "links": [
    { "url": "<PR URL>", "title": "PR #<N>: <title>" }
  ]
}
```

Then a comment with PR summary:

```
Tool: save_comment
Args: {
  "issueId": "PTR-XXX",
  "body": "**Открыт PR**: <PR URL>\n\n- Заголовок: `<type>(<scope>): PTR-XXX <description>`\n- Размер: <N> файлов / <M> строк\n- DoD: <короткий статус — что прогнал>\n- Известные ограничения: <если есть>"
}
```

## Workflow: block a task

When a hard external blocker is found:

```
Tool: save_issue
Args: { "id": "PTR-XXX", "state": "Blocked" }
```

Always accompany with a comment explaining:

```
Tool: save_comment
Args: {
  "issueId": "PTR-XXX",
  "body": "**Заблокировано**\n\n- Причина: <чёткое описание блокера>\n- Что уже сделано: <буллеты>\n- Что нужно от человека/внешней системы: <конкретный запрос>\n- Связанные артефакты: <PR/коммиты, если есть>"
}
```

If a PR is open — also mark it as Draft via `gh pr ready --undo` (separate operation, outside this skill).

## Workflow: create a follow-up issue

For a tangential issue discovered during work (do **not** fix it in the current PR):

```
Tool: save_issue
Args: {
  "team": "PTR",
  "title": "<≤80 chars, императив, на русском или английском>",
  "description": "## Контекст\n<откуда задача — ссылка на исходный PR/PTR-XXX>\n\n## Проблема\n<описание>\n\n## Acceptance criteria\n- [ ] <…>\n\n## Test plan\n<буллеты>",
  "state": "Backlog",
  "labels": ["<label-if-applicable>"],
  "relatedTo": ["PTR-XXX"]
}
```

Then comment in the **original** issue:

```
Tool: save_comment
Args: {
  "issueId": "PTR-XXX",
  "body": "Follow-up найден в ходе работы: PTR-YYY — <короткое описание>."
}
```

## Workflow: clarify ambiguous task

If acceptance criteria are missing or contradictory:

```
Tool: save_comment
Args: {
  "issueId": "PTR-XXX",
  "body": "**Требуются уточнения перед началом работы**\n\n1. <вопрос 1>\n2. <вопрос 2>\n3. <вопрос 3>\n\nПосле ответов сформулирую acceptance criteria и test plan здесь же, начну работу при подтверждении."
}
```

Do **not** change status to `In Progress` until the questions are answered.

## Comment style guide

- Markdown.
- Заголовок жирным в начале (`**Открыт PR**`, `**Заблокировано**`, …) — для быстрой визуальной навигации.
- Структурированные списки. Никаких «walls of text».
- Ссылки на PR/коммиты — полным URL (Linear их распарсит).
- Никаких секретов в комментариях (см. [`.ai/rules/80-security-and-secrets.md`](../../../.ai/rules/80-security-and-secrets.md)).
- Язык — русский (см. языковую политику в [`AGENTS.md` §2](../../../AGENTS.md#2-языковая-политика)).

## Anti-patterns

- ❌ Перевод задачи в `Done` или `Cancelled` без явного запроса человека (это делает интеграция при merge).
- ❌ Создание задачи без acceptance criteria и test plan.
- ❌ Создание дублирующих задач без проверки `list_issues`.
- ❌ Изменение чужих задач (assigned to another person).
- ❌ Комментарий без структуры — «делал то, делал сё, ничего не получилось».
- ❌ Использование магических слов закрытия (`Closes PTR-XXX`) в комментариях — они работают только в PR-описаниях.

## Related

- Rules: [`.ai/rules/50-task-management.md`](../../../.ai/rules/50-task-management.md)
- Workflow: [`.ai/rules/10-workflow.md`](../../../.ai/rules/10-workflow.md)
- Forbidden: [`.ai/rules/90-forbidden.md`](../../../.ai/rules/90-forbidden.md)
- Linear MCP descriptors: `mcps/plugin-linear-linear/tools/`
