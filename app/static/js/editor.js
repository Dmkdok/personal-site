/**
 * The article editor.
 *
 * Everything that changes the article's text goes through the textarea, so the
 * toolbar, the shortcuts and the image upload all funnel into one insertion
 * helper. That helper dispatches a real `input` event, which is what drives the
 * htmx live preview and the autosave — there is no second code path that could
 * save something the preview never rendered.
 *
 * No Russian lives here: every user-visible string arrives on a data attribute
 * written by the template from app/i18n/ru/blog.json.
 */
(function () {
  "use strict";

  // Both editors that carry F50's guarantee — the blog article and the
  // shared-article — point this script at their own ids through data
  // attributes on the root, rather than this file hardcoding one editor's
  // ids: data-editor-form/-body/-status name the form, the textarea and the
  // save-state region to watch.
  var root = document.querySelector("[data-editor-form]");
  if (!root) return;

  var form = document.getElementById(root.getAttribute("data-editor-form"));
  var area = document.getElementById(root.getAttribute("data-editor-body"));
  if (!form || !area) return;

  var statusId = root.getAttribute("data-editor-status");
  var toolbar = root.querySelector(".md-toolbar");
  var picker = document.getElementById("blog-image-input");

  // ==========================================================================
  // Save state
  // The element is replaced by htmx on every save, so it is looked up fresh and
  // its labels are read from the markup rather than held in a variable.
  // ==========================================================================
  var dirty = false;
  var failed = false;

  function setStatus(name) {
    var box = document.getElementById(statusId);
    if (!box) return;
    var text = box.querySelector("[data-status-text]");
    if (text) text.textContent = box.getAttribute("data-" + name) || "";
  }

  /** Requests that write the article's text — not every request on the page.
   *
   * «Опубликовать» and «Снять с публикации» carry `hx-include="#post-form"`,
   * so they save the typed text on their way through and must clear the guard;
   * the cover upload, which is its own multipart form, must not.
   */
  function savesTheArticle(elt) {
    if (!elt || !elt.getAttribute) return false;
    return (
      elt === form ||
      elt.getAttribute("data-role") === "save" ||
      elt.getAttribute("hx-include") === "#" + form.id
    );
  }

  function sourceOf(event) {
    return (event.detail.requestConfig || {}).elt || event.detail.elt;
  }

  form.addEventListener("input", function () {
    dirty = true;
    // A failure outranks «не сохранено»: typing more does not make it untrue,
    // and the debounce will try again in 2.5 s regardless.
    setStatus(failed ? "failed" : "dirty");
  });

  document.body.addEventListener("htmx:beforeRequest", function (event) {
    if (savesTheArticle(event.detail.elt)) setStatus("saving");
  });

  document.body.addEventListener("htmx:afterRequest", function (event) {
    if (!savesTheArticle(sourceOf(event)) || !event.detail.successful) return;
    dirty = false;
    failed = false;
  });

  // A failed autosave used to surface only as a toast that removed itself after
  // four seconds, leaving the page sitting there looking normal with unsaved
  // text in it. This state stays until a save actually succeeds.
  ["htmx:responseError", "htmx:sendError"].forEach(function (name) {
    document.body.addEventListener(name, function (event) {
      if (!savesTheArticle(sourceOf(event))) return;
      failed = true;
      setStatus("failed");
    });
  });

  // The last line of defence: the browser's own confirmation. Autosave fires
  // 2.5 s after the last keystroke, so closing the tab inside that window — or
  // following the «Открыть статью» link — used to lose the text silently. No
  // custom message: every browser ignores the string and shows its own.
  window.addEventListener("beforeunload", function (event) {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  // ==========================================================================
  // Editing the source
  // ==========================================================================
  function placeholder(name) {
    return (toolbar && toolbar.getAttribute("data-ph-" + name)) || "";
  }

  /** Replace [start, end) with `text` and leave the caret where work continues. */
  function replaceRange(start, end, text, selectionStart, selectionEnd) {
    area.focus();
    area.setSelectionRange(start, end);

    var inserted = false;
    if (text) {
      try {
        // Deprecated, but the only way to keep the browser's native undo stack
        // usable. Every browser we support still honours it on a textarea.
        inserted = document.execCommand("insertText", false, text);
      } catch (error) {
        inserted = false;
      }
    }

    if (!inserted) {
      var value = area.value;
      area.value = value.slice(0, start) + text + value.slice(end);
      area.dispatchEvent(new Event("input", { bubbles: true }));
    }

    area.setSelectionRange(selectionStart, selectionEnd);
    area.focus();
  }

  /** `**bold**` and friends: wraps the selection, or unwraps it if already wrapped. */
  function toggleWrap(marker, placeholderName) {
    var start = area.selectionStart;
    var end = area.selectionEnd;
    var value = area.value;
    var width = marker.length;

    if (
      start >= width &&
      end + width <= value.length &&
      value.slice(start - width, start) === marker &&
      value.slice(end, end + width) === marker
    ) {
      var inner = value.slice(start, end);
      replaceRange(start - width, end + width, inner, start - width, start - width + inner.length);
      return;
    }

    var selected = value.slice(start, end) || placeholder(placeholderName);
    replaceRange(start, end, marker + selected + marker, start + width, start + width + selected.length);
  }

  /** Line markers — heading, quote, list — applied to every selected line. */
  function togglePrefix(prefix, placeholderName) {
    var value = area.value;
    var start = value.lastIndexOf("\n", area.selectionStart - 1) + 1;
    var lineEnd = value.indexOf("\n", area.selectionEnd);
    var end = lineEnd === -1 ? value.length : lineEnd;

    var block = value.slice(start, end) || placeholder(placeholderName);
    var lines = block.split("\n");
    var allPrefixed = lines.every(function (line) {
      return line.indexOf(prefix) === 0;
    });

    var next = lines
      .map(function (line) {
        return allPrefixed ? line.slice(prefix.length) : prefix + line;
      })
      .join("\n");

    replaceRange(start, end, next, start, start + next.length);
  }

  /** One line of code stays inline; several lines become a fenced block. */
  function codeAction() {
    var start = area.selectionStart;
    var end = area.selectionEnd;
    var selected = area.value.slice(start, end);

    if (selected.indexOf("\n") === -1) {
      toggleWrap("`", "code");
      return;
    }
    var text = "```\n" + selected + "\n```";
    replaceRange(start, end, text, start + 4, start + 4 + selected.length);
  }

  /** Selecting a URL first puts it in the address half; otherwise in the label. */
  function linkAction() {
    var start = area.selectionStart;
    var end = area.selectionEnd;
    var selected = area.value.slice(start, end);
    var isUrl = /^(https?:\/\/|mailto:|tel:|\/)\S*$/i.test(selected.trim()) && selected.trim() !== "";

    var label = isUrl ? placeholder("text") : selected || placeholder("text");
    var url = isUrl ? selected.trim() : placeholder("url");

    var caret = isUrl ? start + 1 : start + 1 + label.length + 2;
    var length = isUrl ? label.length : url.length;
    replaceRange(start, end, "[" + label + "](" + url + ")", caret, caret + length);
  }

  /**
   * A block that has to own its paragraph, with the caret left on the first thing
   * worth typing over.
   *
   * A video is only a player when its link is a paragraph by itself (F63), and a
   * table is only a table when its rows start at the beginning of a line — so the
   * blank lines around the insertion are part of the skeleton, not decoration.
   * They are added only when they are missing, so pressing the button twice does
   * not leave a growing gap.
   */
  function insertBlock(text, offset, length) {
    var start = area.selectionStart;
    var end = area.selectionEnd;
    var before = area.value.slice(0, start);
    var after = area.value.slice(end);

    var lead = before === "" || /\n\n$/.test(before) ? "" : /\n$/.test(before) ? "\n" : "\n\n";
    var tail = after === "" || /^\n\n/.test(after) ? "" : /^\n/.test(after) ? "\n" : "\n\n";

    var caret = start + lead.length + offset;
    replaceRange(start, end, lead + text + tail, caret, caret + length);
  }

  /** A captioned link on a line of its own — the shape `render_markdown` turns
   * into a named player instead of an anonymous one (T142). The caption is
   * selected first, so typing over it is the very next thing that happens. */
  function videoAction() {
    var text = placeholder("video-text");
    var url = placeholder("video-url");
    insertBlock("[" + text + "](" + url + ")", 1, text.length);
  }

  /** Header row, the dashes that make it a header, and one row of data. */
  function tableAction() {
    var th = placeholder("th");
    var td = placeholder("td");
    var text =
      "| " + th + " | " + th + " |\n| --- | --- |\n| " + td + " | " + td + " |";
    insertBlock(text, 2, th.length);
  }

  var ACTIONS = {
    bold: function () {
      toggleWrap("**", "text");
    },
    italic: function () {
      toggleWrap("_", "text");
    },
    code: codeAction,
    heading: function () {
      togglePrefix("## ", "heading");
    },
    quote: function () {
      togglePrefix("> ", "quote");
    },
    list: function () {
      togglePrefix("- ", "item");
    },
    link: linkAction,
    video: videoAction,
    table: tableAction
  };

  // ==========================================================================
  // Toolbar: one tab stop, arrow keys between the buttons (WAI-ARIA toolbar).
  // ==========================================================================
  var buttons = toolbar
    ? Array.prototype.slice.call(toolbar.querySelectorAll(".md-toolbar__button"))
    : [];

  buttons.forEach(function (button, index) {
    button.tabIndex = index === 0 ? 0 : -1;
    button.addEventListener("click", function () {
      var action = ACTIONS[button.getAttribute("data-md")];
      if (action) action();
    });
  });

  function focusButton(index) {
    var next = (index + buttons.length) % buttons.length;
    buttons.forEach(function (button, position) {
      button.tabIndex = position === next ? 0 : -1;
    });
    buttons[next].focus();
  }

  if (toolbar) {
    toolbar.addEventListener("keydown", function (event) {
      var index = buttons.indexOf(document.activeElement);
      if (index === -1) return;

      if (event.key === "ArrowRight" || event.key === "ArrowDown") focusButton(index + 1);
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") focusButton(index - 1);
      else if (event.key === "Home") focusButton(0);
      else if (event.key === "End") focusButton(buttons.length - 1);
      else return;

      event.preventDefault();
    });
  }

  area.addEventListener("keydown", function (event) {
    if (!(event.ctrlKey || event.metaKey) || event.altKey || !event.key) return;
    var key = event.key.toLowerCase();
    var name = key === "b" ? "bold" : key === "i" ? "italic" : key === "k" ? "link" : null;
    if (!name) return;
    event.preventDefault();
    ACTIONS[name]();
  });

  // ==========================================================================
  // Video title: fetched once, server-side, when a recognised link lands in
  // either half of the skeleton T142 inserts (F66, ADR-040). videoAction()
  // leaves the *caption* selected — so a paste that follows the button
  // without moving the caret lands there, not in the address, and has to be
  // recognised too, or the most direct gesture ("press the button, paste the
  // link I already copied") would leave a dead link instead of a player. VK
  // is unaffected — the server never attempts it, so no request is ever made
  // for one.
  // ==========================================================================
  function maybeFillVideoCaption() {
    var value = area.value;
    var lineStart = value.lastIndexOf("\n", area.selectionStart - 1) + 1;
    var lineEnd = value.indexOf("\n", area.selectionEnd);
    if (lineEnd === -1) lineEnd = value.length;
    var line = value.slice(lineStart, lineEnd);

    var shape = /^\[([^[\]]*)\]\(([^()]*)\)$/.exec(line);
    if (!shape) return;

    // Exactly one half must still be its untouched placeholder; the other is
    // what the owner just pasted, wherever it landed. An owner who already
    // typed their own title into an untouched address keeps what they typed —
    // neither half matches, and nothing here fires.
    var captionPh = placeholder("video-text");
    var urlPh = placeholder("video-url");
    var pastedIntoAddress = shape[1] === captionPh && shape[2] !== urlPh;
    var pastedIntoCaption = shape[1] !== captionPh && shape[2] === urlPh;
    if (!pastedIntoAddress && !pastedIntoCaption) return;
    var url = pastedIntoAddress ? shape[2] : shape[1];
    if (!url) return;

    var body = new URLSearchParams();
    body.set("url", url);
    fetch("/blog/admin/video-title", {
      method: "POST",
      body: body,
      headers: csrfHeaders(),
      credentials: "same-origin"
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (responseBody) {
        var title = responseBody && responseBody.title;
        if (!title) return;
        // The request took a moment. Only write back if the line is still
        // exactly what it was when asked (an owner who kept typing meanwhile
        // is left alone) and the owner has not moved on to something else —
        // this is unrequested, so it must never pull focus back to steal
        // the next keystroke.
        if (document.activeElement !== area) return;
        if (area.value.slice(lineStart, lineStart + line.length) !== line) return;
        var text = "[" + title + "](" + url + ")";
        replaceRange(lineStart, lineStart + line.length, text, lineStart + 1, lineStart + 1 + title.length);
      })
      .catch(function () {});
  }

  // Video-title autofetch belongs to the toolbar's video button (F66), so it
  // needs the toolbar's placeholders to recognise the skeleton against — a
  // page with none would have nothing to compare. Both editors carry one
  // since T148, so both get this for free; only a future editor with no
  // `.md-toolbar` at all would skip it.
  if (toolbar) {
    area.addEventListener("paste", function () {
      // After the browser's own paste has landed in the value, not before.
      setTimeout(maybeFillVideoCaption, 0);
    });
  }

  // ==========================================================================
  // Images: the photo control (its own visible action, F72), a drop on the
  // textarea, or a paste. Each file gets its own row — uploading, then done
  // or failed with a retry — and its own XMLHttpRequest, so progress is real
  // and one rejection cannot disturb the rest of the drop (F73, modelled on
  // uploader.js's send/addRow/setState/setError/addRetry). Uploads run one
  // at a time: an article carries a handful of pictures, never the fifty an
  // album can, so completion order is drop order and no reorder buffer is
  // needed to keep insertions in order.
  // ==========================================================================
  function csrfHeaders() {
    // The token is already on <body> for htmx; reading it back avoids printing
    // it a second time into the page.
    try {
      return JSON.parse(document.body.getAttribute("hx-headers") || "{}");
    } catch (error) {
      return {};
    }
  }

  function insertAtCursor(markdown) {
    var start = area.selectionStart;
    var end = area.selectionEnd;
    var before = area.value.slice(0, start);

    // A picture needs its own block, or Markdown folds it into the paragraph.
    var lead = "";
    if (before && !/\n\n$/.test(before)) lead = /\n$/.test(before) ? "\n" : "\n\n";

    var text = lead + markdown + "\n";
    replaceRange(start, end, text, start + text.length, start + text.length);
  }

  /** The article being edited, so its pictures are filed with it (F40). */
  function currentPostId() {
    var form = document.querySelector("[hx-post^='/blog/admin/posts/']");
    var match = form && /\/blog\/admin\/posts\/(\d+)/.exec(form.getAttribute("hx-post"));
    return match ? match[1] : "";
  }

  // Image upload is blog-only (F51) — no picker means no photo control, no
  // drop zone and no image paste either, which is exactly the shared-article
  // editor's own state (ADR-042: title and Markdown body only, no image
  // pipeline).
  if (picker) {
    var imageButton = document.getElementById("editor-image-button");
    var queue = document.getElementById("editor-image-queue");
    var queueStatus = document.getElementById("editor-image-queue-status");

    var maxBytes = parseInt(root.getAttribute("data-max-bytes"), 10) || 0;
    var accept = (root.getAttribute("data-accept") || "").split(",").filter(Boolean);
    var msg = {
      uploading: root.getAttribute("data-msg-uploading") || "",
      done: root.getAttribute("data-msg-done") || "",
      failed: root.getAttribute("data-msg-failed") || "",
      tooBig: root.getAttribute("data-msg-too-big") || "",
      wrongType: root.getAttribute("data-msg-wrong-type") || "",
      retry: root.getAttribute("data-retry-label") || "",
      progress: root.getAttribute("data-progress-label") || "",
      summary: root.getAttribute("data-summary") || "",
      summaryFailed: root.getAttribute("data-summary-failed") || ""
    };

    var counts = { total: 0, done: 0, failed: 0 };
    var statusTimer = null;

    /** Report progress once a second, as one sentence — the same throttle
     * uploader.js uses: a screen reader that read out every row change on a
     * multi-file drop would have to sit through all of it before the page
     * is usable again. */
    function announce() {
      if (!queueStatus || statusTimer) return;
      statusTimer = window.setTimeout(function () {
        statusTimer = null;
        if (!counts.total) {
          queueStatus.textContent = "";
          return;
        }
        var template = counts.failed ? msg.summaryFailed : msg.summary;
        queueStatus.textContent = template
          .replace("{done}", counts.done)
          .replace("{total}", counts.total)
          .replace("{failed}", counts.failed);
      }, 1000);
    }

    function progressBar(file) {
      var bar = document.createElement("progress");
      bar.className = "upload-item__bar";
      bar.max = 100;
      bar.value = 0;
      bar.setAttribute("aria-label", msg.progress + " — " + file.name);
      return bar;
    }

    function addRow(file) {
      queue.hidden = false;

      var row = document.createElement("li");
      row.className = "upload-item upload-item--uploading";

      var name = document.createElement("span");
      name.className = "upload-item__name";
      name.textContent = file.name;

      var state = document.createElement("span");
      state.className = "meta upload-item__state";
      state.textContent = msg.uploading;

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
      setState(row, "failed", msg.failed);
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
    }

    /** Offer the row another attempt. The `File` is still held, so nothing is
     * re-picked; only failures a second attempt could survive get one — a
     * file refused for its size or its type would fail identically (and
     * never gets this button — see `upload()`). A retry runs standalone,
     * outside the drop's own sequence: it already missed its slot in drop
     * order the moment it failed. */
    function addRetry(job) {
      if (job.row.retry) return;

      var button = document.createElement("button");
      button.type = "button";
      button.className = "button button--quiet upload-item__retry";
      button.textContent = msg.retry;
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
        setState(job.row, "uploading", msg.uploading);
        announce();
        send(job, function () {});
      });

      job.row.retry = button;
      job.row.root.appendChild(button);
    }

    /** Why this picture cannot succeed, or "" if it can — checked before
     * sending. The same gate the album uploader applies, for the same
     * reason: a drop ignores the input's `accept` entirely, so an oversized
     * frame or a HEIC used to travel the whole way up before being refused.
     * The server checks again regardless.
     *
     * An empty `file.type` is not refused: browsers report HEIC's MIME type
     * inconsistently, and this filter used to discard a photograph straight
     * off a phone in silence — no row, no message, nothing to retry. The
     * magic sniff on the server is the authority (F51), and a refusal there
     * at least says so. Anything that *declares* a non-image type still goes.
     */
    function rejection(file) {
      if (maxBytes && file.size > maxBytes) {
        return msg.tooBig.replace("{name}", file.name).replace("{limit}", Math.round(maxBytes / (1024 * 1024)));
      }
      if (file.type && accept.length && accept.indexOf(file.type) === -1) {
        return msg.wrongType.replace("{name}", file.name);
      }
      return "";
    }

    function send(job, next) {
      var payload = new FormData();
      payload.append("file", job.file);

      var postId = currentPostId();
      if (postId) payload.append("post_id", postId);

      var request = new XMLHttpRequest();
      request.open("POST", "/blog/admin/images", true);
      var headers = csrfHeaders();
      Object.keys(headers).forEach(function (name) {
        request.setRequestHeader(name, headers[name]);
      });

      request.upload.addEventListener("progress", function (event) {
        if (!event.lengthComputable || !job.row.bar) return;
        job.row.bar.value = Math.round((event.loaded / event.total) * 100);
      });

      request.addEventListener("load", function () {
        var body = {};
        try {
          body = JSON.parse(request.responseText || "{}");
        } catch (error) {
          body = {};
        }

        if (request.status === 200 && body.markdown) {
          if (job.row.bar) {
            job.row.bar.value = 100;
            job.row.bar.removeAttribute("value");
          }
          setState(job.row, "ready", msg.done);
          insertAtCursor(body.markdown);
          counts.done += 1;
        } else {
          setError(job.row, body.error || body.detail || msg.failed);
          addRetry(job);
          counts.failed += 1;
        }
        announce();
        next();
      });

      request.addEventListener("error", function () {
        setError(job.row, msg.failed);
        addRetry(job);
        counts.failed += 1;
        announce();
        next();
      });

      request.send(payload);
    }

    function upload(files) {
      // An empty `type` is passed on rather than dropped — see `rejection()`.
      var images = Array.prototype.filter.call(files || [], function (file) {
        return file && (!file.type || file.type.indexOf("image/") === 0);
      });
      if (!images.length) return;

      var pending = [];
      images.forEach(function (file) {
        var row = addRow(file);
        counts.total += 1;
        var why = rejection(file);
        if (why) {
          setError(row, why);
          counts.failed += 1;
          return;
        }
        pending.push({ file: file, row: row });
      });
      announce();

      // Sequential, so completion order is drop order and a picture's
      // Markdown always lands after every picture dropped before it.
      function pump() {
        if (!pending.length) return;
        send(pending.shift(), pump);
      }
      pump();
    }

    imageButton.addEventListener("click", function () {
      picker.click();
    });

    picker.addEventListener("change", function () {
      upload(picker.files);
      picker.value = "";
    });

    function carriesFiles(event) {
      var transfer = event.dataTransfer;
      if (!transfer) return false;
      return Array.prototype.indexOf.call(transfer.types || [], "Files") !== -1;
    }

    area.addEventListener("dragover", function (event) {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      area.classList.add("is-dropping");
    });

    area.addEventListener("dragleave", function () {
      area.classList.remove("is-dropping");
    });

    area.addEventListener("drop", function (event) {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      area.classList.remove("is-dropping");
      upload(event.dataTransfer.files);
    });

    area.addEventListener("paste", function (event) {
      var files = event.clipboardData && event.clipboardData.files;
      if (!files || !files.length) return;
      var images = Array.prototype.filter.call(files, function (file) {
        return file.type && file.type.indexOf("image/") === 0;
      });
      if (!images.length) return;
      event.preventDefault();
      upload(images);
    });
  }
})();
