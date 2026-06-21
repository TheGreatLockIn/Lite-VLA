# Agent Instructions

These instructions apply to all agents working in this repository.

## Documentation sources

- For project documentation under `docs/`, follow `docs/AGENTS.md`.
- For epic walkthrough format and style, follow `presentations/AGENTS.md`.

## Documentation scope (default: minimal)

Not every chat or config change needs docs. Default to **no new documentation** unless the work clearly meets a threshold below.

### Epic presentations (`presentations/<epic-slug>/index.html`)

Update **only** when you **implement or modify project code** tied to a Jira epic/story/task (from the import CSV or live Jira), in the **same change** as that code.

Qualifying code paths: `ml/`, `ros_ws/`, `data/`, `deployment/`, `litevla/`, `scripts/` (runtime/CI), `tests/`, and versioned config that affects build, train, deploy, or robot runtime.

**Do not** update presentations for:
- IDE, editor, or MCP setup (`.cursor/`, Cursor settings, OAuth troubleshooting)
- Questions, explanations, or reviews with no code change
- Personal dev-environment fixes (PATH, nvm, local tooling)
- One-off debugging that does not change committed project behavior

When you do update a presentation:
- Infer the active epic from the task title, Jira key, branch name, changed paths, CSV parent mapping, and conversation context. Ask only when two or more epics remain equally plausible.
- Add each story/task/subtask in source order. Do not append tasks randomly; preserve the epic sequence from the Jira CSV or current board.
- For every worked task, record intent, files/modules touched, code walkthrough notes, data/control flow, validation evidence, and ADRs for meaningful technical decisions.
- Prefer visual explanation: maintain Mermaid C4 diagrams for system/container views and Mermaid flowcharts or sequence diagrams for task-level flows.
- Use the standard format in `presentations/AGENTS.md`. The presentation HTML is the source of truth for epic walkthroughs.

### Project docs (`docs/`)

Create a **new** topic page only for durable knowledge a new teammate needs to build, run, train, deploy, or operate Lite-VLA (architecture, dependencies, CI, experiment logging, ROS setup, action schemas, etc.).

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
