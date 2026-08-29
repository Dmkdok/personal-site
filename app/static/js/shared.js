/**
 * «Скопировать ссылку» (F70).
 *
 * One generic behaviour: any button carrying `data-copy-link` copies the text
 * (or `data-share-url`, when the target has one) of whatever `data-copy-target`
 * points at, and reports the outcome through the same toast every other admin
 * action uses. No Russian lives here — every message arrives on a data
 * attribute written by the template from app/i18n/ru/shared.json.
 */
(function () {
  "use strict";

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // A non-secure context has no Clipboard API: fall back to the legacy
    // command through a hidden, unfocusable field.
    var area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.focus();
    area.select();
    var copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (error) {
      copied = false;
    }
    area.remove();
    return copied ? Promise.resolve() : Promise.reject(new Error("copy failed"));
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy-link]");
    if (!button) return;

    var target = document.querySelector(button.getAttribute("data-copy-target") || "");
    var text = target && (target.getAttribute("data-share-url") || target.textContent.trim());
    if (!text) return;

    copyText(text)
      .then(function () {
        if (window.portfolioToast) {
          window.portfolioToast(button.getAttribute("data-copy-done") || "", "success");
        }
      })
      .catch(function () {
        if (window.portfolioToast) {
          window.portfolioToast(button.getAttribute("data-copy-failed") || "", "error");
        }
      });
  });
})();
