#!/usr/bin/env bash
# Drive litevla_robot in Webots and save four 640x480 BGR PNG reference frames.
#
# Fixed red cube in mvp_arena.wbt (translation 2 0 0.1).
# Robot drives to each viewpoint; camera frames saved for Purshottam.
#
# Usage:
#   ./ros_ws/scripts/capture_reference_frames_by_driving.sh
#
# Output:
#   data/reference_images/red_cone_centered.png   (MOVE_FORWARD)
#   data/reference_images/red_cone_left.png       (TURN_LEFT)
#   data/reference_images/red_cone_right.png      (TURN_RIGHT)
#   data/reference_images/stop_barrier_close.png  (STOP)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
OUT_DIR="${REPO_ROOT}/data/reference_images"
TIMEOUT_SEC=300

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "ROS setup not found: ${ROS_SETUP}" >&2
  exit 1
fi

# shellcheck source=/dev/null
eval "$("${SCRIPT_DIR}/find_webots.sh" --export)"

if [[ ! -f "${WS_ROOT}/install/setup.bash" ]]; then
  echo "Building workspace ..."
  "${WS_ROOT}/scripts/build_ros_ws.sh"
fi

set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
# shellcheck source=/dev/null
source "${WS_ROOT}/install/setup.bash"
set -u

export WEBOTS_HOME
mkdir -p "${OUT_DIR}"

echo "Driving robot in Webots to capture reference frames"
echo "  Output: ${OUT_DIR}"
echo "  (Webots GUI may open briefly; robot will drive automatically)"
echo

timeout "${TIMEOUT_SEC}s" ros2 launch litevla_bridge reference_capture.launch.py \
  output_dir:="${OUT_DIR}"

echo
echo "Captured files:"
ls -1 "${OUT_DIR}"/red_cone_*.png "${OUT_DIR}"/stop_barrier_close.png 2>/dev/null || {
  echo "Capture incomplete — check launch logs above." >&2
  exit 1
}
