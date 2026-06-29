# Dummy action generator

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-26 / 1014 · **Subtasks:** 10042 (forward), 10043 (sequence), 10044 (dummy mode config)

**Human-readable version (browser):** [`dummy-action-generator.html`](dummy-action-generator.html)

## Executive summary

`dummy_action_generator` is the **pre-ML command source** for Epic 102: it steps through a configurable list of Epic 103 discrete actions, maps each to nominal velocities via `action_to_twist()`, and publishes desired twists for the heartbeat—not `/cmd_vel` directly. This proves the full perception–action loop before Epic 104/108 connect a VLA model.

## API contract and data flow

```text
action_sequence (config / param)
    ──> dummy_action_generator (timer per step)
    ──> action_to_twist(DiscreteAction)
    ──> /litevla/desired_twist + /litevla/current_action
    ──> heartbeat_controller
    ──> /cmd_vel
```

| Parameter | Default | Config mirror |
|-----------|---------|---------------|
| `runtime_mode` | `dummy` | `runtime.mode` — node idles otherwise |
| `action_sequence` | forward → forward → left → stop | `runtime.action_sequence` |
| `sequence_step_sec` | `2.0` | `runtime.sequence_step_sec` |
| `desired_twist_topic` | `/litevla/desired_twist` | Consumed by VLA-27 |

**Invariant:** Action names are uppercase Epic 103 tokens only (`MOVE_FORWARD`, `TURN_LEFT`, …).

## Implementation breakdown

### Shared schema bridge

| Path | Role |
|------|------|
| `litevla/actions/schema.py` | Canonical `DiscreteAction`, `action_to_twist()` |
| `litevla_bridge/action_schema.py` | ROS package import shim |
| `scripts/run_dummy_pipeline.py` | Offline print of the same sequence (no ROS) |

Single vocabulary for dummy ROS, offline scripts, future parser (Epic 103), and dataset labels (Epic 105).

### ROS node (`dummy_action_generator.py`)

- Publishes twist + string action label each step.
- Respects `control_mode` / `runtime_mode` gates so teleop can take over without duplicate publishers.

## Engineering decisions

**ADR: Publish desired twist, not cmd_vel**

- **Status:** Accepted (VLA-27)
- **Context:** Action sources update slowly; diff-drive expects steady commands.
- **Decision:** Dummy publishes `/litevla/desired_twist`; heartbeat owns `/cmd_vel`.
- **Consequences:** All future sources (teleop, model) follow the same pattern.

## Verification patterns

```bash
pytest tests/test_action_schema.py -q
python scripts/run_dummy_pipeline.py
colcon test --packages-select litevla_bridge
ros2 launch litevla_bridge dummy_sim.launch.py
```

## Related

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (VLA-29)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
