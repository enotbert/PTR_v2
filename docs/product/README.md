# Product documentation

Этот каталог хранит продуктовые документы Pocket Raid Tavern, которые должны быть доступны агентам и ревьюерам
прямо из основного репозитория.

## Документы

| Файл | Назначение |
|---|---|
| [PRD_v1_public_early_access.md](PRD_v1_public_early_access.md) | Требования к публичной v1 / early access: цели, user flows, функциональные и нефункциональные требования, release gates. |
| [ux_state_matrix_v1.md](ux_state_matrix_v1.md) | UX/state matrix для первой сессии, regular raid и social/share flows: состояния, mobile constraints, acceptance criteria для UI-задач и Playwright-сценарии. |
| [LORE_v0.1.md](LORE_v0.1.md) | Базовый сеттинг, тон, архетипы ролей и визуальные опоры для UI-текста и prototype assets. |
| [enemy_roster_v1.md](enemy_roster_v1.md) | Минимальный набор PvE-врагов и мини-босса v1, синергии врагов, wave patterns и boss encounter grammar. |
| [weekly_event_v1.md](weekly_event_v1.md) | Первый weekly event public EA: `weekly_route_reopening`, вклад в маршрут, rewards/progress, UX entry points и analytics. |

## Правило обновления

- Если меняются требования публичной v1, обновлять PRD в том же PR, где меняется соответствующее решение.
- Если лор начинает требовать новую механику, API, экономику, платформу или PWA-поведение, это сначала проходит
  через PRD/ADR и Linear issue.
- Linear остаётся трекером задач, но source-of-truth документы должны жить в git и попадать в проект через PR.
