# Presentation Documentation Instructions

The `presentations/` folder contains living, human-facing HTML walkthroughs for each epic. These files explain why the code exists, how it works, what decisions were made, and how data/control flows through the system.

## When To Update

Update the relevant epic HTML whenever you:

- implement or modify code for a story, task, or subtask;
- add tests, scripts, configs, schemas, ROS nodes, ML modules, data tooling, deployment logic, or docs that change the architecture;
- make or reverse a meaningful technical decision;
- discover a constraint, risk, trade-off, or integration detail future teammates need to understand.

Do this in the same change as the implementation. Do not wait for the epic to finish.

## How To Infer The Epic

Teammates should not need to specify the epic manually. Infer it from:

- Jira story/task title in the prompt, branch, commit message, PR, or issue;
- IDs and parent mapping in `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`;
- changed paths (`ros_ws/`, `ml/`, `data/`, `deployment/`, `scripts/`, `docs/`, etc.);
- task wording such as "parser", "dataset", "LoRA", "benchmark", "GGUF", or "demo";
- nearby existing sections in the presentation files.

If two epics remain equally plausible after checking those signals, ask the user one concise clarification question.

## Required Update Format

Each epic page keeps stories/tasks in source order. For the active story/task, update or add:

- **Status:** Planned, In Progress, Blocked, Complete, or Superseded.
- **Intent:** What the task is trying to accomplish for the epic.
- **Implementation Walkthrough:** The important modules, functions, classes, configs, commands, and tests. Use repo-relative paths in `<code>` tags.
- **Data And Control Flow:** Inputs, outputs, state transitions, ROS topics/messages, model inputs/outputs, files written, or benchmark artifacts.
- **Visuals:** Prefer Mermaid C4 diagrams for system/container views and Mermaid flowcharts/sequence diagrams for task-level behavior.
- **ADR Notes:** For each meaningful decision, record context, decision, alternatives rejected, consequences, and status.
- **Validation:** Tests, smoke commands, manual checks, benchmark results, or why validation was not run.
- **Open Questions:** Anything future teammates must resolve.

## ADR Standard

Use short ADR entries inside the task section:

```text
ADR: <short decision title>
Status: Proposed | Accepted | Superseded
Context: <why this mattered>
Decision: <what changed>
Alternatives Rejected: <other options and why not>
Consequences: <trade-offs, follow-up work, impact>
```

## Visual Standard

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

## Style Rules

- Keep files as standalone HTML pages under `presentations/<epic-slug>/index.html`.
- Link the shared presentation stylesheet with `../styles/presentation.css`.
- Preserve the warm-neutral project styling inherited from `docs/styles/doc.css`.
- Keep updates concise but concrete. Prefer a diagram plus a few precise notes over long prose.
- Never invent completed work. If a page is seeded from Jira but implementation has not been verified, leave it marked as Planned or Seeded.
