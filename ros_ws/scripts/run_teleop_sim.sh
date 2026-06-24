#!/usr/bin/env bash
# Launch Webots + keyboard teleop. Must run in an interactive terminal (not Cursor task output).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

if [[ ! -t 0 ]]; then
  echo "ERROR: stdin is not a TTY — keyboard teleop will not work here." >&2
  echo >&2
  echo "Open GNOME Terminal / Konsole and run:" >&2
  echo "  cd \"${WS_ROOT}/..\"" >&2
  echo "  ./ros_ws/scripts/run_teleop_sim.sh" >&2
  echo >&2
  echo "Or run sim + teleop in two terminals:" >&2
  echo "  ./ros_ws/scripts/run_webots_mvp.sh" >&2
  echo "  ros2 run litevla_bridge heartbeat_controller --ros-args -p use_sim_time:=true -p control_mode:=teleop -p require_frame:=false" >&2
  echo "  ros2 run litevla_bridge teleop_keyboard --ros-args -p use_sim_time:=true -p control_mode:=teleop" >&2
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
  for pid in "${PIDS[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait_for_controllers() {
  echo "Waiting for diffdrive_controller to become active..."
  for _ in $(seq 1 120); do
    if ros2 service call /controller_manager/list_controllers controller_manager_msgs/srv/ListControllers "{}" 2>/dev/null \
      | grep -q "name='diffdrive_controller', state='active'"; then
      echo "Controllers active — robot can move."
      return 0
    fi
    if ros2 service call /controller_manager/list_controllers controller_manager_msgs/srv/ListControllers "{}" 2>/dev/null \
      | grep -q "name='diffdrive_controller', state='inactive'"; then
      echo "diffdrive_controller loaded but not active yet..." >&2
    fi
    sleep 1
  done
  echo "ERROR: diffdrive_controller did not become active." >&2
  echo "Close Webots, wait 5s, and run this script again." >&2
  return 1
}

echo "Starting Webots sim, heartbeat, and recorder in the background."
echo "Watch the Webots window (not just this terminal)."
echo "If the robot looks static, click litevla_robot in the scene tree (left panel)."
echo "Hold w to drive forward — turns (a/d) are subtle from a distance."
echo "Onboard camera (updates live): ros2 run rqt_image_view rqt_image_view /image_raw"
echo "Keep this terminal focused for keyboard teleop."
echo

ros2 launch litevla_bridge webots_sim.launch.py interactive:=true "$@" &
PIDS+=("$!")

ros2 run litevla_bridge heartbeat_controller --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop \
  -p require_frame:=false &
PIDS+=("$!")

ros2 run litevla_bridge command_recorder --ros-args \
  -p use_sim_time:=true \
  -p enabled:=true \
  -p source:=teleop &
PIDS+=("$!")

wait_for_controllers || {
  echo "Aborting teleop — fix controllers first (see errors above)." >&2
  exit 1
}
echo "Hold w for 2-3 seconds to drive toward the red cube."
echo "Press q to quit teleop."
echo

ros2 run litevla_bridge teleop_keyboard --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop
