# Dummy action generator

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-26 / Story 1014 · **Subtasks:** 10042 (constant forward), 10043 (sequence), 10044 (dummy mode config)

**Human-readable version (browser):** [`dummy-action-generator.html`](dummy-action-generator.html)

Scripted discrete actions (`MOVE_FORWARD`, `TURN_LEFT`, …) fed to the heartbeat controller before the VLA model is connected.

## Intent

Provide a non-ML command source that exercises the robot loop using the same action vocabulary as Epic 103.

## Shared schema (Epic 103 alignment)

| Path | Purpose |
|------|---------|
| `litevla/actions/schema.py` | `DiscreteAction`, `action_to_twist()` |
| `litevla_bridge/action_schema.py` | Monorepo import bridge for ROS nodes |
| `scripts/run_dummy_pipeline.py` | Offline print of the same sequence |

## ROS artifacts

| Path | Purpose |
|------|---------|
| `litevla_bridge/dummy_action_generator.py` | Publishes desired twist + action label (not `/cmd_vel`) |
| `launch/dummy_sim.launch.py` | Webots + heartbeat + dummy generator |
| `test/test_action_mapping.py` | Validates schema import from ROS package |

## Parameters

| Param | Default | Config mirror |
|-------|---------|---------------|
| `runtime_mode` | `dummy` | `runtime.mode` |
| `action_sequence` | forward → forward → left → stop | `runtime.action_sequence` |
| `sequence_step_sec` | `2.0` | `runtime.sequence_step_sec` |
| `desired_twist_topic` | `/litevla/desired_twist` | Consumed by heartbeat (VLA-27) |

Publishes to `/litevla/desired_twist` and `/litevla/current_action`. The **heartbeat controller** publishes `/cmd_vel`.

## Run

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash

# Webots + dummy sequence
ros2 launch litevla_bridge dummy_sim.launch.py

# Dummy node only (sim already running)
ros2 run litevla_bridge dummy_action_generator
```

**Pass:** Logs show action transitions; robot runs forward → turn → stop in Webots.

## Offline validation

```bash
pytest tests/test_action_schema.py -q
python scripts/run_dummy_pipeline.py
colcon test --packages-select litevla_bridge
```

## Related

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (Epic 103)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
- [velocity-command-publisher.md](velocity-command-publisher.md) (VLA-25)
