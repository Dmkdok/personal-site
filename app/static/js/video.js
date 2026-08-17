/**
 * The video facade in prose (F63, ADR-035).
 *
 * `app/services/markdown.py` renders a paragraph holding nothing but a link to a
 * supported service as a `<figure class="prose-video">` around a `<button>` that
 * carries the embed URL. This file is the only thing in the product that builds
 * an `<iframe>`: `iframe` is not in the sanitiser's allow-list, so a published
 * page contains none and asks the video host for nothing until a reader presses
 * play. That is the whole point of the facade, and it is what exit criterion 6
 * asserts by watching requests.
 *
 * All user-visible text arrives on data attributes from the server, so nothing
 * Russian is written here.
 *
 * Delegated from the document rather than bound per figure: prose arrives in the
 * editor's preview through htmx too, and a listener bound at load would not see
 * a facade that was swapped in afterwards.
 */
(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var button = event.target.closest(".prose-video__play");
    if (!button) return;

    var src = button.getAttribute("data-video");
    if (!src) return;

    var frame = document.createElement("iframe");
    frame.className = "prose-video__frame";
    frame.setAttribute("src", src);
    frame.setAttribute("title", button.getAttribute("data-title") || "");
    frame.setAttribute("allow", "autoplay; fullscreen; encrypted-media; picture-in-picture");
    frame.setAttribute("allowfullscreen", "");
    frame.setAttribute("loading", "lazy");

    button.replaceWith(frame);

    // The button the caret was on has just left the document, so without this
    // the focus falls to <body> and the next Tab restarts at the skip link
    // (F-002). An iframe is focusable, and it is also the thing the reader now
    // wants their keyboard pointed at.
    frame.focus();
  });
})();
