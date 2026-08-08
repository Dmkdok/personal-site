/**
 * Shared UI behaviour: save feedback, htmx error handling and focus.
 *
 * Every admin action reports its outcome — a save that silently does nothing is
 * the failure mode that loses work. Every message it shows comes from the
 * catalogue through data attributes on the toast host, because the CSP forbids
 * an inline script and a Russian string in a .js file is a string nobody can
 * find (ADR-007).
 */
(function () {
  "use strict";

  var host = document.getElementById("toasts");
  var text = (host && host.dataset) || {};

  function toast(message, kind) {
    if (!host || !message) return;
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

  /**
   * Put a fresh CSRF token on <body> and hand it back.
   *
   * The token lives in the session, and a session that was replaced — a login
   * in another tab, a restart — leaves the page holding one the server no
   * longer recognises. Asking for the current one costs a GET; telling the
   * owner to reload costs whatever they had typed (SPEC edge case 5).
   */
  function refreshCsrf() {
    return fetch("/csrf", { credentials: "same-origin" })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (data) {
        if (!data || !data.token) return null;
        document.body.setAttribute(
          "hx-headers",
          JSON.stringify({ "X-CSRF-Token": data.token })
        );
        return data.token;
      })
      .catch(function () {
        return null;
      });
  }

  document.body.addEventListener("htmx:responseError", function (event) {
    var detail = event.detail;
    var status = detail.xhr.status;
    var config = detail.requestConfig || {};
    var source = config.elt || detail.elt;

    // A stale token is worth one silent retry. `data-csrf-retried` keeps that
    // to one attempt per element: a genuinely forbidden request must surface
    // rather than loop.
    if (status === 403 && source && !source.dataset.csrfRetried) {
      source.dataset.csrfRetried = "1";
      refreshCsrf().then(function (token) {
        if (!token) {
          toast(text.msgStale, "error");
          return;
        }
        window.htmx.ajax(config.verb, config.path, {
          source: source,
          values: config.parameters,
          headers: { "X-CSRF-Token": token },
        });
      });
      return;
    }

    if (status === 401) {
      toast(text.msgExpired, "error");
      return;
    }
    if (status === 403) {
      toast(text.msgStale, "error");
      return;
    }
    toast((text.msgFailed || "").replace("{status}", status), "error");
  });

  document.body.addEventListener("htmx:afterRequest", function (event) {
    // One retry per *episode*, not per page: a later 403 on the same button
    // deserves its own attempt.
    var source = (event.detail.requestConfig || {}).elt;
    if (source && source.dataset && event.detail.successful) {
      delete source.dataset.csrfRetried;
    }
  });

  // A rejected save comes back as a re-rendered form with status 200, so
  // htmx:responseError never fires. The swap then destroys the submit button
  // and focus falls to <body> — for the footer form, that is the very bottom
  // of the page. Put the caret on the field that caused it instead, or on
  // whatever the fragment nominated.
  document.body.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (!target || !target.querySelector) return;

    var invalid =
      (target.matches && target.matches("[aria-invalid='true']") && target) ||
      target.querySelector("[aria-invalid='true']");
    if (invalid) invalid.focus();
  });

  /**
   * Honour `data-autofocus` on freshly swapped markup.
   *
   * `autofocus` itself is only guaranteed when the element is parsed as part of
   * the document; the HTML spec lets a browser ignore it on anything inserted
   * afterwards, which is every htmx swap.
   *
   * On `afterSettle`, not `afterSwap`: htmx restores focus by id during the
   * swap, and when the fragment carries the same id as the control that
   * triggered it — «Новая статья» is a button and a form both called
   * `blog-new` — that restoration lands on the wrapper and takes the caret
   * straight back off the field.
   */
  document.body.addEventListener("htmx:afterSettle", function (event) {
    // `event.target` rather than `event.detail.target`: htmx dispatches settle
    // on the swapped element itself and does not put it in the detail, so
    // reading the detail here finds nothing to focus.
    var target = (event.detail && event.detail.target) || event.target;
    if (!target || !target.querySelector) return;
    if (target.querySelector("[aria-invalid='true']")) return;

    var wanted =
      (target.matches && target.matches("[data-autofocus]") && target) ||
      target.querySelector("[data-autofocus]");
    if (wanted && wanted !== document.activeElement) wanted.focus();
  });

  document.body.addEventListener("htmx:sendError", function () {
    toast(text.msgOffline, "error");
  });
})();
