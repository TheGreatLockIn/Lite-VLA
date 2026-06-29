# LiteVLA-Edge System Architecture Summary

This document outlines the system architecture, core components, data flow, and implementation goals for the local, on-device Lite-VLA implementation.

**Human-readable version (browser):** [`architecture_summary.html`](architecture_summary.html)

---

## 1. Core System Components

The LiteVLA-Edge system is composed of five primary functional blocks:

### 1.1 Perception & Processing (Front-End)
* **Sensor Ingestion**: Pulls camera streams (RGB frames) from the robot's physical or simulated environment.
* **Visual Encoder**: Processes raw frames into normalized visual tokens using a vision encoder network (SigLIP).
* **Instruction Encoder**: Tokenizes and embeds natural language commands alongside visual tokens.

### 1.2 VLA Model Inference (Core Brain)
* **Backbone Model**: Compact Multimodal Transformer (TBD: SmolVLM-256M or similar small VLM).
* **LoRA Adapter**: Parameter-efficient low-rank adapters ($r=8, \alpha=8$) trained to output robot actions.
* **llama.cpp Engine**: Local execution engine running fully GPU-offloaded 4-bit quantized GGUF weights (`Q4_K_M`) for optimized inference.

### 1.3 Action Parser (Bridge)
* **Token Capture**: Isolates target action tokens from the model's text output stream.
* **Numerical Mapping**: Maps discrete action tokens or structured coordinates to linear ($v$) and angular ($\omega$) velocity values.
* **Format Translation**: Packages values into standard messages for publishing.

### 1.4 Safety Override (Guardrails)
* **Velocity Clamp**: Checks values against physical constraints to prevent unsafe or extreme motor commands.
* **Parsing Fallback**: Automatically overrides unrecognized model outputs, transforming them instantly into a safe `STOP`.
* **Manual Override**: Monitored input triggers that immediately disconnect VLA control in favor of human operator control.

### 1.5 ROS 2 / Simulation Controller (Actuation)
* **ROS 2 Publisher**: Translates actions into standard `geometry_msgs/Twist` messages published on the `/cmd_vel` topic.
* **Decoupled Control Loop**: Runs a low-level heartbeat (100 Hz) to smooth out inputs from the high-level VLA (~6.6 Hz).
* **Simulation Interface**: ROS 2 nodes communicate with Webots/simulation using the `webots_ros2` package to control joint and wheel motors.

---

## 2. System Data Flow

The runtime loop operates as a closed-loop perception-action cycle:

```
Camera RGB Frame + Text Instruction
  │
  ▼
Visual & Text Tokenizer
  │
  ▼
VLA Inference Engine (SmolVLM-256M @ INT4)
  │
  ▼
Action Token Parser / Decoder
  │
  ▼
Safety Gate (Velocity Clamping & Stop Fallback)
  │
  ▼
ROS 2 Publisher (/cmd_vel Twist message)
  │
  ▼
Webots Robot Controller
```

---

## 3. Paper Claims vs. Project Implementation Goals

The project balances replication of the paper's core architecture with practical constraints of a beginner-friendly simulation setup.

| Dimension | Paper Claims & Results | Our Project Implementation Goals | Status |
| :--- | :--- | :--- | :--- |
| **Hardware** | NVIDIA Jetson AGX Orin (64GB) / Orin NX.<br>Runs fully local and offline. | RTX 4080 Laptop GPU (Linux, ROS 2 installed) handles both training, inference, and Webots simulation loop. | **Modified Strategy** |
| **Latency & Hz** | Mean end-to-end latency of **150.5 ms** (~6.64 Hz).<br>Extremely low jitter ($\sigma = 0.13$ ms). | Target closed-loop control in simulation at a stable **6 to 10 Hz** rate. | **Matched Target** |
| **VLM Model** | Distilled SmolVLM-256M backbone.<br>Converted to 4-bit (Q4_K_M) GGUF. | Compact VLM backbone (TBD: SmolVLM-256M or similar). | **Matched Target** |
| **Fine-Tuning** | Supervised image-to-action fine-tuning in FP32 using LoRA ($r=8, \alpha=8$). | Utilize LoRA fine-tuning in FP32. | **Matched Target** |
| **Control Middleware** | Fully integrated ROS 2 middleware publishing Twist velocity vectors. | Fully integrated ROS 2 workspace linking Webots nodes via `webots_ros2`. | **Matched Target** |
| **Action Space** | Continuous control coordinates (linear velocity $v$, angular velocity $\omega$). | Start with a discrete action vocabulary (e.g. `MOVE_FORWARD`, `STOP`) for easy parsing. | **Simplified MVP Path** |
