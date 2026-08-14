/**
 * «Показать правки» — reveal every in-place edit affordance at once.
 *
 * Each one appears on hover, which is the right resting state for a page that
 * is also the published page, and no use at all for finding an affordance you
 * did not know was there (UI-AUDIT F-018). The class goes on <html>, the
 * stylesheet does the rest, and the choice is remembered the way the theme is —
 * the pre-paint script in base.html has already applied it, so this file only
 * wires the control and keeps storage and `aria-pressed` in step.
 *
 * Loaded only for a signed-in admin: the markup it operates on does not exist
 * in a visitor's HTML.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "show-edits";
  var CLASS = "show-edits";
  var root = document.documentElement;

  function shown() {
    return root.classList.contains(CLASS);
  }

  function apply(on) {
    root.classList.toggle(CLASS, on);
    try {
      if (on) {
        localStorage.setItem(STORAGE_KEY, "1");
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {
      /* private mode — the choice simply will not persist */
    }
    sync();
  }

  /**
   * Read the state off the page rather than off a variable.
   *
   * F-019 was a control whose `aria-pressed` was written once and then drifted
   * from what it described. Every path here — the click, the initial pass, an
   * htmx swap that brings a new admin bar — ends in the same read.
   */
  function sync() {
    var pressed = String(shown());
    document.querySelectorAll("[data-edits-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", pressed);
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-edits-toggle]");
    if (!button) return;
    apply(!shown());
  });

  document.body.addEventListener("htmx:afterSettle", sync);

  sync();
})();
