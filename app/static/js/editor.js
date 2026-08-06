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

  var root = document.querySelector(".editor");
  if (!root) return;

  var form = document.getElementById("post-form");
  var area = document.getElementById("post-body");
  if (!form || !area) return;

  var toolbar = root.querySelector(".md-toolbar");
  var picker = document.getElementById("blog-image-input");

  function toast(message, kind) {
    if (message && window.portfolioToast) window.portfolioToast(message, kind || "success");
  }

  // ==========================================================================
  // Save state
  // The element is replaced by htmx on every save, so it is looked up fresh and
  // its labels are read from the markup rather than held in a variable.
  // ==========================================================================
  function setStatus(name) {
    var box = document.getElementById("save-state");
    if (!box) return;
    var text = box.querySelector(".editor-status__text");
    if (text) text.textContent = box.getAttribute("data-" + name) || "";
  }

  form.addEventListener("input", function () {
    setStatus("dirty");
  });

  document.body.addEventListener("htmx:beforeRequest", function (event) {
    var elt = event.detail.elt;
    if (!elt) return;
    if (elt === form || (elt.getAttribute && elt.getAttribute("data-role") === "save")) {
      setStatus("saving");
    }
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
    image: function () {
      if (picker) picker.click();
    }
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
  // Images: the toolbar button, a drop on the textarea, or a paste.
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

  function uploadOne(file) {
    var payload = new FormData();
    payload.append("file", file);

    return fetch("/blog/admin/images", {
      method: "POST",
      body: payload,
      headers: csrfHeaders(),
      credentials: "same-origin"
    })
      .then(function (response) {
        return response.text().then(function (raw) {
          var body = {};
          try {
            body = JSON.parse(raw);
          } catch (error) {
            body = {};
          }
          if (!response.ok) throw new Error(body.error || body.detail || "");
          return body;
        });
      })
      .then(function (body) {
        insertAtCursor(body.markdown);
      });
  }

  function upload(files) {
    var images = Array.prototype.filter.call(files || [], function (file) {
      return file && file.type && file.type.indexOf("image/") === 0;
    });
    if (!images.length) return;

    toast(root.getAttribute("data-msg-uploading"));

    // Sequential, so the pictures land in the order they were dropped.
    var chain = Promise.resolve();
    images.forEach(function (file) {
      chain = chain.then(function () {
        return uploadOne(file);
      });
    });

    chain
      .then(function () {
        toast(root.getAttribute("data-msg-done"));
      })
      .catch(function (error) {
        toast((error && error.message) || root.getAttribute("data-msg-failed"), "error");
      });
  }

  if (picker) {
    picker.addEventListener("change", function () {
      upload(picker.files);
      picker.value = "";
    });
  }

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
})();
