# Agent Instructions

These instructions apply to all agents working in this repository.

## Documentation sources

- For cross-cutting project documentation under `docs/`, follow `docs/AGENTS.md`.
- For epic walkthroughs and Jira task docs, follow `docs/epics/AGENTS.md` (architecture track) and `docs/epics/code/AGENTS.md` (code teaching track).
- Epic task files live under `docs/epics/<epic-slug>/architecture/` and `docs/epics/<epic-slug>/code/` (see **Epic docs** below).

## Documentation scope (default: minimal)

Not every chat or config change needs docs. Default to **no new documentation** unless the work clearly meets a threshold below.

### Do not write docs during task implementation

**When implementing a Jira story/task (or any qualifying code change), do not generate or update documentation in the same change.**

During implementation, deliver **code and tests only**:

- Do **not** create or update `docs/epics/<epic-slug>/architecture/` or `code/` task docs
- Do **not** update `docs/epics/<epic-slug>/index.html`
- Do **not** run `scripts/render_epic_task_doc.py` or otherwise emit new HTML docs
- Do **not** expand cross-cutting `docs/` or `docs/html/` pages unless the user explicitly asks

Write or update epic walkthroughs and task docs **only when the user explicitly asks for documentation**, or as a **separate documentation pass after the implementation is complete and accepted**. Do not assume docs are part of “finishing” the coding task.

### Epic presentation walkthroughs (`docs/epics/<epic-slug>/index.html`)

This section is the **canonical, shareable** contract for epic HTML walkthroughs (formerly kept only as a Cursor rule). Follow it in any agent or IDE.

**Do not generate or update epic documentation during task implementation.** Deliver code and tests first. Write or update walkthroughs and task docs only when the user explicitly asks for documentation, or as a separate documentation pass after the implementation is complete.

Update walkthroughs **only** in that documentation pass, for code tied to a Jira epic/story/task.

Qualifying code paths: `ml/`, `ros_ws/`, `data/`, `deployment/`, `litevla/`, `scripts/` (runtime/CI), `tests/`, and versioned config that affects build, train, deploy, or robot runtime.

**Do not** update epic walkthroughs for:
- IDE, editor, or MCP setup (`.cursor/`, Cursor settings, OAuth troubleshooting)
- Questions, explanations, or reviews with no code change
- Personal dev-environment fixes (PATH, nvm, local tooling)
- One-off debugging that does not change committed project behavior
- The implementation PR or coding session itself (defer docs — see above)

When documenting (deferred / user-requested):

- Use `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`, branch names, task titles, issue IDs, code paths, and conversation context to infer the active epic. Ask only when two or more epics remain equally plausible.
- Update `docs/epics/<epic-slug>/index.html` in the documentation pass — not in the same change as coding the feature.
- Add each story/task/subtask in source order. Do not append tasks randomly; preserve the epic sequence from the Jira CSV or current board.
- For every worked task, record intent, files/modules touched, code walkthrough notes, data/control flow, validation evidence, and ADRs for meaningful technical decisions.
- Treat these pages as senior-to-junior architectural walkthroughs: explain contracts, data flow, trade-offs, and operational risks — not trivial syntax or line-by-line narration.
- Prefer visual explanation: maintain Mermaid flowcharts or sequence diagrams for task-level flows, plus HTML/SVG/interactive visuals when they clarify the code. Do **not** add C4 system-context or container diagrams to epic `index.html` pages.
- Use the standard format in `docs/epics/AGENTS.md` (architecture) and `docs/epics/code/AGENTS.md` (code teaching, including a compact **Concepts in this task** checklist). The epic `index.html` is the source of truth for walkthroughs.

### Epic task docs (`docs/epics/<epic-slug>/`)

When the user requests documentation for a **completed or in-progress Jira story/task**, create and maintain **two tracks** inside the matching epic folder:

| Track | Path | Purpose |
|-------|------|---------|
| Architecture | `docs/epics/<epic-slug>/architecture/<task-slug>.md` (+ `.html`) | System design, contracts, trade-offs |
| Code | `docs/epics/<epic-slug>/code/<task-slug>.md` (+ `.html`) | Implementation teaching for novices |

Rules:

- Infer `<epic-slug>` from Jira parent epic, CSV mapping, branch name, or changed paths (same signals as walkthrough updates).
- Use a kebab-case `<task-slug>` from the story title (example: `action-schema` for “Define discrete action schema”). Same slug in both tracks.
- Add the epic and Jira key at the top of each `.md` file; cross-link the sibling track.
- Architecture docs: executive summary, API contract and data flow, grouped implementation breakdown with risks/gotchas, verification patterns, decisions, and open questions (see `docs/epics/AGENTS.md`).
- Code docs: follow `docs/epics/code/AGENTS.md` — include a compact **Concepts in this task** checklist, then teach the implementation.
- Link both human HTML pages from the epic `index.html` story section when they exist.
- Update the epic walkthrough (`index.html`) in the **same documentation pass** as the task docs (not during coding).
- Reuse `docs/styles/doc.css` for task HTML; link with `../../../styles/doc.css` from `architecture/` or `code/`.

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
