# Documentation conventions for agents

When creating or updating project documentation in `docs/`, follow these rules.

## When to create documentation

**Default: do not add new docs.** Follow the documentation scope section in the root [`AGENTS.md`](../AGENTS.md).

Create or expand `docs/` content only for **durable project knowledge** — things a new teammate needs to build, run, train, deploy, or operate Lite-VLA without reading chat history.

| Write docs | Skip docs (chat reply is enough) |
|------------|----------------------------------|
| Architecture, MVP scope, requirements | Cursor/MCP/Jira OAuth, IDE setup |
| Dependencies, CI, experiment logging | PATH fixes, nvm, local troubleshooting |
| ROS setup, deployment (cross-cutting) | Conversation summaries |
| Changes to an **existing** `docs/` topic | One-off config for a single machine |
| Jira epic walkthroughs and task deliverables | Use `docs/epics/<epic-slug>/` (see [`epics/AGENTS.md`](epics/AGENTS.md)) |

If a topic is not in the table, prefer updating an existing page or answering in chat. Ask the user before creating a new topic pair (`.md` + `.html`).

## Do not read HTML files

**Agents must never read HTML documentation files.**

- Do **not** open, read, search, grep, or cite HTML under `docs/html/`, `docs/epics/`, or elsewhere in `docs/`.
- HTML is for **humans viewing in a browser only** — not for agent consumption.
- If you need documentation content, always use the paired **`.md`** file instead (`docs/<topic>.md` or `docs/epics/<epic-slug>/<task-slug>.md`).
- When a human or the README points to an HTML path, resolve it to the matching `.md` for your own work.
- When updating documentation, edit the `.md` file first (or in the same change as the `.html`); never treat `.html` as the source of truth.

This applies to every agent (Cursor, CI bots, or any other tooling) regardless of how the file is referenced elsewhere in the repo.

## Dual format: Markdown for agents, HTML for humans

Documentation uses paired `.md` + `.html` files in three locations:

| Scope | Agent source | Human browser |
|-------|--------------|---------------|
| Cross-cutting project topics | `docs/<topic>.md` | `docs/html/<topic>.html` |
| Epic walkthrough | — (HTML only) | `docs/epics/<epic-slug>/index.html` |
| Jira story/task deliverables | `docs/epics/<epic-slug>/<task-slug>.md` | `docs/epics/<epic-slug>/<task-slug>.html` |

Epic walkthrough pages are HTML-only; agents follow [`epics/AGENTS.md`](epics/AGENTS.md) for structure and update them alongside code changes.

**Do not** place Jira task deliverables in `docs/` root or `docs/html/`. **Do not** place cross-cutting topics inside `docs/epics/`.

Rules:

- Add new **cross-cutting** docs as **both** `docs/<topic>.md` and `docs/html/<topic>.html`.
- Add new **Jira task** docs as **both** `docs/epics/<epic-slug>/<task-slug>.md` and `.html` (see root `AGENTS.md` and `epics/AGENTS.md`).
- Keep factual content in sync between each `.md` / `.html` pair. The `.md` file is the **agent source of truth**.
- The `.html` file may add presentation-only extras (layout, styling, interactive widgets) but must not drift in substance from the `.md` file.
- Do **not** remove `.md` files when adding HTML counterparts.
- This file (`AGENTS.md`) is agent-only instructions and has no HTML pair.

At the top of each `.md` doc, include a line pointing humans to the HTML version, e.g.:

```markdown
**Human-readable version (browser):** [`requirements.html`](html/requirements.html)
```

## Responsive HTML (for human files only)

When creating or updating the **`.html`** counterpart in `docs/html/` or `docs/epics/` (without reading existing HTML as input — derive from the `.md` instead):

- Include `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Link the shared stylesheet: `../styles/doc.css` (from `docs/html/`) or `../../styles/doc.css` (from `docs/epics/<epic-slug>/`).
- Epic walkthroughs use `../../styles/presentation.css` (from `docs/epics/<epic-slug>/index.html`).
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
  <link rel="stylesheet" href="../styles/doc.css">
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

**Agents:** link to other docs with `.md` paths only (`requirements.md`, `epics/<epic-slug>/<task-slug>.md` — not HTML).

**Humans (README, HTML footers):** link to `docs/html/<topic>.html` or `docs/epics/<epic-slug>/<task-slug>.html`.

- Link to repo code from HTML with paths like `../../../ml/` (from epic folders) or `../../ml/` (from `docs/html/`); use `<code>` in HTML.
- Root `README.md` links to `docs/html/*.html` and `docs/epics/` for human discoverability.

## Existing assets

- Agent instructions: `docs/AGENTS.md` (this file) · `docs/epics/AGENTS.md` (epic walkthroughs and task docs)
- Cross-cutting human HTML: `docs/html/`
- Epic index and walkthroughs: `docs/epics/`
- Shared styles: `docs/styles/doc.css` · `docs/styles/presentation.css`
- Example cross-cutting pair: `docs/requirements.md` · `docs/html/requirements.html`
- Experiment logging: `docs/experiment-logging.md` · `docs/html/experiment-logging.html`
- Example task pair: `docs/epics/action-interface-parser-and-safety-layer/action-schema.md` · `action-schema.html`
