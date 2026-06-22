# Epic documentation instructions

The `docs/epics/` folder contains living HTML walkthroughs for each Jira epic, plus paired task docs for completed stories. These files explain why the code exists, how it works, what decisions were made, and how data/control flows through the system.

## Layout

```
docs/epics/
├── AGENTS.md                 # this file
├── index.html                # epic index (human)
└── <epic-slug>/
    ├── index.html            # epic walkthrough (required)
    ├── <task-slug>.md        # task doc — agent source of truth
    └── <task-slug>.html      # task doc — human browser page
```

Shared styles: `docs/styles/presentation.css` (walkthroughs) and `docs/styles/doc.css` (task docs and cross-cutting topics).

## When to update

Update the relevant epic whenever you:

- implement or modify code for a story, task, or subtask;
- add tests, scripts, configs, schemas, ROS nodes, ML modules, data tooling, deployment logic, or docs that change the architecture;
- add or update **task documentation** for a Jira story (`.md` + `.html` in the epic folder);
- make or reverse a meaningful technical decision;
- discover a constraint, risk, trade-off, or integration detail future teammates need to understand.

Do this in the same change as the implementation. Do not wait for the epic to finish.

## How to infer the epic

Teammates should not need to specify the epic manually. Infer it from:

- Jira story/task title in the prompt, branch, commit message, PR, or issue;
- IDs and parent mapping in `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`;
- changed paths (`ros_ws/`, `ml/`, `data/`, `deployment/`, `scripts/`, `docs/epics/`, etc.);
- task wording such as "parser", "dataset", "LoRA", "benchmark", "GGUF", or "demo";
- nearby existing sections in the epic walkthrough files.

If two epics remain equally plausible after checking those signals, ask the user one concise clarification question.

## Epic task documentation

When a Jira story/task produces durable docs (schemas, APIs, runbooks), store them in the **same epic folder** as the walkthrough:

```
docs/epics/<epic-slug>/
├── index.html              # epic walkthrough (required)
├── <task-slug>.md          # agent source of truth
└── <task-slug>.html        # human browser page
```

Rules:

- **Location:** `docs/epics/<epic-slug>/` — never `docs/` root or `docs/html/`.
- **Naming:** kebab-case `<task-slug>` from the story title (`action-schema`, `discrete-action-parser`, etc.).
- **Header:** start each `.md` with epic name, Jira key, and a link to the `.html` pair.
- **Styles:** link `../../styles/doc.css` from task HTML; include viewport meta and `table-wrap` for tables (same as `docs/AGENTS.md`).
- **Cross-link:** add a link from the story section in `index.html` to the task HTML.
- **Agents:** read and edit `.md` only; do not read task or walkthrough `.html` files (derive HTML from `.md` when updating).

## Required walkthrough format

Each epic `index.html` keeps stories/tasks in source order. For the active story/task, update or add:

- **Status:** Planned, In Progress, Blocked, Complete, or Superseded.
- **Intent:** What the task is trying to accomplish for the epic.
- **Implementation Walkthrough:** The important modules, functions, classes, configs, commands, and tests. Use repo-relative paths in `<code>` tags.
- **Data And Control Flow:** Inputs, outputs, state transitions, ROS topics/messages, model inputs/outputs, files written, or benchmark artifacts.
- **Visuals:** Prefer Mermaid C4 diagrams for system/container views and Mermaid flowcharts/sequence diagrams for task-level behavior.
- **ADR Notes:** For each meaningful decision, record context, decision, alternatives rejected, consequences, and status.
- **Validation:** Tests, smoke commands, manual checks, benchmark results, or why validation was not run.
- **Open Questions:** Anything future teammates must resolve.

## ADR standard

Use short ADR entries inside the task section:

```text
ADR: <short decision title>
Status: Proposed | Accepted | Superseded
Context: <why this mattered>
Decision: <what changed>
Alternatives Rejected: <other options and why not>
Consequences: <trade-offs, follow-up work, impact>
```

## Visual standard

Use Mermaid blocks embedded in HTML:

```html
<pre class="mermaid">
C4Container
title Epic Container View
Person(team, "Team", "Builds and reviews the feature")
System_Boundary(repo, "Lite-VLA") {
  Container(code, "Changed Module", "Python/ROS/config", "What this task changed")
  Container(test, "Validation", "pytest/manual benchmark", "Evidence gathered")
}
Rel(team, code, "implements")
Rel(code, test, "validated by")
</pre>
```

For task internals, use `flowchart TD` or `sequenceDiagram` when C4 is too high-level.

## Style rules

- Keep epic walkthroughs at `docs/epics/<epic-slug>/index.html`.
- Keep task docs as paired `.md` + `.html` siblings in the same epic folder.
- Link walkthrough stylesheets with `../../styles/presentation.css`.
- Link task doc stylesheets with `../../styles/doc.css`.
- Preserve the warm-neutral project styling inherited from `docs/styles/doc.css`.
- Keep updates concise but concrete. Prefer a diagram plus a few precise notes over long prose.
- Never invent completed work. If a page is seeded from Jira but implementation has not been verified, leave it marked as Planned or Seeded.
