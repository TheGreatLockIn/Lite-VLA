# Concept Primers Guidelines (AGENTS.md)

This directory (`docs/mentorship/concepts/`) contains generalized reference documents for programming languages, frameworks, and technologies used in the Lite-VLA project.

---

## 1. Scope and Tone

1. **Generalized Topics:** Keep the explanations general and reusable. A reader should be able to copy these concept primers to another project and use them as a general learning resource.
2. **Pedagogical Clarity:** Start with the simplest terms, avoid nested jargon, and provide clear code examples.
3. **Link Integration:** Pair with human HTML files so they can be hyperlinked from other code walkthrough pages.

---

## 2. Topic Explanation Template

Every concept explained under this folder must follow this structure:

### `### <Topic Name>`
A header defining the concept.

#### Overview
A 2–3 sentence plain English explanation of what this is and what problem it solves.

#### Code Example
A simple, minimal, copy-pasteable Python snippet demonstrating the concept in isolation. Keep it clean and explain what the output is.

#### Use-Case Scenarios
Explain **how** and **where** this topic is applied:
* **General Use-Case:** Where you see this in standard Python/ML projects.
* **Robotics & VLA Use-Case:** How it solves a specific robotic problem (e.g. data capture, model fine-tuning, streaming).

#### When to Use vs. When NOT to Use
A short trade-offs section guiding the developer's architectural logic:
* **Choose this when:** (Conditions under which this pattern/tool is best).
* **Avoid this when:** (Scenarios where another pattern/tool is a better fit).
