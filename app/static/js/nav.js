/** Mobile navigation: the capsule keeps its shape, the links drop below it. */
(function () {
  "use strict";

  var toggle = document.querySelector("[data-nav-toggle]");
  var links = document.getElementById("nav-links");
  if (!toggle || !links) return;

  var mobile = window.matchMedia("(max-width: 767px)");

  function close() {
    links.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  function open() {
    links.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
  }

  function sync() {
    if (mobile.matches) {
      close();
    } else {
      links.hidden = false;
      toggle.setAttribute("aria-expanded", "false");
    }
  }

  toggle.addEventListener("click", function () {
    if (toggle.getAttribute("aria-expanded") === "true") {
      close();
    } else {
      open();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
      close();
      toggle.focus();
    }
  });

  document.addEventListener("click", function (event) {
    if (!mobile.matches) return;
    if (toggle.getAttribute("aria-expanded") !== "true") return;
    if (links.contains(event.target) || toggle.contains(event.target)) return;
    close();
  });

  mobile.addEventListener("change", sync);
  sync();
})();
