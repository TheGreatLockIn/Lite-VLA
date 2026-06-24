# Epic documentation instructions

The `docs/epics/` folder contains living HTML walkthroughs for each Jira epic, plus paired task docs for completed stories. These files explain why the code exists, how it works, what decisions were made, and how data/control flows through the system.

**This file is the canonical source** for epic and task documentation standards. Agents should follow it whenever they implement, modify, review, or explain code tied to a Jira epic or task.

## Agent contract

When implementing, modifying, reviewing, or explaining project code, keep the matching epic and task documentation current when the root [`AGENTS.md`](../../AGENTS.md) documentation thresholds say docs are required.

- Use `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`, branch names, task titles, Jira IDs, changed paths, and conversation context to infer the active epic. Ask only when two or more epics remain equally plausible.
- Update the paired epic/task docs in source order. Do not append tasks randomly; preserve the epic sequence from Jira or the current board.
- Treat task docs as teaching artifacts for asynchronous review. A reader should understand the task purpose, how it fits the codebase, what modules/classes/functions changed, how data/control flows through them, how to run or validate the work, and what trade-offs were accepted.
- Write architectural walkthroughs, not code narration. Focus on system contracts, data integrity, trade-offs, and operational risks. Do not explain trivial syntax (for example, "here we define a function") or walk a file line-by-line.
- Explain named modules, classes, functions, commands, topics, schemas, and config keys when they are mentioned. Prefer a short walkthrough of the call path or runtime lifecycle over a bare inventory of names.
- Write like a senior engineer mentoring a junior engineer: concrete, accurate, and approachable. Define project-specific concepts the first time they appear, and connect code details back to engineering intent.
- Prefer visual explanation: maintain task-specific Mermaid flowcharts or sequence diagrams, plus HTML/SVG/interactive visuals when they improve the human `.html` counterpart. Do not default to C4 context/container diagrams unless the user explicitly asks for architecture modeling.
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

Follow the **architectural walkthrough framework** below. Section titles may vary, but the substance should be present.

### Architectural walkthrough framework

#### 1. Executive summary

Open with 2–3 sentences on the module's **architectural responsibility**: what problem it solves, what system contract it owns, and how upstream/downstream modules depend on it. This replaces a generic task blurb when code is involved.

#### 2. Reader map (optional, keep brief)

List the files to read first and why. One line per file is enough when the implementation breakdown below already teaches the code. Skip or shorten this section when it would only repeat later content.

#### 3. API contract and data flow

Show how data enters the module, is validated or transformed, and exits. Prefer a compact flow map using Mermaid or ASCII arrows (`──>`), for example:

```text
VLA text ──> parser ──> DiscreteAction ──> action_to_twist ──> (linear_x, angular_z) ──> safety gate ──> /cmd_vel
```

State the **contract** explicitly: accepted input types, output shape/units, invariants, and error behavior. Explain the main **trade-offs** behind structural choices (enum vs string, nominal table vs config clamp, strict tokens vs aliases, where fallback logic is intentionally deferred).

Keep task docs **task-local**. Do not repeat an epic-level pipeline diagram unless this task adds new detail.

#### 4. Implementation breakdown

Group code by **logical concern** (vocabulary, mapping, validation, integration), not by file order. For each group include:

- **Snippet:** a focused real excerpt from the repo (see Code snippet standard).
- **Design notes:** the engineering principle or implicit standard being applied (shared contract, single source of truth, fail-fast vs fail-safe boundary, reusable helper, etc.).
- **Risks and gotchas:** edge cases, unhandled exceptions, assumptions, missing fallbacks, or follow-up stories that own deferred behavior.

Do not paste entire files. Teach what matters for maintenance and safe extension.

#### 5. Engineering decisions

Record meaningful ADRs or design notes: alternatives rejected, consequences, and what future work must preserve. Use the ADR standard when a decision is durable.

#### 6. Verification patterns

Explain how tests, smoke scripts, or pipeline commands act as **executable documentation**. Name the **behavioral contracts** being defended (boundary clamping, strict validation, stable token order, invalid input rejection, config integration, etc.) and give exact commands to run.

#### 7. Visual explanation (when needed)

Add a diagram or visual aid when the task has multiple components, runtime steps, or a non-obvious data path.

### Minimum checklist

Each task doc should usually include:

- **Executive summary** — architectural responsibility and system fit.
- **API contract and data flow** — inputs, outputs, invariants, errors, trade-offs.
- **Implementation breakdown** — grouped snippets with design notes and risks/gotchas.
- **Verification patterns** — tests/commands and the contracts they defend.
- **Open questions** — unresolved decisions or follow-up ownership when relevant.

Prefer concise teaching paragraphs over terse bullets when explaining code. Bullets are fine for scanability, but do not leave named code elements unexplained.

## Code snippet standard

Docs should feel like a modern editor or GitHub page when they show code.

- In Markdown sources, use fenced code blocks with language tags: `python`, `bash`, `yaml`, `json`, `diff`, `html`, `text`, `mermaid`, etc.
- In human `.html` docs, render every code, CLI, config, Mermaid, and diff example as `<pre><code class="language-...">...</code></pre>` or `<pre class="mermaid">...</pre>` when Mermaid requires that form.
- Use `language-bash` for plain shell commands, `language-yaml` for YAML config, `language-python` for Python, `language-json` for JSON, and the closest Prism language for other snippets.
- Escape HTML special characters inside `<code>` blocks: `<` as `&lt;`, `>` as `&gt;`, and `&` as `&amp;`.
- For before/after code examples, use Prism diff-highlight compatible blocks such as `<pre><code class="language-diff-python diff-highlight">...</code></pre>`.
- Human `.html` pages must load Prism plus `docs/scripts/doc-code.js` so snippets render as editor-style highlighted blocks (see [`docs/AGENTS.md`](../AGENTS.md)).
- Prefer short, real snippets from the repo over invented pseudocode. Show enough surrounding lines for a junior engineer to understand the symbol in context.
- Do not replace prose with giant code dumps. Pair each snippet with a focused explanation of what to notice.

## Required walkthrough format

Each epic `index.html` keeps stories/tasks in source order. For the active story/task, update or add:

- **Status:** Planned, In Progress, Blocked, Complete, or Superseded.
- **Intent:** Architectural responsibility in 1–2 sentences — what contract this story owns in the epic.
- **Implementation Walkthrough:** Grouped snippets with design notes and risks/gotchas; avoid line-by-line narration. Use repo-relative paths in `<code>` tags.
- **Data And Control Flow:** Contract, inputs/outputs, invariants, error paths, and trade-offs. Task-local diagram or ASCII map when helpful.
- **Visuals:** Mermaid flowcharts/sequence diagrams or HTML/SVG when they teach behavior better than prose. Avoid duplicated diagrams across epic and task pages.
- **ADR Notes:** Context, decision, alternatives rejected, consequences, and status.
- **Verification Patterns:** Tests, smoke commands, or pipeline evidence — and which behavioral contracts they defend.
- **Open Questions:** Deferred logic, assumptions, or ownership gaps future teammates must resolve.

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

Use Mermaid blocks embedded in HTML for task-local flows:

```html
<pre class="mermaid">
flowchart TD
  Input["Input"]
  Module["Changed module"]
  Output["Output"]
  Input --> Module --> Output
</pre>
```

Use diagrams to teach the runtime lifecycle or data path, not just to decorate the page. Do not duplicate an epic-level pipeline diagram inside a task doc unless the task adds new detail.

## Style rules

- Keep epic walkthroughs at `docs/epics/<epic-slug>/index.html`.
- Keep task docs as paired `.md` + `.html` siblings in the same epic folder.
- Link walkthrough stylesheets with `../../styles/presentation.css`.
- Link task doc stylesheets with `../../styles/doc.css`.
- Preserve the warm-neutral project styling inherited from `docs/styles/doc.css`.
- Keep updates concrete and readable. Do not compress task docs into bare module lists; include enough explanation for asynchronous review and junior-engineer onboarding.
- Never invent completed work. If a page is seeded from Jira but implementation has not been verified, leave it marked as Planned or Seeded.
