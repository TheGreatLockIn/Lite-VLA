# Code teaching documentation instructions

This file defines how agents must explain **implementation code** in this repository.

**This file is the canonical source** for code-teaching task docs. For system contracts, data flow, trade-offs, and ADRs, follow [`../AGENTS.md`](../AGENTS.md) (architecture track). For HTML pairing and agent editing rules, also follow [`../../AGENTS.md`](../../AGENTS.md).

## Two documentation tracks

Each Jira task that touches project code may produce **two** paired docs in the same epic:

| Track | Folder | Purpose | Canonical instructions |
|-------|--------|---------|------------------------|
| **Architecture** | `docs/epics/<epic-slug>/architecture/` | Why the feature exists, system contract, data/control flow, trade-offs, ADRs, operational risks | [`../AGENTS.md`](../AGENTS.md) |
| **Code** | `docs/epics/<epic-slug>/code/` | How the code works — read the implementation, understand syntax, follow data through the pipeline | this file |

Do **not** merge these tracks into one mega-doc. The architecture doc teaches **system thinking**. The code doc teaches **reading and writing the implementation**.

Cross-link between tracks, but do not duplicate:

- Architecture doc: link to the code doc for “how to read the implementation.”
- Code doc: link to the architecture doc for “why this design exists” and the system contract.

## Purpose

These docs are **not** feature summaries, release notes, or Jira status updates.

The purpose is to help a motivated reader **understand the code that was written**: what each file does, how data moves, what the syntax means, and how the pieces connect.

Assume the reader may be new to Python or the libraries involved. Write clearly — like a senior engineer explaining code on a shared screen — without turning the doc into a rigid worksheet.

**Success criterion:** after reading the doc, the reader can open the source files, follow the execution path, and explain what the code is doing line by line in their own words.

## Why agents produce summaries instead of lessons

Common failure modes:

| Failure | What the agent writes | What the reader still lacks |
|---------|----------------------|----------------------------|
| **Labeling ≠ teaching** | “`format_user_text` builds the full user prompt string.” | What the code actually does step by step |
| **Rigid subsection spam** | Every function gets identical headings that do not fit | A readable explanation of the logic |
| **Architecture bleed** | Mental models and ADRs in `code/` | Implementation walkthrough |
| **Test narration** | Arrange / Act / Assert for every test | Understanding the production code |

**Good explanation (excerpt):**

> `format_user_text` is a method on `PromptTemplate`, so Python passes the template object as `self`. It builds `action_list` with `", ".join(ACTION_NAMES)`, then assembles three text blocks (preamble, goal line, action list), drops empty blocks, and joins the rest with `"\n\n"`. For instruction `"Move toward the red cone"`, the middle block becomes `"Goal: Move toward the red cone"`.

That is **one flowing explanation** with syntax called out inline — not twelve mandatory subheadings.

## Agent contract

**Do not write code teaching docs during task implementation.** Deliver code and tests first. Create or update these docs only when the user explicitly asks for documentation, or in a separate pass after the implementation is complete (see root [`AGENTS.md`](../../../AGENTS.md)).

When writing docs for a Jira epic or task:

1. Update the matching **architecture** doc per [`../AGENTS.md`](../AGENTS.md) in the same documentation pass.
2. Create or update the matching **code teaching** doc in that same documentation pass (not while coding).
3. Infer the active epic from Jira keys, CSV parent mapping, branch names, changed paths, and conversation context. Ask only when two or more epics remain equally plausible.
4. Use kebab-case `<task-slug>` from the story title (`dataset-loader`, `configure-lora-fine-tuning`, etc.).
5. Edit **`.md` only**; derive `.html` from `.md` (agents must not read HTML docs as input).
6. Link both docs from the epic `index.html` story section.
7. Never invent completed work. Mark unverified sections as Planned, Seeded, or explicitly unvalidated.

Qualifying code paths: `ml/`, `ros_ws/`, `data/`, `deployment/`, `litevla/`, `scripts/` (runtime/CI), `tests/`, and versioned config that affects build, train, deploy, or robot runtime.

## File layout

```
docs/epics/<epic-slug>/
├── index.html                              # epic walkthrough (HTML only)
├── architecture/
│   ├── <task-slug>.md
│   └── <task-slug>.html
└── code/
    ├── <task-slug>.md                      # agent source of truth
    └── <task-slug>.html
```

Each `.md` file must start with:

- Epic name and Jira key(s)
- Task status when known (Planned, In Progress, Complete)
- Link to the paired `.html` file (same folder)
- Link to the sibling track doc when it exists

Styles: link `../../../styles/doc.css` from task HTML under `architecture/` or `code/`.

Render HTML with [`scripts/render_epic_task_doc.py`](../../../scripts/render_epic_task_doc.py).

## Mandatory completeness

When a task touches code, the code teaching doc must explain **the implementation itself**, not summarize it.

**Default rule:** every touched code file gets a walkthrough section. Explain **every** function, method, class, and module-level constant defined in those files.

**Do not copy the architecture doc.** Link to it for “why”; teach “how the code works” here.

**Do not explain tests.** Mention the test file path and `pytest` command under “How to run and verify” only. Test logic belongs in the test source, not the walkthrough.

External code the task **calls but did not touch**: one short sentence on what it returns, plus a link to its doc if one exists. Do not re-teach the whole dependency.

## What these docs are not

- Architecture walkthroughs (those live in `architecture/`)
- Test-by-test narration or Arrange / Act / Assert writeups
- Break-and-fix exercise sheets
- “What this code does NOT do” boundary tables
- Beginner Q&A worksheets
- Feature summaries or Jira status updates

---

## Required document order

Every **Full code teaching** doc follows this order:

| # | Section | Role |
|---|---------|------|
| 1 | **Files touched** | **First content section** — every file this task created or modified |
| 2 | **Plain-English purpose** | 2–4 sentences; link architecture doc for “why” |
| 3 | **Concepts in this task** | Compact checklist of ideas/skills to learn — names only, low token cost |
| 4 | **How to run and verify** | Copy-paste commands; what success looks like (e.g. `N passed`) — **no test walkthroughs** |
| 5 | **Follow one example through the pipeline** | Central chapter — one canonical input traced stage by stage with values |
| 6 | **Related dependencies** | Brief links/contracts for imports from other packages (not a Q&A table) |
| 7 | **File walkthroughs** | One section per touched file — explain the code in prose |

Optional at the end: short “Check your understanding” questions (3–5 max), only if they help — not required worksheets.

Do not start with Jira metadata beyond the header block. **Files touched comes first.**

---

## 1. Files touched

List **every** file this task created or modified. This is the orientation map at the top of the doc.

Use a table:

| File | Role in this task |
|------|-------------------|
| `litevla/training/lora.py` | LoRA config loading and adapter setup |
| `configs/lora/smolvlm.yaml` | Default hyperparameters for SmolVLM LoRA |
| `tests/test_lora_config.py` | Automated checks (run via pytest; not explained in this doc) |

Add one sentence per row if the role is not obvious from the path.

**Include:** Python modules, configs, schemas, CLI scripts the task added/changed.

**Exclude from walkthroughs:** `__pycache__/*.pyc` (generated bytecode — not source). Mention in one line if a beginner asks.

---

## 3. Concepts in this task

A **short checklist** of language features, libraries, and project patterns the reader should understand for this task. Purpose: skim what to learn **without** a long primer section or external concept library.

Rules:

- Bullet list only (or a two-column table: concept | where it shows up). Aim for **5–15 items**.
- **Names / phrases only** — no tutorials, no code samples, no “Overview / When to use” blocks.
- Cover syntax (e.g. dataclasses, generators), libraries (e.g. PEFT, YAML), and domain ideas (e.g. LoRA rank, assistant-only masking) that appear in this task.
- Do **not** create or link a `docs/concepts/` library. Explain details later in file walkthroughs.

```markdown
## Concepts in this task

- Dataclasses (`LoraAdapterConfig`)
- YAML config loading (`yaml.safe_load`)
- Keyword-only arguments (`*` in signatures)
- Registry dictionaries (`LORA_TARGET_SPECS`)
- LoRA / PEFT adapters (`target_modules`, `layers_pattern`)
- Trainable vs frozen parameters
```

---

## 5. Follow one example through the pipeline

The **main narrative chapter**. Pick one small real example (config snippet, JSONL row, CLI invocation) and trace it through every major stage. Reuse the **same example** throughout — do not switch mid-doc.

For each stage include:

1. **Stage title** — which function runs, with file path
2. **Input at this stage** — concrete value
3. **Output at this stage** — concrete value after the step
4. **Variable trace** — table of important names → values after key lines (when helpful)
5. **Type transition** — when representation changes (JSON text → dict → dataclass, etc.)

Optional pipeline diagram:

```text
input artifact
    ↓
reader / loader
    ↓
core transform
    ↓
output artifact
```

Teach type transitions when the task crosses them (JSON on disk vs Python dict vs dataclass).

---

## 6. Related dependencies

Brief section — **not** a beginner Q&A table. For each important import from another project module or schema file:

- Name and one-line role
- Link to architecture or code doc if it exists

```markdown
## Related dependencies

| Dependency | Role in this task |
|------------|-------------------|
| `litevla.training.format.SFTExample` | Input shape the LoRA loader expects |
| `configs/lora/smolvlm.yaml` | Default training hyperparameters |
```

Skip dependencies that are standard library only — explain them inline in file walkthroughs when they matter.

---

## 7. File walkthroughs

One `## File walkthrough: \`path\`` section per touched file, in a sensible reading order (often: types/config → core logic → `__init__.py` → CLI).

### Per-file structure

1. **What this file is for** — one short paragraph
2. **Imports** — table: import line, plain meaning, why this file needs it
3. **Module-level constants, classes, registries** — explain each
4. **Functions and methods** — see below

### How to explain functions (natural walkthrough)

**Do not** use a fixed checklist of subheadings on every function. Explain the code in **clear prose**, walking through the body in order. Mix general syntax teaching with task-specific behavior.

**Include when relevant (woven into the explanation, not as mandatory headings):**

- What the function receives and returns, with a **concrete example** when it helps
- Line-by-line or chunk-by-chunk logic for non-trivial bodies
- Syntax callouts inline: what `self`, `.join`, `yield`, `@dataclass`, `*` (keyword-only), etc. mean **on these lines**
- Variable traces as tables or inline when values change in non-obvious ways
- Where the function is called from in this task

**Do not include:**

- “Beginner summary” / “Why this function exists” as separate boilerplate headings
- “Why not simpler?”
- “Worked micro-example” as a labeled section (use examples inside the prose)
- “What can fail”
- “Tests (Arrange / Act / Assert)” or any test explanation
- “Beginner trap” / “Predict the output” as required labels

**Heart-of-task rule:** the file that owns the core logic (e.g. `lora.py`, `format.py`, main ROS node) gets the **longest** walkthrough. Helper one-liners can be shorter but still explain what they do.

### Code chunk format (when logic is dense)

For non-trivial blocks, show a short code excerpt then explain it:

````markdown
### `load_lora_config`

This function reads a YAML file and returns a `LoraConfig` dataclass.

```python
def load_lora_config(path: Path) -> LoraConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return LoraConfig(**raw)
```

`path.read_text(encoding="utf-8")` reads the whole file as a string. `yaml.safe_load` parses YAML into a Python dict. `LoraConfig(**raw)` unpacks dict keys as keyword arguments to build the dataclass — so the YAML keys must match field names on `LoraConfig`.

For `configs/lora/smolvlm.yaml`, the returned object might have `r=8`, `lora_alpha=16`, etc.
````

Cite real line ranges when helpful, e.g. `` `litevla/training/lora.py` lines 40–58 ``.

---

## How to run and verify

Copy-paste commands only:

```bash
pytest tests/test_lora_config.py -q
python scripts/your_script.py --help
```

State expected outcome (`6 passed`, file written, etc.). **Do not** walk through individual test functions.

---

## Anti-patterns (automatic fail)

| Anti-pattern | Why it fails |
|--------------|--------------|
| Architecture doc pasted into `code/` | Reader gets “why” twice, no “how” |
| Files touched buried below long sections | Reader cannot orient |
| Identical subheadings on every function | Unreadable; sections empty or redundant |
| “See source for details” | Defeats the purpose |
| Full test file explained | Tests are not the teaching target |
| Break-and-fix / observe–trace–modify worksheets | Wrong doc type |
| “What this code does NOT do” table | Clutters; say what it **does** in prose |
| Beginner Q&A table for dependencies | Use short related-dependencies table instead |
| Long concept primers or tutorials in this section | Keep **Concepts in this task** to a short name-only checklist |
| Missing **Concepts in this task** checklist | Reader cannot skim what to learn |
| Function labeled in one sentence with no body explanation | Labeling, not teaching |

---

## Quality gate

Before saving a code teaching doc, verify:

### Structure

1. **Files touched** is the **first** section after the header block.
2. **Concepts in this task** is a short name-only checklist (not a primer).
3. **Pipeline chapter** exists with one canonical example traced through stages.
4. **File count:** touched code files = number of `## File walkthrough:` sections.
5. **Function coverage:** every `def` in touched Python files is explained in its file section.
6. **Import tables:** every import line in each touched file appears in that file’s imports table.

### Explanation quality

7. Heart-of-task file has the deepest walkthrough.
8. Syntax is explained **in context** (inline or in chunks), not only in a detached glossary.
9. No mandatory “Why not simpler?”, “What can fail”, or test breakdown sections.
10. Doc does not duplicate the architecture doc.

### Excluded (must be absent)

11. No Observe → Trace → Modify section.
12. No break-and-fix lessons.
13. No “What this code does NOT do” section.
14. No beginner questions answered / Q&A dependency section.
15. No per-test Arrange / Act / Assert writeups.
16. No long concept primers, concept-library links, or tutorial subsections under **Concepts in this task**.
17. Docs were not written during the coding task — only in a deferred documentation pass.

---

## Relationship to architecture docs

| Question | Architecture doc | Code doc |
|----------|------------------|----------|
| Why does this exist? | Primary | Brief link |
| System contract / data flow | Primary | Pipeline trace at execution level |
| Trade-offs and ADRs | Primary | Optional short notes in prose |
| Imports and syntax | Mention | Primary |
| Function bodies | Snippets + design notes | Full walkthrough in prose |
| Tests | Which contracts they defend | Command to run only |

---

## Visual standard

Prefer prose first. Add Mermaid flowcharts when they teach execution order. Derive HTML per [`../../AGENTS.md`](../../AGENTS.md).

---

## Example header

```markdown
# Configure LoRA fine-tuning — code walkthrough

**Epic:** Supervised Fine-Tuning and Model Evaluation · **Jira:** VLA-1037 · **Status:** Complete

**Human-readable version (browser):** [`configure-lora-fine-tuning.html`](configure-lora-fine-tuning.html)

**Architecture doc (system design):** [`../architecture/configure-lora-fine-tuning.md`](../architecture/configure-lora-fine-tuning.md)

## Files touched

| File | Role in this task |
|------|-------------------|
| ... | ... |

## Plain-English purpose

...

## Concepts in this task

- ...

## How to run and verify

...
```

---

## Reference exemplar

When unsure about tone and depth, read a completed code doc in the same epic and match this contract. Update the exemplar when these rules change.

Possible exemplars:

- `docs/epics/supervised-fine-tuning-and-model-evaluation/code/prepare-model-training-format.md` (pipeline + file walkthroughs)
- `docs/epics/supervised-fine-tuning-and-model-evaluation/code/configure-lora-fine-tuning.md` (LoRA config + PEFT bridge)
