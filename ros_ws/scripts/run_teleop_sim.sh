#!/usr/bin/env bash
# Launch Webots + keyboard teleop. Must run in an interactive terminal (not Cursor task output).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/sim_common.sh"

if [[ ! -t 0 ]]; then
  echo "ERROR: stdin is not a TTY — keyboard teleop will not work here." >&2
  echo >&2
  echo "Open GNOME Terminal / Konsole and run:" >&2
  echo "  cd \"${REPO_ROOT}\"" >&2
  echo "  ./ros_ws/scripts/run_teleop_sim.sh" >&2
  echo >&2
  echo "To stop a previous session:" >&2
  echo "  ./ros_ws/scripts/stop_teleop_sim.sh" >&2
  exit 1
fi

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "ROS setup not found: ${ROS_SETUP}" >&2
  exit 1
fi

if [[ ! -f "${WS_ROOT}/install/setup.bash" ]]; then
  echo "Workspace not built. Run: ${WS_ROOT}/scripts/build_ros_ws.sh" >&2
  exit 1
fi

# shellcheck source=/dev/null
eval "$("${SCRIPT_DIR}/find_webots.sh" --export)" || true

set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
# shellcheck source=/dev/null
source "${WS_ROOT}/install/setup.bash"
set -u

export WEBOTS_HOME="${WEBOTS_HOME:-}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

PIDS=()

cleanup() {
  local pid
  for pid in "${PIDS[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cleanup_stale_sim_processes

echo "Starting Webots (interactive GUI)..."
echo "  stop: ./ros_ws/scripts/stop_teleop_sim.sh"
echo "  w/↑ forward  s/↓ backward  a/← left  d/→ right  x brake  q quit"
echo

ros2 launch litevla_bridge webots_sim.launch.py interactive:=true "$@" &
PIDS+=("$!")

wait_for_sim_clock 90 || {
  echo "Aborting — simulation did not publish /clock." >&2
  exit 1
}

wait_for_diffdrive_stack 120 || {
  echo "Aborting — controllers failed to activate." >&2
  echo "Try: ./ros_ws/scripts/stop_teleop_sim.sh && sleep 3 && ./ros_ws/scripts/run_teleop_sim.sh" >&2
  exit 1
}

wait_for_camera_topic 30 || true

ros2 run litevla_bridge heartbeat_controller --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop \
  -p require_frame:=false \
  -p heartbeat_hz:=25.0 \
  -p action_timeout_sec:=0.2 \
  -p teleop_startup_grace_sec:=20.0 &
PIDS+=("$!")

ros2 run litevla_bridge command_recorder --ros-args \
  -p use_sim_time:=true \
  -p enabled:=true \
  -p source:=teleop &
PIDS+=("$!")

echo
echo "Ready — hold w/s to drive, a/d to turn. Release keys to stop."
echo "Onboard camera: ros2 run rqt_image_view rqt_image_view /image_raw"
echo

ros2 run litevla_bridge teleop_keyboard --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop \
  -p poll_hz:=50.0 \
  -p hold_sec:=0.12
