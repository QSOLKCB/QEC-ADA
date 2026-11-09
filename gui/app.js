/* SPDX-License-Identifier: MPL-2.0 */
/* Browser-only presentation. No network, storage or Ada execution. */
"use strict";
(() => {
  const documents = window.QEC_ADA_CATALOG || [];
  const search = document.getElementById("search");
  const category = document.getElementById("category");
  const count = document.getElementById("results-count");
  const list = document.getElementById("results");
  const preview = document.getElementById("archive-preview");
  const previewTitle = document.getElementById("archive-title");
  const previewText = document.getElementById("archive-source");
  const safeSources = window.QEC_ADA_ARCHIVE_TEXT || Object.create(null);
  document.getElementById("close-source").addEventListener("click", () => {
    preview.hidden = true;
    previewText.textContent = "";
  });
  const categoryNames = [...new Set(documents.map(item => item.category))].sort();
  for (const name of categoryNames) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name.replace(/(^|[-_ ])\w/g, match => match.toUpperCase());
    category.appendChild(option);
  }

  const titleFor = item => item.title || item.path;
  function render() {
    const q = search.value.trim().toLowerCase();
    const c = category.value;
    const result = documents.filter(item =>
      (c === "all" || c === item.category) &&
      (!q || (item.path + " " + titleFor(item)).toLowerCase().includes(q))
    );
    list.replaceChildren();
    for (const item of result) {
      const li = document.createElement("li");
      // An archived HTML file is executable content; never navigate to it.
      // JavaScript is likewise shown inertly, with no dynamic-code evaluation.
      const executableArchive = /\.(html|js)$/i.test(item.path);
      const info = document.createElement("span");
      info.textContent = item.category + " / " + item.path;
      if (executableArchive) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "source-open";
        button.textContent = "Read source: " + titleFor(item);
        button.setAttribute("aria-label", "Read archived source as inert text: " + item.path);
        button.addEventListener("click", () => {
          const content = Object.hasOwn(safeSources, item.path)
            ? safeSources[item.path]
            : "Source preview unavailable; use the local CLI docs show command.";
          previewTitle.textContent = item.path;
          previewText.textContent = content;
          preview.hidden = false;
          preview.scrollIntoView({ block: "start" });
          previewText.focus();
        });
        li.append(button, info);
      } else {
        const link = document.createElement("a");
        link.href = "../docs/reference/qec/" + item.path.split("/").map(encodeURIComponent).join("/");
        link.textContent = titleFor(item);
        link.setAttribute("aria-label", "Open local reference: " + item.path);
        li.append(link, info);
      }
      list.appendChild(li);
    }
    if (!result.length) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No matching documents. Try a different term or category.";
      list.appendChild(li);
    }
    count.textContent = result.length + " of " + documents.length + " source-identical files";
  }
  search.addEventListener("input", render);
  category.addEventListener("change", render);
  document.addEventListener("keydown", event => {
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === "Escape" && document.activeElement === search) {
      search.value = "";
      render();
    }
  });
  render();

  const form = document.getElementById("field-form");
  const a = document.getElementById("coefficients");
  const b = document.getElementById("errors");
  const output = document.getElementById("syndrome");
  const formula = document.getElementById("formula");
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!/^[012]{3}$/.test(a.value) || !/^[012]{3}$/.test(b.value)) {
      output.textContent = "INVALID";
      formula.textContent = "Enter exactly 3 symbols, each in {0,1,2}.";
      return;
    }
    const left = [...a.value].map(Number);
    const right = [...b.value].map(Number);
    const terms = left.map((v, i) => v * right[i]);
    const sum = terms.reduce((total, x) => total + x, 0);
    output.textContent = String(sum % 3);
    formula.textContent = terms.join(" + ") + " = " + sum + " ≡ " + (sum % 3) + " (mod 3)";
  });
  form.requestSubmit();
})();
