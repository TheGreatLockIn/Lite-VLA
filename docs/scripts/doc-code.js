/**
 * Lite-VLA documentation — Prism init, editor-style code panels, copy buttons.
 * Load after Prism core and language components.
 */
(function () {
  const LANG_LABELS = {
    python: "Python",
    bash: "Bash",
    shell: "Shell",
    yaml: "YAML",
    json: "JSON",
    diff: "Diff",
    "diff-python": "Diff (Python)",
    text: "Text",
    html: "HTML",
    javascript: "JavaScript",
    typescript: "TypeScript",
  };

  function languageLabel(pre) {
    const code = pre.querySelector("code");
    const classes = `${pre.className} ${code ? code.className : ""}`.split(/\s+/);
    for (const cls of classes) {
      if (cls.startsWith("language-")) {
        const lang = cls.slice("language-".length);
        if (LANG_LABELS[lang]) {
          return LANG_LABELS[lang];
        }
        return lang.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      }
    }
    return "Code";
  }

  function wrapCodePanels() {
    document.querySelectorAll("pre > code[class*='language-']").forEach((code) => {
      const pre = code.parentElement;
      if (!pre || pre.closest(".code-panel")) {
        return;
      }

      const panel = document.createElement("div");
      panel.className = "code-panel";

      const header = document.createElement("div");
      header.className = "code-panel-header";

      const dots = document.createElement("div");
      dots.className = "code-panel-dots";
      dots.setAttribute("aria-hidden", "true");
      for (let i = 0; i < 3; i += 1) {
        dots.appendChild(document.createElement("span"));
      }

      const lang = document.createElement("span");
      lang.className = "code-panel-lang";
      lang.textContent = languageLabel(pre);

      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "code-copy-btn";
      copyBtn.textContent = "Copy";
      copyBtn.addEventListener("click", async () => {
        const text = code.textContent || "";
        try {
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = "Copied";
          copyBtn.classList.add("copied");
          window.setTimeout(() => {
            copyBtn.textContent = "Copy";
            copyBtn.classList.remove("copied");
          }, 1600);
        } catch {
          copyBtn.textContent = "Failed";
          window.setTimeout(() => {
            copyBtn.textContent = "Copy";
          }, 1600);
        }
      });

      header.appendChild(dots);
      header.appendChild(lang);
      header.appendChild(copyBtn);

      pre.parentNode.insertBefore(panel, pre);
      panel.appendChild(header);
      panel.appendChild(pre);
    });
  }

  function init() {
    wrapCodePanels();
    if (window.Prism) {
      window.Prism.highlightAll();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
