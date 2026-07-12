# Epic documentation instructions

The `docs/epics/` folder contains living HTML walkthroughs for each Jira epic, plus paired task docs for completed stories. These files explain why the code exists, how it works, what decisions were made, how data/control flows through the system, and how a newcomer should learn to reason about the engineering behind the code.

**This file is the canonical source** for epic and task documentation standards. Agents should follow it whenever they implement, modify, review, or explain code tied to a Jira epic or task.

## Agent contract

When implementing, modifying, reviewing, or explaining project code, keep the matching epic and task documentation current when the root [`AGENTS.md`](../../AGENTS.md) documentation thresholds say docs are required.

- Use `LiteVLA_Edge_Jira_TeamManaged_Kanban_IMPORT_READY.csv`, branch names, task titles, Jira IDs, changed paths, and conversation context to infer the active epic. Ask only when two or more epics remain equally plausible.
- Update the paired epic/task docs in source order. Do not append tasks randomly; preserve the epic sequence from Jira or the current board.
- Treat task docs as teaching artifacts for asynchronous review and code mastery. A reader dropping into the project cold should understand the task purpose, how it fits the codebase, what modules/classes/functions changed, how data/control flows through them, why the code is shaped that way, how to run or validate the work, what trade-offs were accepted, and what instincts a senior engineer applies when debugging or extending it.
- Write architectural walkthroughs, not code narration. Focus on system contracts, data integrity, trade-offs, and operational risks. Do not explain trivial syntax (for example, "here we define a function") or walk a file line-by-line.
- Explain named modules, classes, functions, commands, topics, schemas, and config keys when they are mentioned. Prefer a short walkthrough of the call path or runtime lifecycle over a bare inventory of names.
- Write like a senior engineer mentoring a junior engineer: concrete, accurate, and approachable. Define project-specific concepts the first time they appear, and connect code details back to engineering intent.
- Prefer visual explanation: maintain task-specific Mermaid flowcharts or sequence diagrams, plus HTML/SVG/interactive visuals when they improve the human `.html` counterpart. Do not default to C4 context/container diagrams unless the user explicitly asks for architecture modeling.
- Record validation evidence, open risks, and ADRs for meaningful technical decisions. Never invent completed work; mark unverified work as Planned, Seeded, or explicitly unvalidated.
- For file placement, `.md`/`.html` pairing, and HTML generation rules, also follow [`docs/AGENTS.md`](../AGENTS.md).

## Learner-centered standard

The docs must be learner-centered, not artifact-centered. They should not merely answer "what exists?" They should also answer "how should I think about this?"

Every substantial epic/task doc should teach four layers:

| Layer | Reader question to answer |
|-------|---------------------------|
| **System layer** | What role does this task/module play in Lite-VLA, and what problem does it solve? |
| **Code layer** | Which files, functions, classes, schemas, topics, scripts, or configs implement the behavior, and why is the code organized that way? |
| **Concept layer** | What general robotics, ML, data, or software engineering idea does this represent? |
| **Mastery layer** | How would a senior engineer debug, extend, test, or avoid mistakes in this area? |

Do not leave named artifacts to the reader's imagination. If a doc mentions `data/schema/episode.schema.json`, `commands.jsonl`, `/cmd_vel`, `Twist`, `DataLoader`, LoRA, GGUF, a ROS launch file, or a config key, explain what that artifact is, why it exists, how it connects to neighboring components, and what a beginner should notice about it.

## Required teaching anchors

Task docs may vary their exact headings, but substantial docs should include the following teaching anchors unless there is a clear reason to omit one. Short seeded placeholders may stay brief until implementation starts.

### Mental model

Near the top, include a plain-English mental model:

```markdown
## Mental model

Think of this module as a ______.

It exists because ______.

The key engineering tension is ______.

A beginner mistake is ______.

A senior engineer watches for ______.
```

This section should connect the task to a reusable engineering instinct. For example, a heartbeat controller is not just "a ROS node"; it is a safety-owned last-mile publisher that converts irregular upstream intent into steady robot actuation.

### Backstory: why this exists

Explain the problem that existed before this task, the naive solution a beginner might reach for, why that solution breaks down, and why the chosen design is a better fit. Prefer this shape:

```markdown
## Backstory: why this exists

Before this module existed, the system had the following problem...

The naive solution would be...

That breaks because...

So this design chooses...

This pattern appears in real systems as...
```

### Concept primer and vocabulary

Define project-local and domain-local terms before asking the reader to understand diagrams, tables, or code. Keep primers short and task-local; link out when a full topic page exists.

Use a vocabulary table for terms a novice may pretend to understand:

| Term | Meaning in this project |
|------|-------------------------|
| `Twist` | A ROS motion message; Lite-VLA mainly uses `linear.x` and `angular.z`. |
| JSONL | One JSON object per line, useful for append-only logs and stream processing. |
| Schema | A machine-checkable contract for what fields a record must contain. |

### Guided code reading and file index

When files are referenced, include a guided reading path instead of a bare file list. Each entry should say what the file is for, what to inspect first, and what can be ignored on a first pass.

```markdown
## Guided code reading

Read these in order:

1. `teleop_utils.py`
   - First understand how key states become `(linear_x, angular_z)`.
   - Ignore ROS for now; this file is pure logic.

2. `teleop_keyboard.py`
   - Now see how terminal input is converted into calls to the pure helper.

While reading, ask:
- Where does data enter?
- Where is it validated?
- Where can it fail?
- Who owns the final side effect?
```

For larger docs, add a compact file index:

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `commands.jsonl` | Append-only action log | Replays and labels what the robot was asked to do | One row's timestamp, action, and source fields |
| `frames/*.png` | Captured camera images | Pair visual state with action labels | Whether filenames align with command timestamps |

### Naive approach vs chosen approach

Show the design judgment explicitly. This teaches why the implementation is not merely accidental.

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Direct writer to `/cmd_vel` | Fewer nodes and less indirection | Creates competing actuation owners and bypasses safety timing |
| Single heartbeat owner | Adds a routing step | Gives the system one safety boundary and one owner of physical motion |

### Failure modes and debugging path

Verification commands say whether things work; failure-mode tables teach how to recover when they do not.

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Robot does not move | `/cmd_vel` is not being published | `ros2 topic echo /cmd_vel` | Check the heartbeat node, control mode, and timeouts |
| Dataset loader crashes | Missing image path or malformed record | Run the validator before training | Fix the JSONL/image layout or schema violation |

### Engineering principle and active learning

State the reusable principle the task teaches, then add active checks that force the reader to reason.

```markdown
## Engineering principle taught by this task

This task teaches the "single owner of side effects" pattern...

## Active learning checks

Before modifying this module, answer:

1. Why does this component publish intent instead of commanding the final side effect directly?
2. What happens if the upstream producer crashes mid-command?
3. Which component is responsible for detecting stale data?
4. How would you test that stale data becomes safe output?

## Small modification exercise

Change one safe parameter, then verify the config is loaded, the clamp still applies, tests pass, and the runtime behavior stays within the new limit.
```

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

Task docs must be unified mentorship tutorials. There is exactly one consolidated document per story (do not split into a surface task page and a separate code walkthrough page). The main body of this document must be the detailed, learner-oriented walkthrough, with supplemental practical engineering context placed at the end.

Follow the **mentorship walkthrough structure** below:

### Mentorship walkthrough structure

#### 1. Goal & Objective
A 1–2 sentence statement of what this module achieves.

#### 2. Why We Need It
An explanation of the engineering problem, its operational risks (e.g. GPU crashes during fine-tuning), and why a loose approach is unacceptable.

#### 3. How to Start Thinking About It (Developer Thought Process)
A step-by-step sequential breakdown of the thought process behind the design (e.g. why we chose a frozen dataclass, how paths are resolved cross-platform, why lazy loading avoids memory issues).

#### 4. Imports & Global Constants Explained
An annotated markdown table listing every import, its purpose in this module, and hyperlinked references to the general `/docs/concepts/` pages (e.g., Python Primer) where the underlying language feature or library is explained. Key global constants should also be documented here with their engineering rationales.

#### 5. Class & Data-Flow Diagrams
A Mermaid flowchart illustrating the ingestion, transformation, and export data paths.

#### 6. Detailed Code Walkthrough
A granular, logical walkthrough grouping snippets from the source code. Discuss:
- Custom classes and exceptions.
- Core functions (intent, parameters, return values, choices made, system connections).
- Key syntax (such as generator `yield` logic, seed-locked deterministic generators, and regex patterns).

---

### Practical Engineering Context

#### 1. Executive Summary
The module's architectural responsibility and system dependencies.

#### 2. Naive Approach vs Chosen Approach
An explicit trade-off table comparing simple solutions (e.g. CSVs, wall-clock ROS stamps) to the robust production choices made.

#### 3. ADR Log Summary
Short ADR entries detailing context, decision, alternatives rejected, and consequences.

#### 4. Verification Patterns & Failure Modes
Testing commands and a detailed debugging table mapping symptoms to causes, diagnostic tools, and fixes.

#### 5. Active Learning Checks & Exercises
Questions and a low-risk code exercise encouraging hands-on verification.

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
