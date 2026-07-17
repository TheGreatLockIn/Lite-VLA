#!/usr/bin/env python3
"""Render epic architecture/code Markdown task docs to paired HTML."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
PRISM_SCRIPTS = """
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-yaml.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-json.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-diff.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/diff-highlight/prism-diff-highlight.min.js"></script>
<script src="../../scripts/doc-code.js"></script>
""".strip()

MERMAID_SCRIPT = """
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({
    startOnLoad: true,
    theme: "base",
    themeVariables: {
      background: "#FAF8F5",
      primaryColor: "#F0EDE8",
      primaryBorderColor: "#D4CFC7",
      primaryTextColor: "#2C2825",
      lineColor: "#B8602A",
      textColor: "#2C2825"
    }
  });
</script>
""".strip()


def _extract_title(md_text: str) -> tuple[str, str]:
    lines = md_text.splitlines()
    if lines and lines[0].startswith("# "):
        return lines[0][2:].strip(), "\n".join(lines[1:])
    return "Lite-VLA", md_text


def _preprocess_mermaid(md_text: str) -> tuple[str, bool]:
    has_mermaid = False

    def repl(match: re.Match[str]) -> str:
        nonlocal has_mermaid
        has_mermaid = True
        body = html.escape(match.group(1).strip())
        return f'<pre class="mermaid">{body}</pre>'

    processed = re.sub(r"```mermaid\n(.*?)```", repl, md_text, flags=re.DOTALL)
    return processed, has_mermaid


def _add_prism_classes(html_body: str) -> str:
    lang_map = {
        "python": "language-python",
        "bash": "language-bash",
        "sh": "language-bash",
        "yaml": "language-yaml",
        "json": "language-json",
        "diff": "language-diff-python diff-highlight",
        "text": "language-text",
    }

    def repl(match: re.Match[str]) -> str:
        lang = match.group(1) or ""
        code = match.group(2)
        cls = lang_map.get(lang, f"language-{lang}" if lang else "")
        if cls:
            return f'<pre><code class="{cls}">{code}</code></pre>'
        return f"<pre><code>{code}</code></pre>"

    return re.sub(
        r'<pre><code class="language-(\w+)">(.*?)</code></pre>',
        repl,
        html_body,
        flags=re.DOTALL,
    )


def _wrap_tables(html_body: str) -> str:
    return re.sub(r"<table>", '<div class="table-wrap"><table>', html_body).replace(
        "</table>", "</table></div>"
    )


def render_markdown_to_html(md_path: Path, out_path: Path | None = None) -> Path:
    md_text = md_path.read_text(encoding="utf-8")
    title, body = _extract_title(md_text)
    body, has_mermaid = _preprocess_mermaid(body)
    html_body = markdown.markdown(
        body,
        extensions=["fenced_code", "tables", "toc"],
    )
    html_body = _add_prism_classes(html_body)
    html_body = _wrap_tables(html_body)

    # Dynamically compute the path prefix back to docs/.
    parts = md_path.resolve().parts
    try:
        docs_idx = parts.index("docs")
        # Number of directories to ascend back to 'docs/' (excluding the file itself)
        levels_after_docs = len(parts) - 1 - docs_idx
        prefix = "../" * (levels_after_docs - 1)
    except ValueError:
        prefix = "../../"

    prism_scripts = PRISM_SCRIPTS.replace("../../", prefix)
    back_link = "../index.html" if md_path.parent.name in {"architecture", "code"} else "index.html"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — Lite-VLA</title>
  <link rel="stylesheet" href="{prefix}styles/doc.css">
</head>
<body>
  <div class="doc-shell">
    <header class="doc-header">
      <a class="back-link" href="{back_link}">Back to epic walkthrough</a>
      <h1>{html.escape(title)}</h1>
    </header>
    <main>
      {html_body}
    </main>
    <footer class="doc-footer">
      <p>Lite-VLA documentation</p>
    </footer>
  </div>
  {prism_scripts}
  {MERMAID_SCRIPT if has_mermaid else ""}
</body>
</html>
"""
    target = out_path or md_path.with_suffix(".html")
    target.write_text(page, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Task .md files to render")
    args = parser.parse_args(argv)
    for path in args.paths:
        out = render_markdown_to_html(path)
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
