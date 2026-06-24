# Epic documentation instructions

The `docs/epics/` folder contains living HTML walkthroughs for each Jira epic, plus paired task docs for completed stories. These files explain why the code exists, how it works, what decisions were made, and how data/control flows through the system.

**This file is the canonical source** for epic and task documentation standards. Agents should follow it whenever they implement, modify, review, or explain code tied to a Jira epic or task.

## Agent contract

When implementing, modifying, reviewing, or explaining project code, keep the matching epic and task documentation current when the root [`AGENTS.md`](../../AGENTS.md) documentation thresholds say docs are required.

- Use `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`, branch names, task titles, Jira IDs, changed paths, and conversation context to infer the active epic. Ask only when two or more epics remain equally plausible.
- Update the paired epic/task docs in source order. Do not append tasks randomly; preserve the epic sequence from Jira or the current board.
- Treat task docs as teaching artifacts for asynchronous review. A reader should understand the task purpose, how it fits the codebase, what modules/classes/functions changed, how data/control flows through them, how to run or validate the work, and what trade-offs were accepted.
- Explain named modules, classes, functions, commands, topics, schemas, and config keys when they are mentioned. Prefer a short walkthrough of the call path or runtime lifecycle over a bare inventory of names.
- Write like a senior engineer mentoring a junior engineer: concrete, accurate, and approachable. Define project-specific concepts the first time they appear, and connect code details back to engineering intent.
- Prefer visual explanation: maintain Mermaid C4 diagrams for system/container views, Mermaid flowcharts or sequence diagrams for task-level flows, and HTML/SVG/interactive visuals when they improve the human `.html` counterpart.
- Record validation evidence, open risks, and ADRs for meaningful technical decisions. Never invent completed work; mark unverified work as Planned, Seeded, or explicitly unvalidated.
- For file placement, `.md`/`.html` pairing, and HTML generation rules, also follow [`docs/AGENTS.md`](../AGENTS.md).

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
- **Teaching depth:** explain the task purpose, where it sits in the epic, the important modules/classes/functions, the runtime flow, validation commands, design trade-offs, and any risks or follow-ups.
- **Styles:** link `../../styles/doc.css` from task HTML; include viewport meta and `table-wrap` for tables (same as `docs/AGENTS.md`).
- **Cross-link:** add a link from the story section in `index.html` to the task HTML.
- **Agents:** read and edit `.md` only; do not read task or walkthrough `.html` files (derive HTML from `.md` when updating).

## Task doc depth standard

Task docs must be more than a summary or inventory. When a page names a module, class, function, ROS topic, schema, config key, script, launch file, or command, explain it in the capacity that helps a junior engineer read and maintain the code.

Each task doc should usually include:

- **Purpose and fit:** what the task adds to Lite-VLA, why the epic needs it, and what behavior would be missing without it.
- **Reader map:** the files to read first, the entry points, and the order in which a human should inspect the code.
- **Code walkthrough:** the responsibilities of each important symbol, how methods call each other, what state is stored, and which boundaries are intentionally kept small or reusable.
- **Data and control flow:** inputs, outputs, message types, ROS topics, model tensors, file artifacts, command-line flags, error paths, and stop/cleanup behavior.
- **Engineering notes:** why the implementation is shaped this way, what alternatives were avoided, what assumptions are encoded, and what future work should preserve.
- **Validation:** exact tests, launch commands, smoke checks, manual observations, or a clear statement that validation was not run.
- **Visual explanation:** at least one diagram or visual aid when the task has multiple components, runtime steps, or a non-obvious data flow.

Prefer concise teaching paragraphs over terse bullets when explaining code. Bullets are fine for scanability, but do not leave named code elements unexplained.

## Required walkthrough format

Each epic `index.html` keeps stories/tasks in source order. For the active story/task, update or add:

- **Status:** Planned, In Progress, Blocked, Complete, or Superseded.
- **Intent:** What the task is trying to accomplish for the epic.
- **Implementation Walkthrough:** The important modules, functions, classes, configs, commands, and tests, with enough explanation to understand each named item. Use repo-relative paths in `<code>` tags.
- **Data And Control Flow:** Inputs, outputs, state transitions, ROS topics/messages, model inputs/outputs, files written, or benchmark artifacts.
- **Visuals:** Prefer Mermaid C4 diagrams for system/container views, Mermaid flowcharts/sequence diagrams for task-level behavior, and HTML/SVG/interactive visuals when they teach the concept better than prose.
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

For task internals, use `flowchart TD` or `sequenceDiagram` when C4 is too high-level. Use diagrams to teach the runtime lifecycle or data path, not just to decorate the page.

## Style rules

- Keep epic walkthroughs at `docs/epics/<epic-slug>/index.html`.
- Keep task docs as paired `.md` + `.html` siblings in the same epic folder.
- Link walkthrough stylesheets with `../../styles/presentation.css`.
- Link task doc stylesheets with `../../styles/doc.css`.
- Preserve the warm-neutral project styling inherited from `docs/styles/doc.css`.
- Keep updates concrete and readable. Do not compress task docs into bare module lists; include enough explanation for asynchronous review and junior-engineer onboarding.
- Never invent completed work. If a page is seeded from Jira but implementation has not been verified, leave it marked as Planned or Seeded.
