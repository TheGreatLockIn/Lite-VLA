# Label review checklist (VLA-44 / 10098)

Use before merging a review CSV into training JSONL.

## Row completeness

- [ ] Every row has a unique `id` matching the exported JSONL
- [ ] `review_status` is set (`approved`, `corrected`, or `rejected`) — not left as `pending`
- [ ] `corrected` rows include a valid `action_reviewed` token
- [ ] `reviewer` and `reviewed_at` filled for approved/corrected rows

## Action quality

- [ ] Action is one of: `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `SLOW_DOWN`, `STOP`
- [ ] Action matches what a careful human would do **next** given the image + instruction
- [ ] No teleop-only labels (`MOVE_BACKWARD`, compound `A+B` strings) in training actions
- [ ] `STOP` used when the goal is reached or continuing would overshoot
- [ ] `SLOW_DOWN` used when approaching a target, not for generic caution

## Image and instruction

- [ ] `image_path` is repo-relative and the PNG exists locally (VLA-45 will automate)
- [ ] Instruction is imperative, present tense, and matches the capture scenario
- [ ] Instruction does not contradict the visible scene (wrong color, missing object)

## Traceability

- [ ] Rejected rows have a short `review_notes` reason (blur, wrong scene, duplicate)
- [ ] Import output path is versioned (e.g. `train_reviewed.jsonl`) — do not overwrite blindly
- [ ] Spot-check 5–10 random rows after import with `pytest tests/test_label_review.py`
