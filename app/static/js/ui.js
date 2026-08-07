/**
 * Shared UI behaviour: save feedback and htmx error handling.
 *
 * Every admin action reports its outcome — a save that silently does nothing is
 * the failure mode that loses work.
 */
(function () {
  "use strict";

  var host = document.getElementById("toasts");

  function toast(message, kind) {
    if (!host) return;
    var el = document.createElement("p");
    el.className = "toast" + (kind ? " toast--" + kind : "");
    el.textContent = message;
    host.appendChild(el);
    window.setTimeout(function () {
      el.remove();
    }, 4000);
  }

  window.portfolioToast = toast;

  // The server signals a message with the HX-Toast response header.
  document.body.addEventListener("htmx:afterOnLoad", function (event) {
    var xhr = event.detail.xhr;
    if (!xhr) return;
    var message = xhr.getResponseHeader("HX-Toast");
    if (!message) return;
    // Header values are latin-1 only, so the server percent-encodes the text.
    try {
      message = decodeURIComponent(message);
    } catch (e) {
      /* fall back to the raw value */
    }
    toast(message, xhr.getResponseHeader("HX-Toast-Kind") || "success");
  });

  document.body.addEventListener("htmx:responseError", function (event) {
    var status = event.detail.xhr.status;
    if (status === 401) {
      toast("Сессия истекла. Откройте /login в новой вкладке, войдите и повторите.", "error");
      return;
    }
    if (status === 403) {
      toast("Страница устарела. Обновите её и повторите.", "error");
      return;
    }
    toast("Не удалось сохранить (ошибка " + status + "). Текст не потерян.", "error");
  });

  // A rejected save comes back as a re-rendered form with status 200, so
  // htmx:responseError never fires. The swap then destroys the submit button
  // and focus falls to <body> — for the footer form, that is the very bottom
  // of the page. Put the caret on the field that caused it instead.
  document.body.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (!target || !target.querySelector) return;
    var invalid =
      (target.matches && target.matches("[aria-invalid='true']") && target) ||
      target.querySelector("[aria-invalid='true']");
    if (invalid) invalid.focus();
  });

  document.body.addEventListener("htmx:sendError", function () {
    toast("Нет связи с сервером. Проверьте соединение и повторите.", "error");
  });
})();
