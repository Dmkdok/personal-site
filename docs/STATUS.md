# Status

phase: iteration I5 — implementation (M17 in progress, M16 still open)
approved: true
approved_at: 2026-08-04
i4_delta_approved_at: 2026-08-16
i5_delta_approved_at: 2026-08-17

## Baseline I5

Recorded 2026-08-16 on `iteration/I4-editing-mode` at `5bd408f`, which is where `iteration/I5-authoring`
is cut from. Every command was run in that session, on that tree.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **289 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **92 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **118 files**, exit 0 |

**One inherited finding, not caused by this iteration.** The tree was dirty at the start:
`CLAUDE.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/TASKS.md`, seven skill files,
`.claude/settings.json` and two untracked files — `docs/status-archive.md`, `docs/tasks-archive.md`.
That is the previous session's split of the documents into live work and history. It touches no
application code. **Correction, 2026-08-17:** the intake claimed it was committed before I5 opened;
it was not — it was still uncommitted when this session started, and it went in at the gate
alongside I5's own amendments, so the two are in one commit rather than two.

## Iteration I5 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F55/F38/F62 + F63–F65, ADR-032…037, TASKS M17)
- [x] GATE approved by the owner — «утверждаю», 2026-08-17
- [ ] 4 implementation
- [ ] 5 verification green, baseline suites still green
- [ ] 6 review clean or waived
- [ ] 7 closed (STATUS rewritten, milestone ticked)
```

Intake, impact map and exit criteria: `docs/iterations/I5-authoring.md`. Tasks: `docs/TASKS.md` M17,
**T135–T139**. T135 is the shared-primitive change and lands first, alone.

## Resume here

**I5's delta is approved and M17 is in progress on `iteration/I5-authoring`.** The order is fixed by
the impact map: **T135 first and alone**, then T136–T139 (T139 after T138). Nothing below the next
horizontal rule has been implemented yet; the section after it is I4's record and is still true.

---

**Iteration I4's code is finished. The iteration is not, and M16 is not ticked.** All four tasks are
implemented, tested, reviewed and committed on `iteration/I4-editing-mode` (cut from `main` at
`a0d1ecf`). Nothing is left in I4 that a session can do — **what remains is exit criterion 7, the
owner's own pass through one full publishing flow using only the new menu and the new mode.** No
test stands in for it, and the written-but-never-run tick is the T073 mistake this project already
paid for once in T086.

| | | State |
|---|---|---|
| **T131** | the admin bar retires into the navigation capsule | **done**, `cc403a5` |
| **T134** | `docs/` leaves ruff's discovery, so prose stops being formatted as code | **done**, `1eec8cb` |
| **T132** | «Просмотр» / «Правка» replace hover and the toggle on top of it | **done**, `82a3eef` |
| **T133** | the cabinet at `/me` — one page that says what needs the owner | **done**, `f75d1da` |
| | exit criterion 4: the visitor guard sweeps four pages, not one | **done**, `c5fba5b` |

**Gates on the closing tree, none piped:** unit/API **289** exit 0 (277 at the baseline), e2e **92**
exit 0 (81 at the baseline, 88 after T131), `ruff check` and `ruff format --check` clean over 118
files. Review: **`docs/REVIEW.md` run 6, PASS**, with two Low security findings recorded rather than
fixed and a plain statement that it is a self-review.

**What actually landed, in one paragraph each, is in `docs/iterations/I4-editing-mode.md`** — three
sections, *T131 landed*, *T132 landed* and *T133 landed*, each listing what the plan did not say.
Read those before touching any of this; they are where the reasons live.

**Two things to expect if you carry this forward.**

1. **The impact map undercounts the tests that carry a behaviour change, every time so far.** T131
   owed four more than the map named; T132 owed **seven** more, in three files the map never
   mentioned — every in-place editing flow, all passing until then only because `opacity: 0` is
   clickable. Before starting anything that changes a resting state, grep `e2e/` for locators that
   describe the old behaviour, not just the files the map lists.
2. **A new i18n key needs `docker compose restart web`.** `translate()`'s catalogue is `@lru_cache`d
   per process, and a missing key renders as its own dotted name — which looks exactly like markup
   that failed to render. It cost a debugging round in T131 and was cheap in T132 and T133 because
   it was written down.

**Two lines for the next intake, deliberately not fixed here.** The cabinet's «Снимки без описания»
list is unbounded and its rows are indistinguishable — on the owner's real data it renders 24 rows
all reading «Снимок в альбоме «X»», told apart only by where they lead; that is also the first
evidence for the trigger ADR-029 records, which is photographs at scale. And **ADR-029's own
consequences line is stale**: it says `/me` joins the parametrized admin-read case in
`test_authz_sweep.py`, which it does not and must not — that case asserts redirect-to-login
semantics and this route answers 404 by decision. The impact map said so first; both statements are
in the record and neither was edited away.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite and the lint gate
before it builds anything.

Everything below this line is I3's record and is still true. **T128 and T129 remain open and remain
the owner's** — they are not blocked by I4 and I4 does not touch them.

---

**I3 is merged, pushed and deployed.** `main` = `38456e5`, fast-forwarded from
`iteration/I3-operations` (33 commits) and pushed to `origin`
(`https://github.com/Dmkdok/personal-site.git`). The `publish` run on that push
(`31895713071`) is **the first release in this project's history whose image was gated by a test
run** — `tests` green, then both images built and `latest` moved to `sha-38456e5`.

**The NAS stack is running that image, deployed 2026-08-15 via the Portainer API** (stack `id=1`
`portfolio`, endpoint 3, Portainer 2.44.0 on `https://192.168.1.20:31015`). All three containers
healthy; `https://profile.dmkdok.crazedns.ru:8443` answers 200 on `/`, `/photo`, `/blog`, `/dev`,
and `/healthz` answers 200 on both the LAN and the public address.

The dev stack (`db`, `web`) is up locally; `docker compose down` stops it. Docker Desktop is not
always running on this host — start it and wait for `docker info` before the first suite.

**Two traps this session hit, both cheap to avoid.** A full e2e run started immediately after
`docker compose restart web` fails all 81 at fixture setup, because the site is not answering yet —
wait for `/healthz` first. And Git Bash rewrites container-absolute paths on this host, so
`docker compose run -e LOG_DIR=/tmp/x` arrives inside the container as `C:/Users/...`; prefix the
command with `MSYS_NO_PATHCONV=1`. The same conversion makes `tar` treat a `C:/...` `BACKUP_DIR` as
a remote host and fail — give `scripts/backup.sh` a POSIX-relative path.

**Iteration I3's code is finished. The iteration is not, and M15 is not ticked.** Its page —
intake, the re-cut, the impact map, both pipeline defects and the exit criteria — is
**`docs/iterations/I3-operations.md`**. Milestone **M15** in `docs/TASKS.md`, six tasks:

| | | State |
|---|---|---|
| **T125** | the dedup race: an upload could answer 500 | **done**, `4255ec4` |
| **T130** | a photo failing *after* the render spins instead of failing | **done**, `6867154` |
| **T126** | the log as a file on disk + log ceilings | **done**, `0ec22c1` |
| **T127** | the suite gates the published image | code done `729fce3` — **needs a push to prove** |
| **T128** | a dump that runs on the server + snapshot task | script + docs done `66455ca` — **needs the snapshot task** |
| **T129** | an external check on `/healthz` | docs done `66455ca` — **needs the cron job** |

**Gates at the close (2026-08-15):** unit/API **277** exit 0, e2e **81 passed exit 0 twice
consecutively**, six launch flows 6 passed, lint and format clean over 53 files. The baseline's
intermittent 500 did not recur, and neither did the unexplained login failure recorded below.

**What is left is the owner's and only the owner's — do not tick any of it from a session.**

1. ~~**T127**~~ — **done 2026-08-15.** Proved on `scratch/t127-proof` by dispatch: red run
   `31895410780` → `tests` failure, `publish` skipped, no image; green run `31895508616` → `tests`
   success, both `publish` jobs success, `sha-0849b46` published and `latest` untouched. Branch
   deleted.
2. **T128** — create the Periodic Snapshot Task in the TrueNAS interface. The dataset, schedule and
   retention are specified in `docs/HANDOFF.md` §5; paste the resulting listing into the iteration
   page.
3. **T129** — create the cron job in `docs/HANDOFF.md` §7 and **verify it by stopping `web`**, not
   by watching it go green.
4. ~~**T126's last mile**~~ — **done 2026-08-15.** `app.log` is live on the appliance at
   `/mnt/tank/app_data/_dev_/portfolio/logs`, 1000:1000, carrying the same lines as stdout, and the
   grep against the production stack variables is clean (the only match is the admin *username* in
   `admin account ready: admin`, a line from M2 — not a credential).

   **`logs` is a plain directory, not a dataset, and that was the right call.** A dataset buys
   nothing: the recursive snapshot task on the parent already covers it, `atime=off` is inherited,
   and the application caps the file at 5 MB × 4 itself. The session initially insisted on a dataset
   out of convention, hit TrueNAS refusing to create one over an existing path, and was heading for
   a root cron job to `rmdir` it — the owner's question ("why can't the log write the way the photos
   do?") cut that off. The answer was ownership, never ZFS.

   **The deploy before the chown proved the non-negotiable in production**, which is worth keeping:
   the stack came up with the directory still root-owned and logged

   ```
   WARNING [portfolio] LOG_DIR /data/logs is not usable
   ([Errno 13] Permission denied: '/data/logs/app.log'); logging to stdout only
   ```

   — then migrated, seeded the admin and served 200s. A log path is not the reason the site is down.

**Merging is the owner's call and the consequence is now different from what it was.** A push to
`main` runs `publish`, which since T127 runs the suite and the lint gate first and builds nothing if
they fail. `latest` still follows `main` — but only a green `main`. The sane order is still to prove
T127 on a scratch branch before trusting it.

**Iteration I2 is complete.** `docs/TASKS.md` has no unticked line, M11 through M14. Its page is
**`docs/iterations/I2-pagination-media-phaseb.md`**; the review is run 4 in `docs/REVIEW.md`.

**One intermittent was seen and is not explained.** In one full e2e run of three, the
`admin_storage_state` fixture failed at setup: the login POSTed and answered `303`, and the page it
redirected to came back anonymous — no admin bar, so the session cookie was issued and then not
honoured. It did not recur on the next run, and the same fixture succeeds fifteen-odd times in every
run. Two runs of that batch also had the app restarting underneath them, because a `git stash` cycle
of `app/**` (used to watch a test go red) trips uvicorn's `WatchFiles` reloader — **so do that with
the stack down, or expect `ERR_EMPTY_RESPONSE` in the middle of a suite.** Whether the login failure
was the same disturbance or something in `end_session`'s token rotation is genuinely unknown. It is
the first thing to chase if it shows up again; there is nothing to fix until it does.

**The audit is now half finished, deliberately, and it says so itself.** Phase A (P1) closed in I1;
Phase B (P2) closed in I2, with F-016 closed as not-a-defect by ADR-020. Seven P3 findings
(F-019…F-022, F-024…F-026) remain open, deferred by ADR-017. `docs/UI-AUDIT.md` carries the register
at the top — that is the only edit ever made to it, and the findings below it are untouched.

## Baseline I4

Recorded 2026-08-16 on `iteration/I4-editing-mode`, cut from `main` at `a0d1ecf` (the I3 close,
merged and deployed). Every command below was run in this session, on this tree, none piped.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **277 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **81 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **1 file would be reformatted**, exit 1 |

**Two inherited findings, neither caused by this iteration.**

1. **`.env` was unparseable, so every `docker compose` command failed** — not only the suite:
   `failed to read .env: line 17: key cannot contain a space`, which is a failure of the file's
   parse, so `up`, `logs` and `test` were all dead. The owner had edited the file and fixed it on
   being shown the error; nothing in the repository changed. **If a later session sees Docker
   "broken", read this line before restarting anything** — `docker compose config --quiet` says so
   in one second.
2. **`ruff format --check` is red on `docs/iterations/I3-operations.md`.** I3's baseline recorded
   *"clean, 127 files"*; the count is 128 now and the extra file is the I3 iteration page itself,
   written during I3 after the last format check and never checked. Ruff formats fenced Python
   inside Markdown and wants to rewrite the T125 dedup excerpt, whose aligned trailing comments are
   the explanation. **ADR-030 / T134** takes `docs/` out of ruff's discovery. Nothing else is red.

The intermittent 500 that made I3's baseline amber did not recur.

```text
Iteration I4 progress:
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F36/F55 reworded, F61/F62 added; ADR-027…031; TASKS M16)
- [x] GATE approved by the owner — «утверждаю», 2026-08-16
- [x] 4 implementation — T131, T134, T132, T133, all four ticked
- [x] 5 verification green — unit/API **289** exit 0 (277 at baseline), e2e **92** exit 0 (81),
      lint and format clean over 118 files; exit criterion 4 closed by strengthening the guard
- [x] 6 review — `docs/REVIEW.md` run 6, PASS, two Low security findings recorded not fixed;
      it says plainly that it is a self-review rather than an independent one
- [ ] 7 closed — **M16 cannot be ticked**: exit criterion 7 is the owner's own publishing pass
```

**Both inherited findings are closed.** The `.env` parse was the owner's edit and never touched the
repository; `ruff format --check` is green over the whole tree since T134 took `docs/` out of ruff's
discovery (ADR-030).

## Open problems and bugs, all of them

Ordered by what bites first. Items 1–3 are consequences of this deployment; 4–8 predate it or sit
beside it.

1. **`SITE_URL` advertises `http://192.168.1.20:8080` to the internet.** Canonical, Open Graph,
   `sitemap.xml`. One variable in Portainer, then redeploy. Note the replacement must carry the
   port: `https://profile.dmkdok.crazedns.ru:8443`.
2. **The login throttle is shared by every external visitor** — no `X-Forwarded-For` from the
   router, so everyone is `192.168.1.1`. Five wrong passwords from a stranger lock the owner out
   for 15 minutes, with no LAN fallback because the LAN address is plain HTTP and the cookie is
   `Secure`. Detail above.
3. **No backups are scheduled.** No ZFS snapshot task on `media` or `pgdata`, no `pg_dump` cron.
   Harmless while the site is empty; not harmless the moment content exists. `make backup` does
   not apply here — see `docs/HANDOFF.md` §6.1.
4. **The Cyrillic font is downloaded twice on every cold load.** `base.html` preloads it through
   `static_url`, so the preload URL carries `?v=…`, while the `@font-face` rule asks for the same
   file without a query. The preload never matches, and it is the LCP-critical font. Pre-existing.
5. **CI runs no tests.** `publish.yml` builds and pushes; `latest` follows `main` in whatever state
   `main` is. The local gates are the only gates.
6. **The appliance runs TrueNAS 26.0.0-BETA.2.** A beta OS under a live site. Nothing has
   misbehaved, but it is worth knowing before diagnosing anything strange.
7. **`docs/TASKS.md` has no milestone for any of this work.** The deployment happened outside the
   M-numbering; it is the one place the tree and the checklists disagree.
8. **Credential hygiene, outstanding.** The TrueNAS account password and four tokens were pasted
   into a chat transcript. The classic GHCR PAT is *in use* — it is Portainer's registry credential
   — so it must be replaced in Portainer before being revoked, not after. `Test_Key` in TrueNAS is
   revoked and should be deleted. Full order of operations at the end of this session's notes.

Older functional gaps — article-image CLS, touch-target sizing, two labelling gaps, draft Russian
copy — are unchanged and live in `docs/HANDOFF.md` §8.

**Not a bug, but it will cost time again.** `media`, `pgdata` and `backups` are separate ZFS
datasets, so anything rooted at `portfolio` that does not cross a mount boundary shows them as empty
directories. Two consequences already met: an SMB share must be created on `media` itself, not on
the parent; and the **File Browser app cannot see them at all** — it bind-mounts `/mnt/tank` with
`propagation=rprivate` and has been running since 10 July, so mounts created afterwards never
entered its namespace. Restarting that app fixes it, and will be needed again for every future
dataset, ours or anyone's.

## Test report

Each gate below carries its own last-run timestamp and the command that produced it.

| Gate | Command | Last run | Result |
|---|---|---|---|
| Unit + API | `docker compose run --rm tests` | 2026-08-15, close of I2 | **271 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | 2026-08-15, close of I2 | **81 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | 2026-08-08 | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | 2026-08-15, close of I2 | clean, exit 0 |
| Format | `uv run ruff format --check .` | 2026-08-15, close of I2 | clean, 127 files |

No failing tests. **Iteration I2 grew the suite 233 → 271 and 60 → 81**, against the baseline in
`## Baseline I2` taken before the change request was read. Iteration I1 before it grew 224 → 226 and
40 → 57, and the search-field fix that followed took e2e to 60.

**Only the tests the impact map named were edited**, plus one it did not: `e2e/test_login.py`'s
unscoped `get_by_role("alert")`, which resolves to two elements once the toast host has a permanent
alert region on every page. Everything else new is an addition, and every addition fails without the
change it guards — with one named exception, T112, argued in the iteration doc.

`-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.** Never
pipe a test run through `tail` or `grep`: you get the pipe's status and a red suite reads as green.

**Two traps this machine cost time on, both of which will recur.** The i18n catalogue is behind
`@lru_cache` in `app/templating.py`, so a **newly added translation key does not appear until the web
container restarts** — it surfaces as the raw key (`blog.save_failed`) rendered on the page, and it
cost one confusing red test. `docker compose restart web`, then wait for `/healthz` before running
e2e; a run started against a restarting container fails at the `_site_is_up` fixture with
`RemoteDisconnected`, which looks nothing like the real cause. And `docker compose run --rm tests
<path>` **replaces the command rather than appending to it** — the service's command is
`["python", "-m", "pytest", "-q"]`, so a single file is run as
`docker compose run --rm tests python -m pytest <path>`.

**Nothing is known bad.** Every task in every milestone including M10 is done and ticked; the only
unticked item anywhere is T074, the production deploy, which the owner has chosen to run himself.

## Notes

Dated entries from the session that is current. Everything up to 2026-08-11 is in
`docs/status-archive.md` under "Notes, 2026-08-04 to 2026-08-11"; the traps out of it that are still
load-bearing are recorded where they are needed instead of here — `CLAUDE.md` for the test and
Serena rules, `docs/CONVENTIONS.md` for the rest.

## History

Closed baselines I1, I2 and I3, the 2026-08-13 deployment record and the session notes that came
with them are in `docs/status-archive.md`. The same history in narrative form, one file per
iteration, is in `docs/iterations/`. Neither is needed to resume work: this file is the handoff.

