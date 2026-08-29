# Release

## Shipped
- What: I7 (M19, T145 — direct video `<iframe>` embed) and I8 (M20, T146/T147 — private
  shared-article links) together, one push. I7 was implemented and reviewed 2026-08-26 but never
  separately pushed to `origin`/deployed; this is its first time live, riding along with I8.
- Where: production NAS — `https://profile.dmkdok.crazedns.ru:8443` (public), `http://192.168.1.20:8080`
  (LAN). Portainer stack `portfolio` (id 1), endpoint 3, `https://192.168.1.20:31015`.
- When: 2026-08-29.
- Method: `git merge --ff-only iteration/I8-token-shared-articles` into `main` (`ce8cc84..fb72a75`
  on `origin`, fast-forward, no conflicts) → `git push origin main` → GitHub Actions `publish`
  (run `33266553668`): `tests` green, then both images (`personal-site`, `personal-site-caddy`)
  built and pushed to GHCR tagged `latest` and `sha-fb72a75` → Portainer API `PUT
  /api/stacks/1?endpointId=3` with the live stack file and env unchanged, `pullImage: true` → all
  three containers recreated and healthy.

## Preflight
- Review verdict: `docs/REVIEW.md` run 9 (I7) and run 10 (I8), both PASS with findings, all
  resolved same session before this deploy — no open Critical/High.
- Env vars / secrets confirmed present (names only): `SECRET_KEY`, `ADMIN_USERNAME`,
  `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, `SITE_URL`, `MEDIA_HOST_DIR`, `PGDATA_HOST_DIR`,
  `HTTP_PORT`, `IMAGE_TAG` — unchanged from the already-running stack; neither I7 nor I8 adds a new
  variable (`git diff` against the prior deployed tip touches no `.env.example`, `deploy/`, or
  `docker-compose.prod.yml`).
- Migrations run: one — `a37da390e9d0` (creates `shared_article`, purely additive, no existing
  table altered). The application runs `alembic upgrade head` automatically at startup
  (`app/main.py`); applied on container start, not a separate manual step. Reversibility was
  already proved twice pre-deploy (implementation session and independent review, both on the dev
  database) — not re-proved against production, since a downgrade against live data was never the
  plan.

## Smoke test
- Evidence, all against the **public** address, run after the redeploy:

  | Check | Result |
  |---|---|
  | `GET /healthz` | 200 |
  | `GET /` | 200 |
  | `GET /blog` | 200 |
  | `GET /photo` | 200 |
  | `GET /dev` | 200 |
  | `GET /sitemap.xml` | 200 |
  | `GET /s/<invalid token>` | 404 (no existence leak, per F68) |
  | `GET /me/shared` (anonymous) | 404 (matches this codebase's admin-route convention — 404, not a login redirect) |

- Containers, confirmed via the Portainer Docker API proxy (endpoint 3) after the redeploy: all
  three recreated within the prior minute —
  `portfolio-web-1` `ghcr.io/dmkdok/personal-site:latest`, healthy;
  `portfolio-caddy-1` `ghcr.io/dmkdok/personal-site-caddy:latest`, running;
  `portfolio-db-1` `postgres:18-alpine`, healthy.
- Not smoke-tested live: creating a real shared article and opening its link, and the `/me/shared`
  editor's autosave/copy-link/regenerate flow — those are covered by T147's own e2e suite
  (`e2e/test_me.py`) against the dev stack, not repeated against production data.

## Rollback
- Command / steps: in Portainer → Stacks → `portfolio`, re-deploy pinned to the previous known-good
  tag, `sha-30010b9` (I6's build, the tag live before this deploy), instead of `latest` — same `PUT
  /api/stacks/1` shape, with `IMAGE_TAG=sha-30010b9` in the env instead of unset/`latest`, then
  `pullImage: true`. No database rollback needed: `a37da390e9d0` only adds a table, so the prior
  image's code simply never references `shared_article` and nothing breaks running against a schema
  one migration ahead of it.
- Verified before deploy: no — the rollback path is stated and reasoned about (additive-only
  migration, same mechanism as the forward deploy), not rehearsed live. Rehearsing it would mean
  briefly running I6's code in production, which was judged not worth doing for an additive schema
  change with a PASS review behind it.

## Notes
- I7 and I8 shipped as one deploy because I7 was never pushed on its own — `origin/main` had been
  sitting at `ce8cc84` (I6) since 2026-08-25. Anyone diagnosing a video-embed issue in production
  from this point on is also looking at I8's code, and vice versa.
- `docs/STATUS.md`'s "Resume here" carries the same facts in narrative form; this file is the
  structured record `deploy-product` asks for.
