/**
 * Batch photo upload.
 *
 * One XMLHttpRequest per file: that is what buys real per-file progress and
 * makes a single rejection a fact about one row rather than about the drop.
 * Uploads run three at a time so a batch of fifty does not open fifty sockets.
 *
 * The CSRF token is read from the `hx-headers` attribute htmx already puts on
 * <body>, so there is exactly one place the token is published.
 *
 * All user-visible text arrives on data attributes from the template.
 */
(function () {
  "use strict";

  var zone = document.getElementById("upload-zone");
  var input = document.getElementById("upload-input");
  var queue = document.getElementById("upload-queue");
  var queueWrap = document.getElementById("upload-queue-wrap");
  var clearButton = document.getElementById("upload-queue-clear");
  var cancelButton = document.getElementById("upload-queue-cancel");
  if (!zone || !input || !queue) return;

  var CONCURRENCY = 3;
  var url = zone.getAttribute("data-upload-url");
  var maxFiles = parseInt(zone.getAttribute("data-max-files"), 10) || 50;
  var maxBytes = parseInt(zone.getAttribute("data-max-bytes"), 10) || 0;
  var accept = (zone.getAttribute("data-accept") || "").split(",").filter(Boolean);

  var text = {
    uploading: zone.getAttribute("data-state-uploading") || "",
    processing: zone.getAttribute("data-state-processing") || "",
    ready: zone.getAttribute("data-state-ready") || "",
    failed: zone.getAttribute("data-state-failed") || "",
    tooMany: zone.getAttribute("data-error-too-many") || "",
    uploadFailed: zone.getAttribute("data-error-upload") || "",
    network: zone.getAttribute("data-error-network") || "",
    cancelled: zone.getAttribute("data-error-cancelled") || "",
    tooBig: zone.getAttribute("data-error-too-big") || "",
    wrongType: zone.getAttribute("data-error-wrong-type") || "",
    retry: zone.getAttribute("data-retry-label") || "",
    progress: zone.getAttribute("data-progress-label") || "",
    summary: zone.getAttribute("data-summary") || "",
    summaryFailed: zone.getAttribute("data-summary-failed") || ""
  };

  var pending = [];
  var inFlight = [];
  var active = 0;
  var rowsByPhoto = {};
  var refreshTimer = null;

  var statusLine = document.getElementById("upload-queue-status");
  var counts = { total: 0, done: 0, failed: 0 };
  var statusTimer = null;

  /** Report progress once a second, as one sentence.
   *
   * The queue list is `aria-live="off"` because it cannot be anything else: a
   * fifty-file drop appends fifty rows and rewrites each of them twice, and a
   * screen reader would read all of it before the page could be used again.
   * This is the same information at a rate a person can follow.
   */
  function announce() {
    if (!statusLine || statusTimer) return;
    statusTimer = window.setTimeout(function () {
      statusTimer = null;
      if (!counts.total) {
        statusLine.textContent = "";
        return;
      }
      var template = counts.failed ? text.summaryFailed : text.summary;
      statusLine.textContent = template
        .replace("{done}", counts.done)
        .replace("{total}", counts.total)
        .replace("{failed}", counts.failed);
    }, 1000);
  }

  function toast(message, kind) {
    if (window.portfolioToast) window.portfolioToast(message, kind);
  }

  function csrfToken() {
    try {
      var headers = JSON.parse(document.body.getAttribute("hx-headers") || "{}");
      return headers["X-CSRF-Token"] || "";
    } catch (error) {
      return "";
    }
  }

  /** Ask the grid to re-read itself; it takes over the processing states. */
  function refreshGrid() {
    if (refreshTimer) return;
    refreshTimer = window.setTimeout(function () {
      refreshTimer = null;
      if (window.htmx) window.htmx.trigger(document.body, "photos-added");
    }, 400);
  }

  // ------------------------------------------------------------------ rows
  function progressBar(file) {
    var bar = document.createElement("progress");
    bar.className = "upload-item__bar";
    bar.max = 100;
    bar.value = 0;
    bar.setAttribute("aria-label", text.progress + " — " + file.name);
    return bar;
  }

  function addRow(file) {
    queueWrap.hidden = false;

    var row = document.createElement("li");
    row.className = "upload-item upload-item--uploading";

    var name = document.createElement("span");
    name.className = "upload-item__name";
    name.textContent = file.name;

    var state = document.createElement("span");
    state.className = "meta upload-item__state";
    state.textContent = text.uploading;

    var bar = progressBar(file);

    row.appendChild(name);
    row.appendChild(state);
    row.appendChild(bar);
    queue.appendChild(row);

    return { root: row, state: state, bar: bar, error: null, retry: null };
  }

  function setState(row, kind, label) {
    row.root.className = "upload-item upload-item--" + kind;
    row.state.textContent = label;
  }

  function setError(row, message) {
    setState(row, "failed", text.failed);
    if (row.bar) {
      row.bar.remove();
      row.bar = null;
    }
    if (!row.error) {
      row.error = document.createElement("p");
      row.error.className = "upload-item__error";
      row.root.appendChild(row.error);
    }
    row.error.textContent = message;
    counts.failed += 1;
    announce();
  }

  /** Offer the row another attempt. The `File` is still held, so nothing is
   *  re-picked; only failures the second attempt could survive get one — a
   *  file refused for its size or its type would fail identically. */
  function addRetry(job) {
    if (job.row.retry) return;

    var button = document.createElement("button");
    button.type = "button";
    button.className = "button button--quiet upload-item__retry";
    button.textContent = text.retry;
    button.addEventListener("click", function () {
      button.remove();
      job.row.retry = null;
      if (job.row.error) {
        job.row.error.remove();
        job.row.error = null;
      }
      counts.failed -= 1;
      job.row.bar = progressBar(job.file);
      job.row.root.appendChild(job.row.bar);
      setState(job.row, "uploading", text.uploading);
      pending.push(job);
      announce();
      pump();
    });

    job.row.retry = button;
    job.row.root.appendChild(button);
  }

  // ------------------------------------------------------------------ queue
  /** Why this file cannot succeed, or "" if it can — checked before sending.
   *
   * The only client-side gate used to be `maxFiles`, plus the input's `accept`
   * — and `accept` does not apply to a drop at all. A 60 MB file, or a TIFF,
   * was uploaded in full and rejected on arrival, after the owner had watched a
   * real progress bar reach 100 %.
   *
   * An empty `file.type` is *not* refused: the browser derives it from the
   * extension, so a JPEG saved without one would be turned away here while the
   * server — which reads the magic bytes — would have taken it. The server is
   * still the authority; this only refuses what it certainly would.
   */
  function rejection(file) {
    if (maxBytes && file.size > maxBytes) {
      return text.tooBig.replace("{limit}", Math.round(maxBytes / (1024 * 1024)));
    }
    if (file.type && accept.length && accept.indexOf(file.type) === -1) return text.wrongType;
    return "";
  }

  function enqueue(files) {
    var list = Array.prototype.slice.call(files);
    if (!list.length) return;

    if (list.length > maxFiles) {
      list = list.slice(0, maxFiles);
      toast(text.tooMany, "error");
    }

    list.forEach(function (file) {
      var job = { file: file, row: addRow(file), request: null };
      var why = rejection(file);
      if (why) {
        // Its own row and its own reason, exactly as a server refusal gets —
        // the counters and the throttled announcement need no special case.
        setError(job.row, why);
        return;
      }
      pending.push(job);
    });
    counts.total += list.length;
    announce();
    pump();
  }

  function pump() {
    while (active < CONCURRENCY && pending.length) {
      active += 1;
      send(pending.shift());
    }
    syncCancel();
  }

  function finished(job) {
    active -= 1;
    var index = inFlight.indexOf(job);
    if (index !== -1) inFlight.splice(index, 1);
    pump();
  }

  /** The stop control exists only while there is something to stop. */
  function syncCancel() {
    if (!cancelButton) return;
    var running = pending.length > 0 || inFlight.length > 0;
    // Hiding the focused control is how focus ends up on <body> (F-002).
    if (!running && document.activeElement === cancelButton) input.focus();
    cancelButton.hidden = !running;
  }

  function send(job) {
    var form = new FormData();
    form.append("file", job.file, job.file.name);

    var request = new XMLHttpRequest();
    request.open("POST", url, true);
    request.setRequestHeader("X-CSRF-Token", csrfToken());

    // Held on the job so the batch can be stopped: without a handle on the
    // live requests there was no way back out of a fifty-file drop.
    job.request = request;
    inFlight.push(job);

    request.upload.addEventListener("progress", function (event) {
      if (!event.lengthComputable || !job.row.bar) return;
      job.row.bar.value = Math.round((event.loaded / event.total) * 100);
    });

    request.addEventListener("load", function () {
      var payload = {};
      try {
        payload = JSON.parse(request.responseText || "{}");
      } catch (error) {
        payload = {};
      }

      if (request.status === 201 && payload.id) {
        // Uploaded. The pipeline owns it from here, and the grid's polling is
        // what will tell us when it is done.
        job.row.bar.value = 100;
        job.row.bar.removeAttribute("value");
        setState(job.row, "processing", text.processing);
        rowsByPhoto[String(payload.id)] = job.row;
        refreshGrid();
      } else {
        setError(job.row, payload.detail || text.uploadFailed);
        addRetry(job);
      }
      finished(job);
    });

    request.addEventListener("error", function () {
      setError(job.row, text.network);
      addRetry(job);
      finished(job);
    });

    request.addEventListener("abort", function () {
      setError(job.row, text.cancelled);
      addRetry(job);
      finished(job);
    });

    request.send(form);
  }

  /** Empty the queue and stop what is already in the air. */
  function cancelAll() {
    pending.splice(0, pending.length).forEach(function (job) {
      setError(job.row, text.cancelled);
      addRetry(job);
    });
    // `abort` fires its own listener, which marks the row and calls finished().
    inFlight.slice().forEach(function (job) {
      if (job.request) job.request.abort();
    });
    syncCancel();
  }

  // ------------------------------------------------- reconcile with the grid
  // The grid is the source of truth for what happened after the upload, so the
  // queue reads its answer rather than guessing.
  document.body.addEventListener("htmx:afterSwap", function () {
    Object.keys(rowsByPhoto).forEach(function (photoId) {
      var tile = document.getElementById("photo-" + photoId);
      if (!tile) return;
      var status = tile.getAttribute("data-status");
      var row = rowsByPhoto[photoId];

      if (status === "ready") {
        setState(row, "ready", text.ready);
        row.bar.remove();
        delete rowsByPhoto[photoId];
        counts.done += 1;
        announce();
      } else if (status === "failed") {
        var message = tile.querySelector(".photo-item__error");
        setError(row, message ? message.textContent.trim() : text.uploadFailed);
        delete rowsByPhoto[photoId];
      }
    });
  });

  // ------------------------------------------------------------------ events
  input.addEventListener("change", function () {
    enqueue(input.files);
    // Let the same file be picked again after a failure.
    input.value = "";
  });

  ["dragenter", "dragover"].forEach(function (name) {
    zone.addEventListener(name, function (event) {
      event.preventDefault();
      zone.classList.add("upload-zone--active");
    });
  });

  ["dragleave", "dragend"].forEach(function (name) {
    zone.addEventListener(name, function (event) {
      if (event.target !== zone) return;
      zone.classList.remove("upload-zone--active");
    });
  });

  zone.addEventListener("drop", function (event) {
    event.preventDefault();
    zone.classList.remove("upload-zone--active");
    if (event.dataTransfer) enqueue(event.dataTransfer.files);
  });

  // A file dropped next to the zone must not navigate the page away from the
  // album the owner is working on.
  ["dragover", "drop"].forEach(function (name) {
    document.addEventListener(name, function (event) {
      if (zone.contains(event.target)) return;
      event.preventDefault();
    });
  });

  if (cancelButton) {
    cancelButton.addEventListener("click", cancelAll);
  }

  if (clearButton) {
    clearButton.addEventListener("click", function () {
      queue.textContent = "";
      queueWrap.hidden = true;
      rowsByPhoto = {};
      counts = { total: 0, done: 0, failed: 0 };
      if (statusLine) statusLine.textContent = "";
      // Hiding the wrap takes the focused button with it.
      input.focus();
    });
  }
})();
