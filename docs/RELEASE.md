# Release

## Shipped
- What: I9 (M21, T148/T149/T150 — article editor UX: shared toolbar/cheat sheet, the photo
  control as its own action with per-file upload progress, a narrow-viewport pane switch that
  reaches the preview without scrolling).
- Where: production NAS — `https://profile.dmkdok.crazedns.ru:8443` (public), `http://192.168.1.20:8080`
  (LAN). Portainer stack `portfolio` (id 1), endpoint 3, `https://192.168.1.20:31015`.
- When: 2026-09-02.
- Method: `git merge --ff-only iteration/I9-article-editor-ux` into `main` (`fdd8c47..ce38ace` on
  `origin`, fast-forward, no conflicts) → `git push origin main` → GitHub Actions `publish` (run
  `33680249219`): `tests` green, then both images (`personal-site`, `personal-site-caddy`) built
  and pushed to GHCR tagged `latest` and `sha-ce38ace` → Portainer API `GET /api/stacks/1` +
  `GET /api/stacks/1/file` to fetch the live stack definition unchanged, then `PUT
  /api/stacks/1?endpointId=3` with that same stack file and env, `PullImage: true` → all three
  containers recreated and healthy. The Portainer API key came from `.env.truenas` (untracked,
  outside the repo's own `.env`), read locally and never printed.

## Preflight
- Review verdict: PASS with one Medium (CSS duplication, recorded as carried debt, not blocking)
  and one informational Low, no Critical or High — recorded in `docs/STATUS.md`'s I9 "Resume here"
  section by an independent `reviewer` subagent pass. **Not also logged as a numbered run in
  `docs/REVIEW.md`**, unlike I5–I8's deploys before it — a process gap in this iteration's own
  record-keeping, not a reason to withhold the verdict, since the same PASS is stated plainly and
  its one finding is described in full.
- Env vars / secrets confirmed present (names only), fetched live from the Portainer stack via its
  API rather than assumed: `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`,
  `SITE_URL`, `MEDIA_HOST_DIR`, `PGDATA_HOST_DIR`, `HTTP_PORT`, `IMAGE_TAG` — same nine as I8's
  deploy, unchanged. `git diff --stat main..iteration/I9-article-editor-ux` before the merge
  touched none of `.env.example`, `deploy/`, or `docker-compose.prod.yml`, and T148–T150 are
  CSS/JS/template/i18n only.
- Migrations: none. No file under an Alembic revisions path appears in the branch diff.
- Live stack file drift found and judged harmless: the file Portainer is actually running differs
  from the repo's tracked `deploy/portainer-stack.yml` by one reworded comment block (the
  `LOGS_HOST_DIR` explanation), no service/variable/behaviour change — someone edited the live
  Portainer stack's comment directly at some point without syncing it back to the repo. Not fixed
  as part of this deploy (out of T148–T150's scope); worth a follow-up to copy the live wording
  back into the tracked file so the two stop drifting.

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
  | `GET /me/shared` (anonymous) | 404 (matches this codebase's admin-route convention) |

- Containers, confirmed via the Portainer Docker API proxy (endpoint 3) after the redeploy: all
  three recreated within the same minute and settled healthy —
  `portfolio-web-1` `ghcr.io/dmkdok/personal-site:latest`, healthy;
  `portfolio-caddy-1` `ghcr.io/dmkdok/personal-site-caddy:latest`, running;
  `portfolio-db-1` `postgres:18-alpine`, healthy.
- Not smoke-tested live: the new pane switch itself (F75) and the photo control's per-file
  progress rows (F73) are both admin-only, behind login, and browser-interaction-shaped — not
  reachable by an anonymous `curl` smoke test. Both are covered by this iteration's own e2e suite
  (`e2e/test_editor_panes.py`, `e2e/test_editor_photo_control.py`) against the dev stack, and by
  the full unit/API/e2e gates recorded in `docs/STATUS.md` before this deploy — not repeated
  against production data or a production login.

## Rollback
- Command / steps: in Portainer → Stacks → `portfolio`, re-deploy pinned to the previous
  known-good tag, `sha-fb72a75` (I8's build, the tag live before this deploy), instead of
  `latest` — same `PUT /api/stacks/1` shape, with `IMAGE_TAG=sha-fb72a75` in the env instead of
  unset/`latest`, then `PullImage: true`. No database rollback needed: this deploy carries no
  migration, so the schema is unchanged and the prior image runs against it without any
  version-skew concern.
- Verified before deploy: no — stated and reasoned about (no schema change, same mechanism as the
  forward deploy), not rehearsed live, consistent with how prior deploys in this project have
  handled an additive-or-absent migration.

## Notes
- `docs/STATUS.md`'s "Resume here" carries the same facts in narrative form; this file is the
  structured record `deploy-product` asks for.
- The Portainer API key and the TrueNAS API key both live in `.env.truenas`, untracked and
  separate from this repo's own `.env` — the owner pointed to it directly for this deploy since
  no MCP tool or stored credential in this session's environment reached Portainer otherwise.
