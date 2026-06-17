# MVP Demo Task & Non-Goals Definition

This document defines the minimum viable product (MVP) scope, explicit non-goals, acceptance criteria, and the first simulated task for the Lite-VLA project.

**Human-readable version (browser):** [`mvp_definition.html`](mvp_definition.html)

---

## 1. Selected Simulated Task: Navigate to Target Object

For our initial demonstration, the robot will perform a single, narrow task in simulation to prove the end-to-end learning and control pipeline.

### 1.1 Scenario Description
* **Environment**: A flat, bounded arena in Webots containing a single wheeled mobile robot (e.g., Pioneer 3-DX or E-puck) and a high-contrast target object (a Red Cube).
* **Objective**: The robot must search for, navigate toward, and stop directly in front of the red cube.
* **Instruction Input**: Natural language commands instructing the robot on its goal, such as:
  * `"Move toward the red cube."`
  * `"Turn left until you see the red cube."`
  * `"Stop when close to the red cube."`

### 1.2 Control Execution Flow
1. The robot starts at a random orientation/position where the red cube may or may not be in its immediate field of view.
2. The camera publishes RGB frames.
3. The VLA model processes the frame and the goal instruction, predicting a discrete action (e.g., `TURN_LEFT` to search, or `MOVE_FORWARD` to approach).
4. The robot executes the command via ROS 2 `/cmd_vel` publishing, moving closer.
5. Once the red cube is directly in front of the robot at close range, the VLA model predicts `STOP` and the robot halts.

---

## 2. Explicit Non-Goals (Out of Scope)

To prevent scope creep and keep this project achievable for a beginner team, the following items are explicitly **deferred** or **declared out of scope**:

* **Real Robot Deployment**: We will not deploy on a physical robot (e.g., TurtleBot, manipulator arm) or configure embedded hardware (NVIDIA Jetson AGX Orin). All evaluation happens in Webots.
* **Exact Latency Replication**: We will not enforce the paper's exact 150.5 ms / 6.6 Hz latency target on day one. Standard Python runtime latency is acceptable for the simulation baseline.
* **Continuous Action Space**: We will not output continuous linear/angular velocities directly from the VLM. The VLM will output discrete action tokens, which our parser will map to velocities.
* **Multi-Object Relationships & Manipulation**: We will not test complex task instructions (e.g., "pick up the blue cup and place it next to the red box"). Manipulation is completely out of scope.
* **Large-scale Robustness Benchmarks**: We will not run massive, multi-scenario evaluation suites. Success is measured on a single navigation task across 10–20 test runs.

---

## 3. MVP Acceptance Criteria

The project is considered complete and working when it meets the following criteria across our selected simulated task:

### 3.1 VLA Model Output
* The fine-tuned model accepts a camera frame and text instruction and outputs a valid discrete action token (`MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `SLOW_DOWN`) with $\ge 90\%$ format accuracy on held-out test images.

### 3.2 ROS 2 Control Loop
* The ROS 2 workspace compiles cleanly using `colcon build`.
* A bridge node successfully translates the simulator's camera sensor into `/image_raw` ROS topics.
* The model inference node subscribes to `/image_raw` and publishes velocity commands on `/cmd_vel` at a stable rate ($\ge 5$ Hz).

### 3.3 Safety Gate
* **Velocity Clamping**: Linear velocity is strictly clamped to a maximum of $0.2\text{ m/s}$ and angular velocity to $0.6\text{ rad/s}$.
* **Parsing Fallback**: Any malformed or unrecognized text output from the VLA model is caught by the parser and immediately publishes a `Twist` command with all zeros (`STOP`).
* **Emergency Stop**: Pressing a designated keyboard key instantly overrides the VLA publisher and halts the robot.

### 3.4 Ingestion & Logging
* The system logs the following parameters for every control step:
  * Camera frame timestamp.
  * Natural language instruction.
  * Model raw text output.
  * Parsed velocity command.
  * End-to-end inference latency (ms).

---

## 4. Project Risk Register

To ensure project stability, the team will track and mitigate the following technical and project risks.

| Risk ID | Category | Description | Severity | Mitigation Strategy | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | Machine Learning | **Dataset Quality & Label Noise**: Inconsistent manual action labels during data collection cause model confusion. | **High** | Write scripted rule-based heuristics to generate optimal actions for the baseline dataset to ensure 100% label consistency. | ML Lead |
| **RSK-02** | Machine Learning | **VLA Malformed Outputs**: Model outputs open-ended conversational text instead of strict action tokens. | **High** | Implement a deterministic regex parser inside the Action Parser node that maps any invalid output to a safe `STOP` command. | ML Lead |
| **RSK-03** | Machine Learning | **Overfitting to Arena**: Robot learns to navigate only with specific lighting or starting positions. | **Medium** | Randomize starting orientation, cube placement, and arena colors during dataset collection. | QA Lead |
| **RSK-04** | Robotics & Control | **Unsafe Control Commands**: Model outputs extreme velocities causing the robot to flip or crash. | **High** | Apply a strict velocity clamp ($v \le 0.2\text{ m/s}$, $\omega \le 0.6\text{ rad/s}$) at the Safety Gate node. | ROS Lead |
| **RSK-05** | Robotics & Control | **Control Jitter & Lag**: Disconnected control frequencies between VLA inference and Webots lead to jerky movements. | **Medium** | Decouple the loop. Run a low-level smoothing controller at 100 Hz that interpolates VLA commands received at ~5 Hz. | ROS Lead |
| **RSK-06** | Deployment | **GGUF/llama.cpp Compatibility**: Selected VLM architecture fails to convert to GGUF format. | **High** | Validate GGUF export and running via `llama.cpp` using the base un-tuned model in Week 1 before starting fine-tuning. | Deployment Lead |
| **RSK-07** | Deployment | **VRAM Allocation Failures**: Running Webots and model inference on the same GPU leads to memory crashes. | **Medium** | Quantize to 4-bit (`Q4_K_M`) to reduce VLA memory footprint to <1.5GB, and monitor VRAM allocation limits. | Deployment Lead |

### 4.1 Review Cadence
Risks will be evaluated **weekly** during Friday retrospective sessions. Updates to risk status, severity, or ownership will be recorded in the weekly learning logs (e.g., [logs/week_1.md](logs/week_1.md)).

