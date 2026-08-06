# Where this project stands (2026-08-06)

Personal multi-section portfolio site for Dmitriy Bogdanov: Главная / Разработка / Фото / Блог,
plus an authenticated authoring surface. Plan was approved 2026-08-04 («Утверждаю»), so
implementation is unblocked. Phase 4 of 7.

`docs/STATUS.md` is the authoritative handoff — read it before doing anything. This memory only
orients you.

## Milestones

- M0–M2 done: scaffold, design system, schema, auth, admin core.
- M3 photography — **code complete, tests RED.** See blocker below.
- M4 blog — done and green (T040–T045).
- M5 development — done (T050–T053).
- M6 search + SEO — done (T060–T062).
- M7 harden — T073/T074 written and not deployed; `e2e/` is empty (T070 not started);
  T071 a11y, T072 performance, T075 handoff all open.

## The blocker to fix first

`docker compose run --rm tests` → 137 tests, 120 pass, 17 fail, all in `tests/api/test_photo.py`.

`app/background.py` holds `_executor` as a module-level `ThreadPoolExecutor`, and `lifespan` in
`app/main.py` (line 66) calls `background.shutdown()` on exit. Under pytest the first `TestClient`
teardown kills the executor for the whole process, so every later upload raises
`RuntimeError: cannot schedule new futures after shutdown`. The first 52 tests pass, then
`test_photo.py` fails en masse. It is a test-lifecycle defect, not a product defect.

`test_albums_can_be_reordered` fails with a jinja2 template error — possibly a genuine second bug,
check it separately.

## Environment facts that cost time to rediscover

- Tests only run in a container: `docker compose run --rm tests`. Starlette's `TestClient` hangs on
  the Windows host before collection.
- Compose project is named `dmkdok-portfolio`. It was originally `portfolio`, which collided with a
  different stack at `C:\Users\dmkdok\AI\Portfolio` and recreated its containers. Never rename it back.
- Postgres 18+ needs the volume at `/var/lib/postgresql`, not `/var/lib/postgresql/data`.
- Serena: activate by path, not by name — `portfolio` is ambiguous on this machine.
- Never pipe a test run through `tail`; you get the pipe's exit code and a red suite looks green.

## Stack

FastAPI 0.141 + Jinja2 + htmx 2.0 + PostgreSQL 18 + Pillow 12.3, hand-written CSS, no Node build.
Russian full-text search via generated `search_vector` columns. Argon2id auth with session-token
rotation. See `docs/PLAN.md` § Architecture and § Repository map.
