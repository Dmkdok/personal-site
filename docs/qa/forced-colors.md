# Forced colours — what was checked, on what, and when

UI-AUDIT **F-013**, closed by T114 (iteration I2).

## What the site does now

Three states were expressed only in properties that forced colours discard —
`box-shadow` and `background-color`:

| State | Where | Now also |
|---|---|---|
| Thumbnail hover / focus | `photo.css` `.photo-item__link::after` | `outline: 2px solid Highlight` inset 2 px |
| Photo being dragged | `photo.css` `.photo-drag-chosen` | `outline: 3px solid Highlight` |
| Current section | `components.css` `.nav__link[aria-current="page"]` | `border: 2px solid Highlight` |
| Nav link hover | `components.css` `.nav__link:hover` | `text-decoration: underline` |
| Home entry hover / focus | `components.css` `.entry` | `outline: 2px solid Highlight` inset 2 px |

`Highlight` is a system colour keyword, so each follows whichever contrast theme
is switched on rather than naming a colour of its own.

## Automated pass — done

**When:** 2026-08-15. **On:** Chromium 151 (Playwright), `forced_colors="active"`,
against the dev stack at `http://localhost:8000`.
**How:** `e2e/test_forced_colors.py`, three cases — a thumbnail's hover and focus,
the current section against a section that is not current, and a home entry's
hover. Each reads the computed style off the shipped stylesheet.

**Result:** all three pass. Watched failing first: with the `photo.css` block
removed, a hovered thumbnail reports `outlineStyle: none` — the finding's exact
symptom, an indicator that is not there.

**Artefacts:** `docs/qa/forced-colors.json` (measured values),
`docs/qa/screenshots/forced-colors-photo.jpg` (album page under emulation, with
the first tile focused and «Фото» marked in the capsule).

## Real-theme pass — outstanding, and it is the owner's to do

Chromium's emulation applies the media query and the forced colour adjustments.
It does **not** load a Windows contrast theme's palette, so it cannot show how
the site looks in *Aquatic* or *Desert* specifically, nor catch a place where two
system colours land on top of each other.

To do it, on this machine:

1. Settings → Accessibility → Contrast themes → pick **Aquatic**, Apply.
2. Open Edge at the site, and look at: `/photo/{album}` (hover and Tab through the
   contact sheet), the nav capsule on any page (the current section must stand out
   from the other three), and the home page (hover the three entries).
3. Drag one photograph in an album to check `.photo-drag-chosen`.
4. Turn the theme back off.

Add the result here when it is done, with the theme name and the date.
