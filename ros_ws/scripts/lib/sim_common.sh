# Shared helpers for Lite-VLA Webots simulation scripts.
# Source from run_teleop_sim.sh / stop_teleop_sim.sh — do not execute directly.

cleanup_stale_sim_processes() {
  echo "Ensuring no stale Lite-VLA sim processes are running..."
  pkill -f "ros2 launch litevla_bridge webots_sim.launch.py" 2>/dev/null || true
  pkill -f "ros2 launch litevla_bridge teleop_sim.launch.py" 2>/dev/null || true
  pkill -f "litevla_bridge/heartbeat_controller" 2>/dev/null || true
  pkill -f "litevla_bridge/teleop_keyboard" 2>/dev/null || true
  pkill -f "litevla_bridge/command_recorder" 2>/dev/null || true
  pkill -f "litevla_bridge/cmd_vel_tester" 2>/dev/null || true
  pkill -f webots-bin 2>/dev/null || true
  sleep 2
}

wait_for_sim_clock() {
  local timeout_sec="${1:-90}"
  echo "Waiting for simulation /clock (up to ${timeout_sec}s)..."
  for _ in $(seq 1 "${timeout_sec}"); do
    if timeout 2 ros2 topic echo /clock --once >/dev/null 2>&1; then
      echo "Simulation clock ready."
      return 0
    fi
    sleep 1
  done
  echo "ERROR: /clock not published — Webots or Ros2Supervisor may have failed." >&2
  return 1
}

wait_for_controller_active() {
  local controller_name="$1"
  local timeout_sec="${2:-120}"
  for _ in $(seq 1 "${timeout_sec}"); do
    if ros2 service call /controller_manager/list_controllers controller_manager_msgs/srv/ListControllers "{}" 2>/dev/null \
      | grep -q "name='${controller_name}', state='active'"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_diffdrive_stack() {
  local timeout_sec="${1:-120}"
  echo "Waiting for ros2_control stack (joint_state + diffdrive)..."
  if ! wait_for_controller_active "joint_state_broadcaster" "${timeout_sec}"; then
    echo "ERROR: joint_state_broadcaster did not become active." >&2
    return 1
  fi
  if ! wait_for_controller_active "diffdrive_controller" "${timeout_sec}"; then
    echo "ERROR: diffdrive_controller did not become active." >&2
    return 1
  fi
  echo "Controllers active — robot can move."
  return 0
}

wait_for_camera_topic() {
  local timeout_sec="${1:-30}"
  echo "Waiting for /image_raw (up to ${timeout_sec}s)..."
  for _ in $(seq 1 "${timeout_sec}"); do
    if timeout 2 ros2 topic echo /image_raw --once >/dev/null 2>&1; then
      echo "Camera topic ready."
      return 0
    fi
    sleep 1
  done
  echo "WARNING: /image_raw not seen yet; teleop can still drive the robot." >&2
  return 1
}
