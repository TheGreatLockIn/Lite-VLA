# Agent Instructions

These instructions apply to all agents working in this repository.

## Documentation Sources

- For project documentation under `docs/`, follow `docs/AGENTS.md`.
- For epic walkthroughs under `presentations/`, follow `presentations/AGENTS.md`.

## Epic Presentation Requirement

Whenever an agent implements, changes, reviews, or explains code tied to a Jira epic/story/task, it must update the matching `presentations/<epic-slug>/index.html` before finishing the turn.

Agents should infer the active epic from the task title, Jira key, branch name, changed paths, CSV parent mapping, and conversation context. Teammates should not need to manually name the epic unless the work is genuinely ambiguous.

Each update should preserve task order and add concise ADRs, C4/Mermaid visuals, data-flow notes, code walkthrough references, and validation evidence for the work performed.
