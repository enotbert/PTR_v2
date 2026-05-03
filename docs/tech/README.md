# Technical documentation

Этот каталог хранит технические контракты Pocket Raid Tavern, которые нужны backend/frontend задачам до появления
исполняемой реализации.

## Документы

| Файл | Назначение |
|---|---|
| [websocket-protocol-v1.md](websocket-protocol-v1.md) | Минимальный WebSocket protocol contract для lobby/combat v1: snapshots, events, commands, errors, sequence/idempotency и reconnect. |

## Правило обновления

- Если меняется WebSocket message name, payload shape или reconnect/idempotency behavior, обновлять protocol doc в том
  же PR, где меняется соответствующее решение.
- Если изменение расширяет scope v1 или меняет transport model, сначала оформить Linear issue и при необходимости ADR.
