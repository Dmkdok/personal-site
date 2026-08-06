/**
 * Drag ordering for album cards and for photos inside an album.
 *
 * Containers opt in with `data-sortable`; each child carries `data-sort-id`.
 * Because every mutation swaps its surface back in, initialisation has to run
 * again after each htmx swap — the flag on the container keeps that idempotent
 * for nodes that survived the swap.
 *
 * Dragging is the shortcut, not the only route: the same reordering is
 * reachable from the ↑/↓ buttons on every card and tile.
 */
(function () {
  "use strict";

  if (!window.Sortable) return;

  var dragging = false;

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function orderOf(list) {
    return Array.prototype.slice
      .call(list.querySelectorAll("[data-sort-id]"))
      .map(function (item) {
        return item.getAttribute("data-sort-id");
      })
      .join(",");
  }

  function submit(list) {
    var holder = list.closest("[data-order-url]") || list;
    var url = holder.getAttribute("data-order-url");
    if (!url || !window.htmx) return;

    window.htmx.ajax("POST", url, {
      source: list,
      target: list.getAttribute("data-sortable") === "photo" ? "#photo-grid" : "#album-board",
      swap: "outerHTML",
      values: { order: orderOf(list) }
    });
  }

  function init(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var lists = Array.prototype.slice.call(scope.querySelectorAll("[data-sortable]"));

    lists.forEach(function (list) {
      if (list.dataset.sortableReady === "1") return;
      list.dataset.sortableReady = "1";

      window.Sortable.create(list, {
        handle: "[data-drag-handle]",
        draggable: "[data-sort-id]",
        animation: reducedMotion() ? 0 : 150,
        ghostClass: "photo-drag-ghost",
        chosenClass: "photo-drag-chosen",
        onStart: function () {
          dragging = true;
        },
        onEnd: function (event) {
          dragging = false;
          if (event.oldIndex === event.newIndex) return;
          submit(list);
        }
      });
    });
  }

  // The grid polls itself while photos are still processing. Swapping it out
  // from under a drag would drop the photo the owner is holding.
  document.body.addEventListener("htmx:beforeRequest", function (event) {
    var target = event.detail && event.detail.elt;
    if (dragging && target && target.id === "photo-grid") {
      event.preventDefault();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.body.addEventListener("htmx:afterSettle", function () {
    init(document);
  });

  // `defer` can still land after DOMContentLoaded on a cached page.
  if (document.readyState !== "loading") init(document);
})();
