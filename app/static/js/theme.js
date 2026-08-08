/**
 * Theme toggle. The pre-paint script in <head> has already applied the stored
 * theme, so this file only wires up the control and keeps storage in sync.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "theme";
  var root = document.documentElement;

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function current() {
    return root.dataset.theme || systemTheme();
  }

  /**
   * Colour the browser chrome to match the page.
   *
   * Written from the resolved `--bg` rather than from a hex literal, and driven
   * from here rather than from a pair of `media`-scoped metas in the head:
   * those describe what the *system* prefers, which is the wrong answer the
   * moment the visitor picks a theme the system did not.
   */
  function paintChrome() {
    var meta = document.getElementById("theme-color");
    if (!meta) {
      meta = document.createElement("meta");
      meta.id = "theme-color";
      meta.name = "theme-color";
      document.head.appendChild(meta);
    }
    meta.content = getComputedStyle(root).getPropertyValue("--bg").trim();
  }

  function apply(theme) {
    root.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* private mode — the choice simply will not persist */
    }
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(theme === "dark"));
    });
    paintChrome();
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-theme-toggle]");
    if (!button) return;
    apply(current() === "dark" ? "light" : "dark");
  });

  // Follow the OS while the visitor has not made an explicit choice.
  var media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", function () {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      /* ignore */
    }
    if (!stored) delete root.dataset.theme;
    paintChrome();
  });

  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    button.setAttribute("aria-pressed", String(current() === "dark"));
  });
  paintChrome();
})();
