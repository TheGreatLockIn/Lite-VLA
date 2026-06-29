#!/usr/bin/env bash
# Launch Webots + keyboard teleop with synchronized frame + command capture (VLA-42).
# Must run in an interactive terminal (not Cursor task output).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/sim_common.sh"

INSTRUCTION="${LITEVLA_CAPTURE_INSTRUCTION:-Move toward the red cube.}"
WORLD="${LITEVLA_CAPTURE_WORLD:-mvp_arena.wbt}"
RECORD_FRAMES_HZ="${LITEVLA_CAPTURE_FPS:-5.0}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--instruction TEXT] [--fps HZ] [--world NAME]

Environment overrides:
  LITEVLA_CAPTURE_INSTRUCTION   Goal text stored in episode.json
  LITEVLA_CAPTURE_FPS           Frame save rate (default: 5.0)
  LITEVLA_CAPTURE_WORLD         Webots world file name (default: mvp_arena.wbt)

Output:
  data/raw/episodes/<episode_id>/
    episode.json
    commands.jsonl
    frames/*.png

Stop with: ./ros_ws/scripts/stop_teleop_sim.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instruction)
      INSTRUCTION="${2:?missing value for --instruction}"
      shift 2
      ;;
    --fps)
      RECORD_FRAMES_HZ="${2:?missing value for --fps}"
      shift 2
      ;;
    --world)
      WORLD="${2:?missing value for --world}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -t 0 ]]; then
  echo "ERROR: stdin is not a TTY — keyboard teleop will not work here." >&2
  echo "Open a terminal and run: cd \"${REPO_ROOT}\" && ./ros_ws/scripts/run_episode_capture.sh" >&2
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

RECORD_INTERVAL_SEC="$(python3 -c "print(1.0 / float('${RECORD_FRAMES_HZ}'))")"

export LITEVLA_CAPTURE_INSTRUCTION="${INSTRUCTION}"
export LITEVLA_CAPTURE_WORLD="${WORLD}"
export LITEVLA_CAPTURE_FPS="${RECORD_FRAMES_HZ}"

EPISODE_DIR="$(python3 -c "
import os
from litevla.data.episode import init_raw_episode
print(init_raw_episode(
    instruction=os.environ['LITEVLA_CAPTURE_INSTRUCTION'],
    source='teleop',
    world=os.environ['LITEVLA_CAPTURE_WORLD'],
    record_frames_hz=float(os.environ['LITEVLA_CAPTURE_FPS']),
))
")"

echo "Episode directory: ${EPISODE_DIR}"
echo "  instruction: ${INSTRUCTION}"
echo "  frame rate:  ${RECORD_FRAMES_HZ} Hz"
echo

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

ros2 launch litevla_bridge webots_sim.launch.py interactive:=true &
PIDS+=("$!")

wait_for_sim_clock 90 || {
  echo "Aborting — simulation did not publish /clock." >&2
  exit 1
}

wait_for_diffdrive_stack 120 || {
  echo "Aborting — controllers failed to activate." >&2
  exit 1
}

wait_for_camera_topic 30 || {
  echo "WARNING: /image_raw not ready; frames may not save until camera publishes." >&2
}

ros2 run litevla_bridge heartbeat_controller --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop \
  -p require_frame:=false \
  -p heartbeat_hz:=25.0 \
  -p action_timeout_sec:=0.2 \
  -p teleop_startup_grace_sec:=20.0 &
PIDS+=("$!")

ros2 run litevla_bridge camera_subscriber --ros-args \
  -p use_sim_time:=true \
  -p record_frames:=true \
  -p frame_save_dir:="${EPISODE_DIR}/frames" \
  -p record_interval_sec:="${RECORD_INTERVAL_SEC}" &
PIDS+=("$!")

ros2 run litevla_bridge command_recorder --ros-args \
  -p use_sim_time:=true \
  -p enabled:=true \
  -p source:=teleop \
  -p episode_dir:="${EPISODE_DIR}" &
PIDS+=("$!")

echo
echo "Capturing to ${EPISODE_DIR}"
echo "Hold w/s to drive, a/d to turn. Press q in teleop to quit."
echo

ros2 run litevla_bridge teleop_keyboard --ros-args \
  -p use_sim_time:=true \
  -p control_mode:=teleop \
  -p poll_hz:=50.0 \
  -p hold_sec:=0.12

echo
echo "Episode saved:"
echo "  ${EPISODE_DIR}"
