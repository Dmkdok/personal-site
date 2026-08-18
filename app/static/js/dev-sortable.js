/**
 * Drag-to-reorder for the project list.
 *
 * The board is replaced wholesale after every mutation, so the list has to be
 * re-initialised after each htmx swap rather than once on load. Dragging is an
 * enhancement — the move up/down buttons do the same job from the keyboard.
 *
 * The handle is `[data-drag-handle]`, the hook `photo-sortable.js` already uses,
 * and it sits inside `owner-only`. That is what keeps the board still in
 * «Просмотр»: the script does not read the mode, the marker takes the handle's
 * box away, and Sortable has nothing to start from (F55, ADR-032).
 */
(function () {
  "use strict";

  function init() {
    var list = document.getElementById("project-list");
    if (!list || list.dataset.sortable === "on") return;
    if (typeof window.Sortable === "undefined") return;

    list.dataset.sortable = "on";

    window.Sortable.create(list, {
      animation: 150,
      handle: "[data-drag-handle]",
      draggable: ".project",
      ghostClass: "project--ghost",
      chosenClass: "project--chosen",
      // Dragging text or clicking a control should not start a drag.
      filter: "a, button, input, textarea, label",
      preventOnFilter: false,
      onEnd: function () {
        var ids = Array.prototype.map.call(
          list.querySelectorAll("[data-project-id]"),
          function (node) {
            return node.dataset.projectId;
          }
        );

        window.htmx.ajax("POST", "/dev/admin/order", {
          target: "#project-board",
          swap: "outerHTML",
          values: { order: ids.join(",") },
        });
      },
    });
  }

  document.addEventListener("DOMContentLoaded", init);
  document.body.addEventListener("htmx:afterSwap", init);
})();
