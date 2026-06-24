# Agent Instructions

These instructions apply to all agents working in this repository.

## Documentation sources

- For cross-cutting project documentation under `docs/`, follow `docs/AGENTS.md`.
- For epic walkthroughs and Jira task docs, follow `docs/epics/AGENTS.md` (canonical source for the agent contract and task-doc depth standard).
- Epic and task files live under `docs/epics/<epic-slug>/` (see **Epic docs** below).

## Documentation scope (default: minimal)

Not every chat or config change needs docs. Default to **no new documentation** unless the work clearly meets a threshold below.

### Epic walkthroughs (`docs/epics/<epic-slug>/index.html`)

Update **only** when you **implement or modify project code** tied to a Jira epic/story/task (from the import CSV or live Jira), in the **same change** as that code.

Qualifying code paths: `ml/`, `ros_ws/`, `data/`, `deployment/`, `litevla/`, `scripts/` (runtime/CI), `tests/`, and versioned config that affects build, train, deploy, or robot runtime.

**Do not** update epic walkthroughs for:
- IDE, editor, or MCP setup (`.cursor/`, Cursor settings, OAuth troubleshooting)
- Questions, explanations, or reviews with no code change
- Personal dev-environment fixes (PATH, nvm, local tooling)
- One-off debugging that does not change committed project behavior

When you do update an epic walkthrough:
- Infer the active epic from the task title, Jira key, branch name, changed paths, CSV parent mapping, and conversation context. Ask only when two or more epics remain equally plausible.
- Add each story/task/subtask in source order. Do not append tasks randomly; preserve the epic sequence from the Jira CSV or current board.
- For every worked task, record intent, files/modules touched, code walkthrough notes, data/control flow, validation evidence, and ADRs for meaningful technical decisions.
- Treat these pages as senior-to-junior engineering walkthroughs for asynchronous review: explain what each mentioned module/class/function/topic/config does, why it exists, and how it participates in the runtime flow.
- Prefer visual explanation: maintain Mermaid C4 diagrams for system/container views, Mermaid flowcharts or sequence diagrams for task-level flows, and human-friendly HTML/SVG/interactive visuals when they clarify the code.
- Use the standard format in `docs/epics/AGENTS.md`. The epic `index.html` is the source of truth for walkthroughs.

### Epic task docs (`docs/epics/<epic-slug>/`)

When a **completed or in-progress Jira story/task** needs durable documentation (schemas, API notes, runbooks tied to that task), create and maintain it **inside the matching epic folder** under `docs/epics/`.

| File | Purpose |
|------|---------|
| `docs/epics/<epic-slug>/<task-slug>.md` | Agent source of truth |
| `docs/epics/<epic-slug>/<task-slug>.html` | Human-readable browser page |

Rules:

- Infer `<epic-slug>` from Jira parent epic, CSV mapping, branch name, or changed paths (same signals as walkthrough updates).
- Use a kebab-case `<task-slug>` from the story title (example: `action-schema` for “Define discrete action schema”).
- Add the epic and Jira key at the top of the `.md` file.
- Include enough explanation for a reader to understand the task without chat history: purpose, code entry points, important symbols, data/control flow, commands, validation, decisions, and remaining risks.
- Link the human HTML from the epic `index.html` story section.
- Update the epic walkthrough (`index.html`) in the **same change** as the task doc.
- Reuse `docs/styles/doc.css` for task HTML; link with `../../styles/doc.css` from epic folders.

**Do not** put Jira task deliverables in `docs/` root or `docs/html/`. Reserve those for cross-cutting project knowledge (architecture, dependencies, CI, experiment logging) that spans epics.

### Project docs (`docs/` and `docs/html/`)

Create a **new** topic page only for durable **cross-cutting** knowledge a new teammate needs to build, run, train, deploy, or operate Lite-VLA (architecture, dependencies, CI, experiment logging, ROS setup, etc.).

**Do not** add Jira story/task deliverables to `docs/` root or `docs/html/` — those belong in `docs/epics/<epic-slug>/` (see above).

**Do not** create new `docs/<topic>.md` / `docs/html/<topic>.html` for:
- Cursor/MCP/Jira OAuth or local IDE wiring
- Conversation summaries or chat walkthroughs
- Troubleshooting notes that belong in a commit message or chat reply

When an existing doc already covers the area, **update that page** instead of adding a sibling.

### README

Link or briefly mention new capabilities in `README.md` only when they affect **getting started**, **contributing**, or **running the project**. Do not add README links for individual developer tooling.

### When unsure

1. Prefer a **chat answer** over a new doc.
2. Prefer **updating an existing doc** over creating one.
3. Ask the user once if scope is ambiguous — do not default to writing docs.
