/**
 * The capsule's two disclosures: the mobile links, and the owner's menu.
 *
 * Both are a button and a panel it hides, and both close the same three ways —
 * the button again, Escape, a click outside — so they share one implementation
 * rather than two that drift. The owner's menu exists only in a signed-in
 * document; this file is served to everyone, and does nothing when it is absent.
 */
(function () {
  "use strict";

  /* Every disclosure on the capsule. Both panels hang from the same box and
     would sit on top of each other below 768 px, so opening one closes the
     other — a stacking order is not an answer to two panels in one place. */
  var registry = [];

  function closeOthers(keep) {
    registry.forEach(function (entry) {
      // Only the ones that are a disclosure at this width: on the desktop the
      // links are the row itself, and closing them would empty the capsule.
      if (entry.panel !== keep && entry.live()) entry.close(false);
    });
  }

  /**
   * @param {HTMLElement} toggle  the button that owns `aria-expanded`
   * @param {HTMLElement} panel   the element it hides
   * @param {function(): boolean} [enabled]  when the disclosure is live at all
   *
   * `aria-expanded` on the button *is* the state: every path reads it back off
   * the DOM instead of a variable, which is the mistake F-019 was.
   */
  function disclosure(toggle, panel, enabled) {
    function live() {
      return !enabled || enabled();
    }

    function isOpen() {
      return toggle.getAttribute("aria-expanded") === "true";
    }

    function close(restoreFocus) {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      // F-002: an action leaves the caret on a control. Escape closes the panel
      // the caret was inside, so without this the next Tab restarts from the
      // skip link at the top of the document.
      if (restoreFocus) toggle.focus();
    }

    function open() {
      closeOthers(panel);
      panel.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
    }

    registry.push({ panel: panel, close: close, live: live });

    toggle.addEventListener("click", function () {
      if (isOpen()) {
        close(false);
      } else {
        open();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape" || !isOpen() || !live()) return;
      close(true);
    });

    // The pointer moved the caret itself, so this one does not restore it.
    document.addEventListener("click", function (event) {
      if (!isOpen() || !live()) return;
      if (panel.contains(event.target) || toggle.contains(event.target)) return;
      close(false);
    });

    return { open: open, close: close };
  }

  /* --- The links, which are a dropdown only below 768 px -------------------- */
  var navToggle = document.querySelector("[data-nav-toggle]");
  var navLinks = document.getElementById("nav-links");

  if (navToggle && navLinks) {
    var mobile = window.matchMedia("(max-width: 767px)");
    var links = disclosure(navToggle, navLinks, function () {
      return mobile.matches;
    });

    var sync = function () {
      if (mobile.matches) {
        links.close(false);
      } else {
        // Wide enough for the row: the links are simply the row, and the button
        // that would collapse them is not rendered.
        navLinks.hidden = false;
        navToggle.setAttribute("aria-expanded", "false");
      }
    };

    mobile.addEventListener("change", sync);
    sync();
  }

  /* --- The owner's menu, at every width ------------------------------------ */
  var ownerToggle = document.querySelector("[data-owner-menu-toggle]");
  var ownerPanel = document.getElementById("owner-menu");

  if (ownerToggle && ownerPanel) {
    disclosure(ownerToggle, ownerPanel);
  }
})();
