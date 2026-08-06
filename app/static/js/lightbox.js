/**
 * Lightbox for the album contact sheet.
 *
 * Progressive enhancement: without JavaScript every thumbnail is a plain link
 * to its largest rendition, so the album still works. With it, the photograph
 * opens over a dimmed, blurred field, arrows and ←/→ move between shots, Esc
 * or a click on the backdrop closes, focus is trapped while it is open and
 * handed back to the thumbnail that opened it.
 *
 * All user-visible text arrives on data attributes from the grid, so nothing
 * Russian is written here.
 */
(function () {
  "use strict";

  var overlay = null;
  var image = null;
  var caption = null;
  var counter = null;
  var closeButton = null;
  var prevButton = null;
  var nextButton = null;

  var slides = [];
  var index = 0;
  var trigger = null;
  var strings = {};

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function build() {
    if (overlay) return;

    overlay = document.createElement("div");
    overlay.className = "lightbox";
    overlay.id = "lightbox";
    overlay.hidden = true;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    var backdrop = document.createElement("div");
    backdrop.className = "lightbox__backdrop";
    backdrop.addEventListener("click", close);

    var figure = document.createElement("figure");
    figure.className = "lightbox__figure";

    image = document.createElement("img");
    image.className = "lightbox__img";
    image.decoding = "async";

    caption = document.createElement("figcaption");
    caption.className = "lightbox__caption";

    figure.appendChild(image);
    figure.appendChild(caption);

    counter = document.createElement("p");
    counter.className = "lightbox__counter";

    closeButton = control("lightbox__close", "✕", close);
    prevButton = control("lightbox__prev", "←", function () {
      show(index - 1);
    });
    nextButton = control("lightbox__next", "→", function () {
      show(index + 1);
    });

    overlay.appendChild(backdrop);
    overlay.appendChild(figure);
    overlay.appendChild(counter);
    overlay.appendChild(prevButton);
    overlay.appendChild(nextButton);
    overlay.appendChild(closeButton);

    document.body.appendChild(overlay);
  }

  /** A control carries its glyph for sighted use and its label for the rest. */
  function control(className, glyph, onClick) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "lightbox__control " + className;

    var icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = glyph;

    var label = document.createElement("span");
    label.className = "visually-hidden";

    button.appendChild(icon);
    button.appendChild(label);
    button.addEventListener("click", onClick);
    return button;
  }

  function readStrings(grid) {
    return {
      label: grid.getAttribute("data-lightbox-label") || "",
      prev: grid.getAttribute("data-lightbox-prev") || "",
      next: grid.getAttribute("data-lightbox-next") || "",
      close: grid.getAttribute("data-lightbox-close") || "",
      position: grid.getAttribute("data-lightbox-position") || "{index} / {total}"
    };
  }

  function show(next) {
    if (!slides.length) return;
    // Wrapping keeps both arrows meaningful at either end of the sheet.
    index = (next + slides.length) % slides.length;

    var slide = slides[index];
    image.src = slide.getAttribute("data-src") || slide.href;
    image.srcset = slide.getAttribute("data-srcset") || "";
    image.sizes = "100vw";
    image.width = parseInt(slide.getAttribute("data-width"), 10) || 0;
    image.height = parseInt(slide.getAttribute("data-height"), 10) || 0;
    image.alt = slide.getAttribute("data-alt") || "";

    var text = slide.getAttribute("data-caption") || "";
    caption.textContent = text;
    caption.hidden = !text;

    counter.textContent = strings.position
      .replace("{index}", String(index + 1))
      .replace("{total}", String(slides.length));
    counter.hidden = slides.length < 2;

    preload(index + 1);
    preload(index - 1);
  }

  function preload(at) {
    if (slides.length < 2) return;
    var slide = slides[(at + slides.length) % slides.length];
    var ahead = new Image();
    ahead.src = slide.getAttribute("data-src") || slide.href;
  }

  function open(link) {
    var grid = link.closest("[data-lightbox-label]");
    if (!grid) return;

    build();
    strings = readStrings(grid);
    slides = Array.prototype.slice.call(grid.querySelectorAll("[data-lightbox]"));
    if (!slides.length) return;

    trigger = link;
    overlay.setAttribute("aria-label", strings.label);
    closeButton.lastChild.textContent = strings.close;
    prevButton.lastChild.textContent = strings.prev;
    nextButton.lastChild.textContent = strings.next;
    closeButton.title = strings.close;
    prevButton.title = strings.prev;
    nextButton.title = strings.next;
    prevButton.disabled = slides.length < 2;
    nextButton.disabled = slides.length < 2;

    show(slides.indexOf(link));

    lockScroll();
    overlay.hidden = false;
    if (reducedMotion()) {
      overlay.classList.add("lightbox--open");
    } else {
      // One frame with the overlay laid out but still transparent, so the
      // fade actually has somewhere to start from.
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          overlay.classList.add("lightbox--open");
        });
      });
    }

    closeButton.focus();
    document.addEventListener("keydown", onKeydown, true);
  }

  function close() {
    if (!overlay || overlay.hidden) return;

    overlay.classList.remove("lightbox--open");
    overlay.hidden = true;
    // Stop the browser holding on to a 2560px frame we are no longer showing.
    image.removeAttribute("src");
    image.removeAttribute("srcset");

    unlockScroll();
    document.removeEventListener("keydown", onKeydown, true);

    if (trigger && document.contains(trigger)) {
      trigger.focus();
    }
    trigger = null;
    slides = [];
  }

  function focusable() {
    return [prevButton, nextButton, closeButton].filter(function (button) {
      return !button.disabled;
    });
  }

  function trapTab(event) {
    var stops = focusable();
    if (!stops.length) return;

    var at = stops.indexOf(document.activeElement);
    var next = event.shiftKey ? at - 1 : at + 1;
    if (at === -1) next = 0;

    event.preventDefault();
    stops[(next + stops.length) % stops.length].focus();
  }

  function onKeydown(event) {
    if (!overlay || overlay.hidden) return;

    switch (event.key) {
      case "Escape":
        event.preventDefault();
        close();
        break;
      case "ArrowLeft":
        event.preventDefault();
        show(index - 1);
        break;
      case "ArrowRight":
        event.preventDefault();
        show(index + 1);
        break;
      case "Home":
        event.preventDefault();
        show(0);
        break;
      case "End":
        event.preventDefault();
        show(slides.length - 1);
        break;
      case "Tab":
        trapTab(event);
        break;
      default:
        break;
    }
  }

  function lockScroll() {
    // Pad by the width the scrollbar gives up, so the page underneath does not
    // jump sideways as it is frozen.
    var gap = window.innerWidth - document.documentElement.clientWidth;
    if (gap > 0) {
      document.body.style.paddingRight = gap + "px";
    }
    document.documentElement.classList.add("is-lightbox-open");
  }

  function unlockScroll() {
    document.documentElement.classList.remove("is-lightbox-open");
    document.body.style.paddingRight = "";
  }

  // Delegated, so thumbnails that arrive with an htmx swap work without re-binding.
  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("[data-lightbox]") : null;
    if (!link) return;
    // Leave the modified clicks alone: opening the file in a new tab is a
    // legitimate thing to want.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
      return;
    }
    event.preventDefault();
    open(link);
  });
})();
