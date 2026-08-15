# Iteration I3 — Operations

Branch `iteration/I3-operations`, cut from `8c75582` (the I2 close) on 2026-08-15.

The theme is the one the roadmap gives it: **everything that protects what already exists.** No
feature here is visible to a visitor. The site went live on the NAS on 2026-08-13 and has been
running unattended since, with nothing scheduled, nothing watching, and no test standing between a
red suite and the container that serves the photographs.

## Baseline

Recorded in `docs/STATUS.md` under `## Baseline I3`. Summary: unit/API **271** exit 0, lint and
format clean over 127 files, e2e **80 passed + 1 error** on the first run and **81 passed** exit 0
on the second — *the same code, twenty minutes apart*.

**The baseline is not green.** The intermittent error is an inherited defect in the deduplication
upload path, described below and taken as T125. It is not a regression from I2: that iteration's
hunks in `images.py` are HEIC only, and its hunks in `photos.py` stop 130 lines above the upload
route. The code involved is M9's, from 2026-08-08.

## Intake

Source: `docs/ROADMAP.md`, items **R-01**, **R-02**, **R-03**, chosen by the owner on 2026-08-15,
plus one defect found while recording the baseline.

**The delta was cut down once, at the gate, on the owner's instruction.** The first draft was eight
tasks and spent five of them on R-01 — a schedule owned by the repository, a 7/4/6 retention policy,
a self-describing backup set, a restore rehearsal on the server. The owner's answer was that the
site is in test mode on the NAS carrying throwaway photographs, that copying files by hand would
satisfy him, that he was prepared to drop the item outright, and that he would rather have
alternatives solvable with small changes and little code. He also replaced the notifier he had
already declined with something concrete: **the log file sticking out of the container, so he can
open it on disk and see what went wrong.** What follows is the re-cut. Five tasks, two of which
touch application code, and the expensive half of R-01 deferred by ADR-024 rather than built.

**A sixth task, T130, was added after T125 shipped.** Building the fix put the neighbouring code
under a microscope and found a second, quieter way for the same disappearance to strand a
photograph — this time after the render rather than before it. It is written up beside T125's
defect below.

### In

| Item | What it is |
|---|---|
| **T125** | The deduplication race: uploading a photograph can answer 500 |
| **T130** | The same disappearance after the render: a photograph spins instead of failing |
| **R-01** *(smallest form)* | Snapshots the appliance already knows how to take, plus the one command it cannot supply |
| **R-02** | The suite gates the image instead of running beside it |
| **R-03** *(re-shaped)* | The log as a file on disk, bounded; an external check on `/healthz` |

### Out, with reasons

- **The engineered backup** — repository-owned schedule, retention policy, manifest, restore
  rehearsal on the server, and any off-machine push this repository configures. Deferred to the move
  off the NAS, which is also when the photographs stop being disposable. **ADR-024.** R-01 stays
  open in the roadmap; this iteration does not tick it.
- **The 500 / failed-photo notifier, and the Telegram bot.** The owner wants the bot — "when the
  site is on a dedicated server", not on this machine. The log file replaces it for now.
  **ADR-025.**
- **R-04** (a way to make contact besides social networks) — the theme of the roadmap's I3-Reach,
  not of operations. Never requested for this round; listed only because the roadmap entry was
  pasted alongside the three that were.
- **R-15** (performance as a gate) — depends on R-02 existing first, which is what this iteration
  builds. It becomes cheap immediately afterwards and expensive now. **ADR-026.**

### Acceptance, one line per item

- **T125** — a photograph whose stored renditions disappear between the two globs is re-rendered
  and answers 201, never 500. A test fails without the fix.
- **T130** — a photograph whose pipeline raises *after* the render settles at `FAILED` with a
  reason the owner can retry from, not at `PROCESSING` until the next restart. A test fails
  without the fix, one per named window.
- **R-01** — a Periodic Snapshot Task exists on the appliance and has taken a snapshot; a logical
  dump can be produced **on the server** by one pasted command, and has been; `docs/HANDOFF.md` §5
  says what each covers and where each falls short.
- **R-02** — a push whose suite is red does not produce a `latest` image.
- **R-03** — the owner opens a file on the NAS share and reads the application's log there; no
  service and no log file can grow without bound; `docs/HANDOFF.md` says how the external check is
  set up and what it watches.

### Non-negotiables

- `scripts/backup.sh` and `scripts/restore-check.sh` keep working **unchanged from a host checkout**
  — that is how they are used in development and how T086's rehearsal was done. The server mode is
  additive.
- **No secret value is ever written into a backup artefact or a log line.** The log file is a new
  destination for output and therefore a new place a secret could land; the review greps for it.
- **A log path is never the reason the site is down.** An unwritable `LOG_DIR` degrades to stdout
  with a warning; it does not raise at startup.
- Nothing in `app/` changes except the two pipeline fixes (T125, T130) and the file handler. This
  iteration is about the outside of the application, not the inside.

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|-------------------|-------|------------------|
| **T125** dedup race | `app/routers/photos.py` → `photo_upload` (known-asset branch), `_assign_renditions`; `app/services/images.py` → `stored_from_asset` | changes none; preserves **F42** (one stored original, no second copy), **F40** (media grouped by owner), ADR-014's ladder guarantee | `tests/api/test_blog.py::test_a_second_upload_of_known_bytes_writes_no_second_original`, `tests/unit/test_photo_pipeline.py::test_a_frame_reused_under_a_richer_profile_gets_the_missing_rungs`, `::test_missing_rungs_names_only_what_is_absent` — all cover the *happy* dedup path; **none covers a hit whose files have gone** | **Local** — one branch of one route plus a two-line guard | New API test patching `images.renditions_of` to answer non-empty once and empty after, reproducing the window between `find_asset` and `stored_from_asset`; asserts 201 + `PENDING`. Watched failing first. The three tests above must pass unchanged. |
| **T130** stuck after the render | `app/routers/photos.py` → `process_photo` (the scope of its existing `try`) | changes none; preserves **F27** (a restart requeues what it caught mid-pipeline) and F42 | `tests/api/test_photo.py::test_a_restart_requeues_a_photo_left_pending`, `::test_a_restart_fails_a_photo_whose_original_is_gone`, `::test_a_failed_photo_can_be_retried`, `::test_the_grid_stops_polling_once_nothing_is_pending` — all cover failures raised *inside* the guard; **none covers one raised after it** | **Local** — the boundary of one `try`, no logic moved | Two tests, one per named window, each patching a step to raise and asserting `FAILED` with a reason rather than a tile that spins. Watched failing first. The four tests above pass unchanged. |
| **R-03a** the log as a file (T126) | `app/config.py` → `Settings` (new `log_dir`); `app/main.py` → module-level logging setup; `.env.example` | adds **F58**; preserves the existing stdout stream and its format exactly — the handler is *added*, never substituted | `tests/unit/` reaches `Settings`; **nothing today asserts anything about logging** | **Cross-cutting policy** — it is two lines of code, but they change where every log line in the application goes | New unit test: with `LOG_DIR` unset nothing is written and the handler set is unchanged; with it set to a temp dir a line reaches `app.log`; with it set to an unwritable path the application **still starts** and warns. Watched failing first. |
| **R-03b** the mount and the ceilings (T126) | `deploy/portainer-stack.yml`, `docker-compose.prod.yml` — one volume plus `logging:` on every service | adds **F60**; preserves every existing mount and the uid-1000 ownership rule the media dataset already follows | none | **Local** config | `docker compose config` renders both files; the rendered output names `max-size` and `max-file` on each service and the log mount on `web`. |
| **R-02** CI gates the image (T127) | `.github/workflows/publish.yml` (new `tests` job + `needs`), plus a generated `.env` step | changes risk 6 at `SPEC.md:247` ("No CI"); adds **F59** | the suite itself; **nothing tests the workflow** | **Contract** — the workflow is the contract between a push and a published tag | Push a deliberately red commit to a scratch branch and watch `publish` not run; then green and watch it publish. Both recorded. |
| **R-01** a dump where the site runs (T128) | `scripts/backup.sh` → one branch on `BACKUP_DB_CONTAINER`; `docs/HANDOFF.md` §5 | changes the Operations bullet at `SPEC.md:198`; adds **F57**; preserves the artefact names and layout `restore-check.sh` parses, and §5's existing restore procedure | **none — no test in this repository executes either shell script** | **Local**, and unverifiable by the suite | Run it both ways: from the host checkout, and against the dev stack by container name. Diff the artefact names against a pre-change run to prove the checkout path is untouched. Then `restore-check.sh` over what it produced. Recorded with output. |
| **R-01** snapshots (T128) | `docs/HANDOFF.md` §5 only — **no code** | adds **F57** | none | **Documentation** | The Periodic Snapshot Task is created on the appliance and has taken a snapshot; the listing is pasted into the close. A documented-but-never-run backup is the exact T073 mistake this project has already paid for once. |
| **R-03c** external `/healthz` check (T129) | `docs/HANDOFF.md` §7 | preserves `/healthz`'s current shape — **the endpoint is not changed** | `tests/api/` covers `/healthz` returning ok | **Documentation** | The check is created on the NAS, and it is verified by *stopping* `web` and seeing the check go red, not by seeing it green. |

### Ordering

1. **T125 first, alone.** It is the red baseline; everything after it is measured against a suite
   that passes twice in a row. *(Done — commit `T125: an upload decides from the same glob it
   assigns from`.)*
2. **T130 next**, while the same code is still in view — it is the neighbouring function in the
   same file, and it was found by reading it.
3. **T126 after both** — the last task that touches `app/`, and it wants a clean suite under it
   before it changes where every log line goes.
4. **T127, T128, T129 are independent** of each other and of everything above. T128 and T129 are
   both partly work on the appliance and are naturally done in one sitting on it.

T125 and T130 touch the same file and neither touches the other's symbol; nothing else overlaps at
all, so nothing has to be merged.

### Tests whose expectations change

**None.** Every row above either adds coverage or touches files the suite does not reach. That is a
meaningful claim in one direction and an uncomfortable one in the other: **three of the six tasks
change shell scripts, deployment configuration and documentation that no automated test in this
repository executes.** Their verification is running them and recording the output, which is why the
acceptance criteria above say "run, not merely written".

## The defect the baseline found

`photo_upload` handles a known set of bytes like this:

```python
known = images.find_asset(db, images.content_digest(data))
if known is not None:
    ...
    if images.missing_rungs(known, images.PHOTO):
        photo.status = PhotoStatus.PENDING          # re-render, go to the pool
    else:
        photo.status = PhotoStatus.READY
        _assign_renditions(photo, images.stored_from_asset(known))
```

`find_asset` already guards the case where the files have gone — it globs the renditions and drops
the row rather than handing back URLs that would 404. `stored_from_asset` then globs **the same
directory a second time**, and `_assign_renditions` indexes the result:

```python
ordered = [stored.derivatives[width] for width in sorted(stored.derivatives)]
photo.thumb_path = ordered[0]
```

Between those two globs the files can be deleted — by a concurrent album deletion calling
`images.release`, or by `scripts/media_orphans.py --prune`. The list is empty, `ordered[0]` raises
`IndexError`, and the request answers **500 with an HTML body** to a client that is parsing JSON.

Two things make it worth fixing rather than recording:

- **The function's own docstring states the invariant it does not check** — "Every case still has
  to leave a servable thumbnail."
- **The recovery already exists.** `missing_rungs` returning a non-empty tuple sends the upload to
  the background pool, which is exactly the right answer when the renditions are absent. The empty
  case should reach it too, instead of falling into the branch that assumes they are present.

**Fixed.** The branch is now chosen from the same `StoredImage` that gets assigned, so the decision
and the assignment cannot read two different directories; an empty ladder falls in with the
incomplete one and goes to the pool. `_assign_renditions` refuses an empty description by name
rather than reaching `ordered[0]`. The test empties the disk the instant the ladder is judged
complete — the only window that actually crashes — and was watched failing with the recorded
traceback first.

## The second one, found while fixing the first

`process_photo` sets `PROCESSING` and **commits** before its `try`, then runs four more steps
*outside* it:

```python
photo.status = PhotoStatus.PROCESSING
db.add(photo); db.commit()          # ← the row is now in-flight, on disk

try:
    stored = images.generate_derivatives(...)
except ...:
    _fail(db, photo, ...); return   # ← the only reported failure

_assign_renditions(photo, stored)                       # can raise (T125 named it)
images.record_asset(db, images.file_digest(...), stored) # can raise FileNotFoundError
db.commit()
```

A raise in any of the last three is caught by `submit_with_session`, which rolls back and logs —
but the rollback cannot undo a commit that already happened, so the row stays `PROCESSING`. The
owner is offered a retry on `FAILED` only, so what he actually sees is **a tile that spins and a
grid that never stops polling**, until the next restart, on a site whose whole premise this
iteration is that it runs unattended for weeks.

Two live windows, and both are the same disappearance T125 was about:

- `_assign_renditions` raising on an empty description — T125 made that raise *named* rather than
  an `IndexError`; it did not make it impossible.
- `images.file_digest` raising `FileNotFoundError` when the original goes between
  `generate_derivatives` and the digest — the same `images.release` / `--prune` race, one door
  further along.

The fix is scope, not logic: the render-and-record sequence moves inside the guard that already
exists. `recover_stuck_photos` is the backstop that bounds this to "until the next restart" and is
deliberately not touched — the bound *is* the problem. Taken as **T130**.

## Exit criteria

- [x] Two consecutive full e2e runs pass, exit 0 both times — the baseline's own failure mode does
      not recur. *(2026-08-15, after T125: 81 passed exit 0, twice. Re-run at the close after all
      five tasks: **81 passed exit 0, twice again**, 186 s and 187 s.)*
- [x] unit/API at **271 or better**, lint and format clean. *(**277 exit 0** at the close — 271
      baseline, +1 T125, +2 T130, +3 T126. Lint and format clean over 53 files.)*
- [x] No photograph can be left in-flight by a failure the pipeline does not report (T130). *(The
      render-and-record sequence is inside the guard; two tests, one per named window, both watched
      failing on "never left the pipeline" first.)*
- [ ] The owner has opened `app.log` on the NAS share and read a real line out of it, and a grep of
      that file for every value in `.env` finds nothing. **— owner's, needs the appliance.**
      *The grep half was rehearsed locally: a real 178-line `app.log` produced by the API suite
      with `LOG_DIR` set, containing no `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL` or
      `ADMIN_USERNAME`, and nothing credential-shaped. `POSTGRES_PASSWORD` matched only because the
      development value is the word `portfolio`, which is also the logger tag; on the server the
      value is random and the grep means something.*
- [x] `docker compose config` shows a log ceiling on every service in both deployment files.
      *(Both rendered 2026-08-15: `max-size: 10m` / `max-file: "3"` on `db`, `web` and `caddy` in
      each, plus `LOG_DIR: /data/logs` and the `/data/logs` mount on `web`.)*
- [x] A red commit has been observed *not* publishing an image, and a green one publishing.
      *(2026-08-15, on `scratch/t127-proof`, dispatched with `gh workflow run`. Red —
      [run 31895410780](https://github.com/Dmkdok/personal-site/actions/runs/31895410780):
      `tests` **failure**, `publish` **skipped**, `e2e` skipped, no image. Green —
      [run 31895508616](https://github.com/Dmkdok/personal-site/actions/runs/31895508616):
      `tests` **success**, both `publish` matrix jobs **success**, `e2e` correctly skipped because
      the ref is not a `v*` tag. The green run published `ghcr.io/dmkdok/personal-site:sha-0849b46`
      and `…-caddy:sha-0849b46` and **nothing else — `latest` did not move**, because
      `enable={{is_default_branch}}` is false off `main`. Scratch branch deleted afterwards.)*
- [x] `scripts/backup.sh` has been run in both modes, and a restore rehearsed from its output.
      *(2026-08-15. Host checkout and `BACKUP_DB_CONTAINER=dmkdok-portfolio-db-1`, both exit 0,
      artefact names identical to a pre-change run. `restore-check.sh` over the container-mode
      pair: 4 albums, 24 photos, 4 posts, 3 projects, 7 site_content rows, 84 files, PASSED.)*
- [ ] A Periodic Snapshot Task exists on the appliance and has taken at least one snapshot, listed
      here. **— owner's, TrueNAS interface.** *Specified in `docs/HANDOFF.md` §5.*
- [ ] The external `/healthz` check has been seen going red when `web` is stopped.
      **— owner's, TrueNAS interface.** *Specified in `docs/HANDOFF.md` §7.*
- [x] Every deferral in the Intake has an ADR, and **R-01 is left open in `docs/ROADMAP.md`** with a
      note pointing at ADR-024 — this iteration takes its smallest form, it does not close it.
      *(ADR-023…ADR-026 all present; R-01, R-02 and R-03 each carry an `I3` note, and R-01's says
      in as many words not to tick it on the strength of this iteration.)*

## What is left, and why it is not ticked

Three criteria above are open and **all three are the owner's own hands** — two in the TrueNAS
interface, one needing the NAS share. The code and the documentation for all of them are written and
committed; none of them is ticked on that basis. That is deliberate: T073 was ticked once with half
its DoD unmet and the bill arrived in T086.

**T127 was closed on 2026-08-15**, after the gate was watched stopping a red commit and letting a
green one through, on a scratch branch that could not move `latest`. Accordingly **T128 and T129 are
left unticked in `docs/TASKS.md`**, and M15 is not a closed milestone. T125, T126, T127 and T130 are
done and ticked.
