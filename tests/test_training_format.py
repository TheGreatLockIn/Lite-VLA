"""Tests for Epic 106 Story 1 — supervised fine-tuning format."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from litevla.data.schema import TrainingRecord, write_jsonl
from litevla.prompting import PromptFormatter
from ml.finetune.format_dataset import (
    convert_jsonl_to_sft,
    format_training_record,
    format_training_records,
    write_sft_jsonl,
)
from ml.finetune.prompt_template import (
    ASSISTANT_PREFIX,
    IMAGE_TOKEN,
    TrainingPromptTemplate,
    build_training_prompt,
)


def _record(**overrides: object) -> TrainingRecord:
    base = {
        "id": "t1",
        "image_path": "data/imgs/frame.png",
        "instruction": "Move toward the red cube.",
        "action": "MOVE_FORWARD",
        "timestamp": "2026-06-24T12:00:00+00:00",
        "source": "reference",
        "episode_id": "ep1",
    }
    base.update(overrides)
    return TrainingRecord(**base)  # type: ignore[arg-type]


def test_training_prompt_matches_inference_formatter() -> None:
    instruction = "Move toward the red cube."
    parts = build_training_prompt(instruction, "MOVE_FORWARD", version="v1")
    inference = PromptFormatter(version="v1").format_prompt(instruction)

    assert parts.prompt == inference
    assert parts.prompt.startswith(f"USER: {IMAGE_TOKEN}\n")
    assert parts.prompt.endswith(ASSISTANT_PREFIX)
    assert parts.target == "MOVE_FORWARD"
    assert parts.full_text == f"{parts.prompt} MOVE_FORWARD"
    assert parts.full_text.endswith("MOVE_FORWARD")


def test_training_prompt_rejects_invalid_action() -> None:
    with pytest.raises(ValueError, match="Unknown action"):
        build_training_prompt("go", "JUMP", version="v1")


def test_format_record_puts_action_only_in_target() -> None:
    example = format_training_record(_record(action="TURN_LEFT"), prompt_version="v1")
    assert example.target == "TURN_LEFT"
    assert example.action == "TURN_LEFT"
    assert example.prompt.endswith(ASSISTANT_PREFIX)
    assert f"{ASSISTANT_PREFIX} TURN_LEFT" not in example.prompt
    assert example.full_text.endswith("TURN_LEFT")
    assert IMAGE_TOKEN in example.prompt


def test_format_record_v2_prompt_version() -> None:
    example = format_training_record(_record(), prompt_version="v2")
    assert example.prompt_version == "v2"
    assert "Navigate command:" in example.prompt
    assert example.target == "MOVE_FORWARD"


def test_convert_jsonl_writes_sft_file(tmp_path: Path) -> None:
    image_dir = tmp_path / "data" / "imgs"
    image_dir.mkdir(parents=True)
    from PIL import Image

    Image.new("RGB", (2, 2), color=(10, 20, 30)).save(image_dir / "frame.png")

    input_jsonl = tmp_path / "train.jsonl"
    write_jsonl(
        input_jsonl,
        iter(
            [
                _record(id="a", action="STOP", instruction="Stop when close."),
                _record(id="b", action="SLOW_DOWN", instruction="Approach slowly."),
            ]
        ),
    )
    output_jsonl = tmp_path / "sft.jsonl"
    examples = convert_jsonl_to_sft(
        input_jsonl,
        output_jsonl,
        prompt_version="v1",
        repo_root=tmp_path,
        check_image=True,
    )

    assert len(examples) == 2
    assert output_jsonl.is_file()
    lines = [json.loads(line) for line in output_jsonl.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["id"] == "a"
    assert lines[0]["target"] == "STOP"
    assert lines[0]["prompt"].endswith(ASSISTANT_PREFIX)
    assert lines[0]["full_text"].endswith("STOP")
    assert lines[0]["image_exists"] is True
    assert lines[1]["target"] == "SLOW_DOWN"


def test_labels_visible_in_target_tokens_for_all_actions() -> None:
    actions = ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "STOP", "SLOW_DOWN")
    records = [_record(id=f"r{i}", action=action) for i, action in enumerate(actions)]
    examples = format_training_records(records, prompt_version="v1")
    assert len(examples) == 5
    for example, action in zip(examples, actions, strict=True):
        assert example.target == action
        assert example.full_text.endswith(action)
        # Target is the only content after ASSISTANT:
        after = example.full_text.split(ASSISTANT_PREFIX, maxsplit=1)[1].strip()
        assert after == action


def test_write_sft_jsonl_omits_none_fields(tmp_path: Path) -> None:
    example = format_training_record(
        TrainingRecord(
            image_path="data/x.png",
            instruction="go",
            action="STOP",
            timestamp="2026-06-24T12:00:00+00:00",
            source="synthetic",
        )
    )
    path = tmp_path / "out.jsonl"
    assert write_sft_jsonl(path, [example]) == 1
    raw = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "id" not in raw
    assert "episode_id" not in raw
    assert raw["target"] == "STOP"


def test_template_reuses_shared_formatter_instance() -> None:
    template = TrainingPromptTemplate(version="v1")
    a = template.build("a", "STOP")
    b = template.build("b", "TURN_RIGHT")
    assert a.prompt_version == b.prompt_version == "v1"
    assert a.target == "STOP"
    assert b.target == "TURN_RIGHT"
