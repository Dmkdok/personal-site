---
name: elicit-requirements
description: >-
  Interrogates the user to build a sharp product brief before any coding.
  Use during discovery, requirements gathering, or when orchestrate-product
  Phase 1 runs. Speaks Russian to the user; writes English brief artifacts.
---

# Elicit Requirements

## Goal

Turn a vague request into `docs/BRIEF.md` that meets Definition of Ready.

## Language

- Chat with user: **Russian**
- `docs/BRIEF.md`: **English** (optional short `docs/BRIEF.ru.md`)

## Method

1. Skim any existing `docs/` and repo files.
2. Ask **one batch** of 5–8 questions (see orchestrate-product `references/question-banks.md`).
3. Reflect answers back in a short Russian summary; confirm misunderstandings.
4. Ask the next batch only for gaps.
5. When DoR is met, write `docs/BRIEF.md` from the template and stop for spec phase.

## Rules

- Do not propose full architecture yet — only capture constraints that affect elicitation.
- Do not write application code.
- Challenge contradictions politely (e.g. "MVP in 2 days" + "custom auth + payments + admin").
- Prefer links and examples over abstract adjectives ("modern", "красивый").

## BRIEF.md must include

- One-sentence pitch
- Problem / job-to-be-done
- Primary user
- Goals & success metrics
- In scope / out of scope
- Constraints & integrations
- Brand & content notes
- Acceptance bar (user's words)
- Open questions (if any remain — ideally empty)
