# Changelog

## 1.0.0 (2026-05-05)


### Features

* **api:** PTR-32 add REST v1 persistent resource skeleton ([#42](https://github.com/enotbert/PTR_v2/issues/42)) ([d528f69](https://github.com/enotbert/PTR_v2/commit/d528f69227787430f83fa4a602ba59c4bac9427a))
* **api:** PTR-35 implement tavern state API ([#44](https://github.com/enotbert/PTR_v2/issues/44)) ([6773e82](https://github.com/enotbert/PTR_v2/commit/6773e826a725d472f406e88c9b9ae1e13894bf01))
* **api:** PTR-37 implement raid setup and party API ([#47](https://github.com/enotbert/PTR_v2/issues/47)) ([50f41dc](https://github.com/enotbert/PTR_v2/commit/50f41dca9fab92dcd3f005a20061b5203fd526a9))
* **backend:** PTR-18 uv lockfile and health pytest smoke ([#20](https://github.com/enotbert/PTR_v2/issues/20)) ([52436ac](https://github.com/enotbert/PTR_v2/commit/52436aca7eaac4b05bec606e2879e52aaad491b4))
* **backend:** PTR-28 FastAPI OpenAPI baseline ([#37](https://github.com/enotbert/PTR_v2/issues/37)) ([371d5a5](https://github.com/enotbert/PTR_v2/commit/371d5a5a20c2b1158f5752400ce544f1a9f0ab2f))
* **backend:** PTR-30 player session API v1 ([#39](https://github.com/enotbert/PTR_v2/issues/39)) ([2a0f701](https://github.com/enotbert/PTR_v2/commit/2a0f701ad5626627ebb4614f681d3a107b903ec1))
* **backend:** PTR-31 idempotency and audit primitives ([#40](https://github.com/enotbert/PTR_v2/issues/40)) ([4685799](https://github.com/enotbert/PTR_v2/commit/46857991ba3098e711b6849b7cb0c64f697d369b))
* **backend:** PTR-40 implement combat validation websocket flow ([#51](https://github.com/enotbert/PTR_v2/issues/51)) ([d6f0ae8](https://github.com/enotbert/PTR_v2/commit/d6f0ae898ab0150d560e647e4d3245952914108b))
* **backend:** PTR-66 add Alembic baseline and SQLAlchemy ([#24](https://github.com/enotbert/PTR_v2/issues/24)) ([6371cf7](https://github.com/enotbert/PTR_v2/commit/6371cf7ae768e2d9139d09e2faef582cff061489))
* **backend:** PTR-71 Alembic migration for dedup and audit tables ([#41](https://github.com/enotbert/PTR_v2/issues/41)) ([1d6f187](https://github.com/enotbert/PTR_v2/commit/1d6f18745e58a06d14539a80d95454bf1375c4da))
* **ci:** PTR-69 add frontend/backend lint and format gates ([#30](https://github.com/enotbert/PTR_v2/issues/30)) ([e727b6b](https://github.com/enotbert/PTR_v2/commit/e727b6b6f70882a6fdfc9a97aff39a15e82e70d9))
* **docker:** PTR-17 Docker Compose skeleton for dev stack ([#19](https://github.com/enotbert/PTR_v2/issues/19)) ([89dce8e](https://github.com/enotbert/PTR_v2/commit/89dce8e2a26a29cc956242fadc4fd117965cb3fb))
* **frontend:** PTR-19 dockerized Vite dev server ([#21](https://github.com/enotbert/PTR_v2/issues/21)) ([f1a76e4](https://github.com/enotbert/PTR_v2/commit/f1a76e4ca612e13189d45880ea8ff4231896796b))
* **frontend:** PTR-22 mobile-first app shell and network status ([#28](https://github.com/enotbert/PTR_v2/issues/28)) ([b43e427](https://github.com/enotbert/PTR_v2/commit/b43e427f49f4a32f4897fd9eb071acd3019485ef))
* **frontend:** PTR-23 add PWA manifest baseline ([#31](https://github.com/enotbert/PTR_v2/issues/31)) ([9959de7](https://github.com/enotbert/PTR_v2/commit/9959de7cefc939fff2887cd9c041e2579f961d7a))
* **frontend:** PTR-24 add service worker offline shell ([#32](https://github.com/enotbert/PTR_v2/issues/32)) ([725443f](https://github.com/enotbert/PTR_v2/commit/725443f9525a588a60558fd87005c54d90739230))
* **frontend:** PTR-25 implement offline api blocked gameplay states ([#33](https://github.com/enotbert/PTR_v2/issues/33)) ([7060f91](https://github.com/enotbert/PTR_v2/commit/7060f91890fb914f9deb338337079ff94a9c10b2))
* **frontend:** PTR-26 add Docker Playwright smoke reliability ([#35](https://github.com/enotbert/PTR_v2/issues/35)) ([e2b2b9f](https://github.com/enotbert/PTR_v2/commit/e2b2b9f814fb5d5a21458dfa2f16f62509d068ba))
* **frontend:** PTR-29 add generated OpenAPI client and types ([#38](https://github.com/enotbert/PTR_v2/issues/38)) ([3dd5e47](https://github.com/enotbert/PTR_v2/commit/3dd5e4770ca26fd665f806eabc670f076b8861fe))
* **frontend:** PTR-36 implement tavern home mobile UI ([#45](https://github.com/enotbert/PTR_v2/issues/45)) ([22489e1](https://github.com/enotbert/PTR_v2/commit/22489e139e17a569146c7ed9faceaf7c6847282c))
* **frontend:** PTR-39 implement first tutorial solo raid entry ([#50](https://github.com/enotbert/PTR_v2/issues/50)) ([6fddcd1](https://github.com/enotbert/PTR_v2/commit/6fddcd12c671a36ff5b6d268155ecb936a058165))
* **packages:** PTR-7 ptr_coder LM Studio agent adapter ([#8](https://github.com/enotbert/PTR_v2/issues/8)) ([1ea13ff](https://github.com/enotbert/PTR_v2/commit/1ea13ffc062c28735e5aee1c50a77d577cd4e10d))
* **ptr-coder:** PTR-68 stderr progress, cancel hook, HTTP timeout ([#29](https://github.com/enotbert/PTR_v2/issues/29)) ([ead705b](https://github.com/enotbert/PTR_v2/commit/ead705b99c59b3007b17dd5fccd0c44870dbceb4))
* **repo:** PTR-38 implement live lobby state over websocket ([#48](https://github.com/enotbert/PTR_v2/issues/48)) ([82c5952](https://github.com/enotbert/PTR_v2/commit/82c5952a42d5e52e34d16e189fcde4e6a85f62a1))


### Bug Fixes

* **repo:** PTR-70 enforce LF endings for frontend lint stability ([#34](https://github.com/enotbert/PTR_v2/issues/34)) ([dc3fb06](https://github.com/enotbert/PTR_v2/commit/dc3fb0608cb14d11953d85ce102ba9a832d20ee7))
* **rules:** PTR-5 remove broken anchor and unbacked Dependabot promise in security rules ([#5](https://github.com/enotbert/PTR_v2/issues/5)) ([2adf53b](https://github.com/enotbert/PTR_v2/commit/2adf53bee109af81dd3c8800dd4303a93d15eee1))
