---
name: pause
description: >-
  Ends a working session cleanly so the next one can resume without guesswork.
  Stops new work, brings the tree to a stable state, verifies the suite, commits,
  and rewrites the handoff in docs/STATUS.md. Use when the user says they are
  stopping for now — "пауза", "на сегодня всё", "останавливаемся", /pause.
---

# Pause

## Goal

The next session must be able to start from `docs/STATUS.md` alone and be right. Not a summary of
this chat — a description of the tree as it actually is.

**Start no new work.** No refactors, no "quick fixes", no opportunistic cleanup. If something is
broken, it gets written down, not fixed. The only work allowed here is closing out what is already
open.

## Workflow

### 1. Close what is open

Look at what is in flight — edits, background commands, subagents.

- Half-finished edit that leaves the code non-working: finish it if that is minutes, otherwise
  `git restore` it and say so in the notes. Never leave the tree in a state that does not run.
- Background commands and subagents: let them finish or stop them. Report anything still running.
- Never leave a half-applied migration or a half-written test file unmentioned.

### 2. Verify — do not trust the checkboxes

```
docker compose run --rm tests
```

Never pipe it through `tail`/`head` — you get the pipe's exit code and a red suite reads as green.

The e2e suite runs on the host against `make up`, not in that container (`tests` mounts only
`tests/`): `uv run pytest e2e/`. If it is too slow to re-run at this hour, do not invent a result —
recover the last one from `.pytest_cache/v/cache/{lastfailed,nodeids}` and label it with that run's
timestamp.

A red suite is a fine way to end a session. A red suite recorded as green is not.

### 3. Commit

Never commit to `main`. Branch as `session/<YYYY-MM-DD>-<slug>` if not already on one.

Split by intent, not by directory — fixes, new tests, docs/evidence are separate commits. The
message says *why*, and names the defect. Do not push unless asked.

If the suite is red, still commit — but say so in the commit body.

### 4. Rewrite the handoff

`docs/STATUS.md`, in this order:

- **`## Resume here`** at the top, rewritten (not appended to). It carries: branch and whether the
  tree is clean; where the work stands in one line; **the next three actions in order**, each
  concrete enough to start without re-reading the code; and any decision that is waiting on the
  owner, marked as theirs.
- **`## Test report`** — every suite, with its own last-run timestamp and command. Name the failing
  tests individually.
- **`## Notes`** — append dated entries for what this session learned. Root causes and traps, not a
  diary of actions. A defect worth a note is one that would cost the next session an hour.

Then `docs/TASKS.md`: tick only what its DoD actually meets, and write the open half of a partly
done task into the task line itself.

### Rotate before you append

`STATUS.md` is the one file every session reads in full, and `## Notes` only grows. An append-only
handoff eventually costs more to read than it saves. Hold the file to **≤150 lines**, and when the
append would break that, rotate before writing:

- `## Resume here` — **≤40 lines.** Rewritten each time, never appended to. It describes the tree as
  it is now; last session's version has no historical value. Being over the line means the next
  actions are carrying explanation that belongs in `## Notes`, not that the cap is wrong.
- `## Notes` — keep entries from the **current milestone only**. Older ones move by kind: a trap or
  root cause to `docs/notes/<YYYY-MM>.md`, a choice with a rationale to `docs/DECISIONS.md`. Neither
  is read on resume, and both stay greppable.
- `## Test report` — one entry per suite, current run only. A superseded run is noise.

Rotation is a move, not a delete: nothing is dropped, it just stops being loaded on every resume.
Leave a one-line pointer to the archive file so the next session knows the history exists.

**Promote before you archive.** Read each entry on its way out and ask whether it is history or a
live trap. A trap that will bite the *next* person to touch that code belongs in
`docs/CONVENTIONS.md`, which every code-touching agent reads — the archive is only for the record of
how the project got here. Getting this backwards is the one way rotation can actually cost
something: the entry is still greppable, but nobody knows to grep for a trap they have not hit yet.

Re-read what you wrote against the tree. A "Resume here" that says the tree is dirty after you
committed it is worse than no handoff.

### 5. Report

Four or five lines to the user, in Russian: suite result, what was committed and on which branch,
the single most important thing to pick up next, and anything left running (containers, background
tasks). No wrap-up prose.

## Rules

- Read `docs/STATUS.md` before writing it. Do not summarise the chat — audit the tree.
- Prefer Serena's symbol tools over whole-file reads; at pause time there is no reason to burn
  context re-reading source.
- If the session ended mid-task, that is the single most important fact in the handoff. Lead with
  it.
