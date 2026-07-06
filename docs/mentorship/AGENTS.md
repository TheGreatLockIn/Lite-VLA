# Mentorship and Code Explanation Guidelines (AGENTS.md)

This directory (`docs/mentorship/`) contains living, pedagogy-centric tutorials and concept primers designed to help developers of all Python skill levels master the Lite-VLA codebase.

---

## 1. Directory Structure

Ensure files are organized repo-wise (matching the module layout of the codebase):
```text
docs/mentorship/
├── AGENTS.md                 # This file (guidelines)
├── index.html                # Main entry point directory
├── concepts/
│   ├── AGENTS.md             # Guidelines for concept primers
│   ├── python_primer.md      # Python syntax and features
│   ├── pytorch_primer.md     # PyTorch and deep learning features
│   └── ros2_primer.md        # ROS 2 and concurrency features
└── <module-name>/
    ├── <tutorial-name>.md    # Code walkthrough (source of truth)
    └── <tutorial-name>.html  # Code walkthrough (browser view)
```

---

## 2. The 5-Step Tutorial Template

Every code tutorial under `docs/mentorship/` must follow this exact 5-step structure:

### Step 1: The Goal & Objective
Define in 1–2 plain-English sentences what the target file or module is trying to accomplish.

### Step 2: Why We Need It
Describe the problem context. Explain what breaks down or fails if this code is not implemented.

### Step 3: How to Think About It (AI Developer Thought Process)
Write this section as a **mimicry of the developer's/AI's thought process** when they first designed this code. Explain the sequential logical decisions:
* "First, I thought about X..."
* "Then I realized that Y would fail because of Z, so I decided to use library A..."
* "Next, I chose to construct it as B because..."
Include a brief, focused real-world analogy to establish intuition, but do not let the analogy distract from the code logic.

### Step 4: Imports & Global Constants Explained
Include a table explaining every import and global constant in the file:
* **Import/Constant Statement:** The exact statement or constant declaration.
* **What it is:** A simple description of the library/variable.
* **Why we use/define it here:** Its specific role in this file.
* **Concept Link:** Hyperlink to the relevant section under `docs/mentorship/concepts/`.

### Step 5: Code Walkthrough & Class Data-Flow Diagrams
Provide a complete, top-to-bottom breakdown of **every class, function, and parameter** in the file. Do not skip any line of logic.

#### Class Data-Flow Diagrams (Mermaid)
For every class in the file, include a Mermaid flowchart showing:
1. The internal variables and types of the class.
2. Where functions import/read data from (disk files, variables, JSONL streams).
3. Where they export/write data to.
4. Callers and dependent classes.

#### Code Details
Use this template for each element:
* **Intent:** What is its architectural purpose?
* **Code Snippet:** A focused code block showing the implementation.
* **Data Contract:** 
  * Inputs: Type, units, and representation.
  * Outputs: Type and return payload.
* **Why it's written this way:** Explain Python features, logic path decisions, and safety considerations.
* **System Connections:** How does this connect to other files? What calls it, what does it call, and what files depend on its side-effects?

---

## 3. Hyperlinking and Concepts Primers Integration

To maintain a unified learning mesh:
1. **Hyperlink Rule:** Whenever a concept, keyword, or library mentioned in a tutorial is also explained in `docs/mentorship/concepts/`, you **must** hyperlink that keyword directly to the corresponding section of the concept file (e.g. `[dataclass](../concepts/python_primer.md#dataclasses)`).
2. **Dual-Format Hyperlinks:**
   * In `.md` files, links must point to `.md` files (e.g. `../concepts/python_primer.md`).
   * In `.html` files, links must point to `.html` files (e.g. `../concepts/python_primer.html`).
