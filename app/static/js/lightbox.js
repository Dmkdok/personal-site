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
  var announcer = null;
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

    // The picture, the caption and the counter all change on ←/→ while focus
    // stays on the same button, so nothing in the dialog is re-read. This is
    // the only thing that tells a screen-reader user the sheet moved.
    announcer = document.createElement("p");
    announcer.className = "visually-hidden";
    announcer.setAttribute("aria-live", "polite");
    announcer.setAttribute("aria-atomic", "true");

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
    overlay.appendChild(announcer);
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

  /**
   * The width the picture will really occupy, so `sizes` is not a lie.
   *
   * It is fitted inside the figure's box, and on anything taller than it is
   * wide the height is what bites. The old value was a flat `100vw`, which
   * overstates that by up to three times on a portrait shot — which is how a
   * 2560 px rendition came to be drawn 553 px wide.
   */
  function renderedWidth(width, height) {
    var box = image.parentNode.getBoundingClientRect();
    var available = box.width || window.innerWidth;
    var tall = box.height || window.innerHeight;
    if (!width || !height) return Math.round(available);
    return Math.round(Math.min(available, (tall * width) / height));
  }

  function show(next) {
    if (!slides.length) return;
    // Wrapping keeps both arrows meaningful at either end of the sheet.
    index = (next + slides.length) % slides.length;

    var slide = slides[index];
    var width = parseInt(slide.getAttribute("data-width"), 10) || 0;
    var height = parseInt(slide.getAttribute("data-height"), 10) || 0;

    // Order matters: the browser picks a candidate against whatever `sizes`
    // says at the moment `srcset` is assigned.
    image.sizes = renderedWidth(width, height) + "px";
    image.srcset = slide.getAttribute("data-srcset") || "";
    image.src = slide.getAttribute("data-src") || slide.href;
    // The originals' dimensions, kept for their aspect ratio alone: they hold
    // the box steady while a larger rendition loads. CSS caps the drawn size.
    image.width = width;
    image.height = height;
    image.alt = slide.getAttribute("data-alt") || "";

    var text = slide.getAttribute("data-caption") || "";
    caption.textContent = text;
    caption.hidden = !text;

    counter.textContent = strings.position
      .replace("{index}", String(index + 1))
      .replace("{total}", String(slides.length));
    counter.hidden = slides.length < 2;

    // Position first: where you are matters more than what you are looking at
    // when you have pressed an arrow, and `alt` is what describes the picture.
    announcer.textContent = [counter.textContent, image.alt, text]
      .filter(Boolean)
      .join(". ");

    preload(index + 1);
    preload(index - 1);
  }

  /**
   * Warm the neighbour — the *same* candidate the lightbox will pick when it
   * gets there. Fetching `data-src` outright warmed the largest rendition
   * instead, and the browser is entitled to reuse a cached larger candidate
   * rather than fetch the right one: a 2560 px file was being downloaded to be
   * drawn 323 px wide on a phone.
   */
  function preload(at) {
    if (slides.length < 2) return;
    var slide = slides[(at + slides.length) % slides.length];
    var width = parseInt(slide.getAttribute("data-width"), 10) || 0;
    var height = parseInt(slide.getAttribute("data-height"), 10) || 0;

    var ahead = new Image();
    ahead.sizes = renderedWidth(width, height) + "px";
    ahead.srcset = slide.getAttribute("data-srcset") || "";
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

    // Laid out before the first `show`, so `renderedWidth` has a real box to
    // measure instead of the zeroes a `hidden` element reports. The fade still
    // starts from the `--open` class a frame later, so nothing flashes.
    lockScroll();
    overlay.hidden = false;

    show(slides.indexOf(link));
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
