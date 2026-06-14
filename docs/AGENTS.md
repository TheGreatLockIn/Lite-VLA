# Documentation conventions for agents

When creating or updating project documentation in `docs/`, follow these rules.

## Do not read HTML files

**Agents must never read `docs/*.html` files.**

- Do **not** open, read, search, grep, or cite any file matching `docs/**/*.html`.
- HTML docs are for **humans viewing in a browser only** — not for agent consumption.
- If you need documentation content, always use the paired **`docs/<topic>.md`** file instead.
- When a human or the README points to `docs/foo.html`, resolve it to `docs/foo.md` for your own work.
- When updating documentation, edit the `.md` file first (or in the same change as the `.html`); never treat `.html` as the source of truth.

This applies to every agent (Cursor, CI bots, or any other tooling) regardless of how the file is referenced elsewhere in the repo.

## Dual format: Markdown for agents, HTML for humans

Every documentation topic exists as **two paired files**:

| Audience | File | Purpose |
|----------|------|---------|
| Agents | `docs/<topic>.md` | Compact, readable source for AI and tooling |
| Humans | `docs/<topic>.html` | Rich, responsive browser docs (tables, CSS, SVG, interactions) |

Rules:

- Add new docs as **both** `docs/<topic>.md` and `docs/<topic>.html`.
- Keep factual content in sync between the pair. The `.md` file is the **agent source of truth**.
- The `.html` file may add presentation-only extras (layout, styling, interactive widgets) but must not drift in substance from the `.md` file.
- Do **not** remove `.md` files when adding HTML counterparts.
- This file (`AGENTS.md`) is agent-only instructions and has no HTML pair.

At the top of each `.md` doc, include a line pointing humans to the HTML version, e.g.:

```markdown
**Human-readable version (browser):** [`requirements.html`](requirements.html)
```

## Responsive HTML (for human files only)

When creating or updating the **`.html`** counterpart (without reading existing HTML as input — derive from the `.md` instead):

- Include `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Link the shared stylesheet: `<link rel="stylesheet" href="styles/doc.css">` (adjust path if the file is in a subdirectory).
- Wrap wide tables in `<div class="table-wrap">` so they scroll horizontally on small screens.
- Use semantic structure: `<header>`, `<main>`, `<section>`, `<nav>`, `<footer>`.

## Color palette: Warm Neutral

Use the shared CSS variables in `docs/styles/doc.css`. Do not introduce ad-hoc colors.

| Role       | Hex       | CSS variable        |
|------------|-----------|---------------------|
| Background | `#FAF8F5` | `--color-bg`        |
| Surface    | `#F0EDE8` | `--color-surface`   |
| Border     | `#D4CFC7` | `--color-border`    |
| Text       | `#2C2825` | `--color-text`      |
| Accent     | `#B8602A` | `--color-accent`    |
| Muted      | `#8A837A` | `--color-muted`     |

## What HTML enables (human docs)

In the `.html` counterpart, prefer HTML features over plain prose when they help human readers:

| Capability | Use for |
|------------|---------|
| `<table>` | Tabular data (dependencies, configs, comparisons) |
| CSS (`doc.css` + scoped `<style>`) | Layout, callouts, responsive design |
| SVG | Diagrams, workflows, architecture sketches |
| `<pre><code>` | Code snippets |
| `<img>` | Screenshots and figures |
| `<canvas>` | Spatial or animated visuals |
| JavaScript + form controls | Sliders, toggles, knobs to explore parameters (e.g. algorithm tuning, design previews) |

Interactive docs are encouraged when they help readers **explore** behavior. Keep scripts small, inline or in a sibling `.js` file under `docs/`, and avoid external CDN dependencies unless necessary.

## Document skeleton (HTML human counterpart)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Topic — Lite-VLA</title>
  <link rel="stylesheet" href="styles/doc.css">
</head>
<body>
  <div class="doc-shell">
    <header class="doc-header">
      <h1>Title</h1>
      <p class="doc-lead">One-line summary.</p>
    </header>
    <main>
      <!-- sections -->
    </main>
    <footer class="doc-footer">
      <p>Lite-VLA documentation</p>
    </footer>
  </div>
</body>
</html>
```

## Cross-references

**Agents:** link to other docs with `.md` paths only (`requirements.md`, not `requirements.html`).

**Humans (README, HTML footers):** link to `docs/*.html`.

- Link to repo code with paths like `../ml/` or `` `ml/` `` in prose; use `<code>` in HTML.
- Root `README.md` links to `docs/*.html` for human discoverability.

## Existing assets

- Agent instructions: `docs/AGENTS.md` (this file)
- Shared styles: `docs/styles/doc.css`
- Example pair: `docs/requirements.md` (agents) · `docs/requirements.html` (humans)
