/**
 * «Просмотр» / «Правка» — the two modes the owner's page has (ADR-028).
 *
 * In «Просмотр» nothing the owner alone has any use for is rendered at all, so
 * the page the owner reads is the page a visitor reads — since I5 that means
 * every block carrying `owner-only`, not the three affordance families I4 gated
 * (ADR-032); in «Правка» all of it is shown permanently and the editable
 * regions are outlined. There is no hover branch
 * and no touch branch left: one class on <html> decides everything, the
 * stylesheets do the rest, and the pre-paint script in base.html has already
 * applied it — so this file only wires the switch and keeps storage and
 * `aria-pressed` in step.
 *
 * The class and the storage key are still called `show-edits`: they mean
 * exactly what they did, and renaming them would move the owner's remembered
 * choice for nothing.
 *
 * Loaded only for a signed-in admin: the markup it operates on does not exist
 * in a visitor's HTML.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "show-edits";
  var CLASS = "show-edits";
  var root = document.documentElement;

  function editing() {
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
   * htmx swap that brings a new menu — ends in the same read, and both halves
   * of the switch are written from it so they cannot disagree.
   */
  function sync() {
    var on = editing();
    document.querySelectorAll("[data-edit-mode]").forEach(function (button) {
      var wants = button.getAttribute("data-edit-mode") === "edit";
      button.setAttribute("aria-pressed", String(wants === on));
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-edit-mode]");
    if (!button) return;
    apply(button.getAttribute("data-edit-mode") === "edit");
  });

  document.body.addEventListener("htmx:afterSettle", sync);

  sync();
})();
