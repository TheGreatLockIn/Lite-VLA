#!/usr/bin/env bash
# Launch Lite-VLA MVP in Webots (VLA-23). GPU-friendly vs Isaac Sim.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "ROS setup not found: ${ROS_SETUP}" >&2
  exit 1
fi

if ! "${SCRIPT_DIR}/find_webots.sh" >/dev/null 2>&1; then
  echo "Webots simulator application not found." >&2
  echo >&2
  echo "You have the ROS bridge if you ran:" >&2
  echo "  sudo apt install ros-${ROS_DISTRO}-webots-ros2" >&2
  echo "That alone is not enough — you also need the Webots app." >&2
  echo >&2
  echo "Install Webots:" >&2
  echo "  ./ros_ws/scripts/install_webots.sh" >&2
  echo >&2
  echo "Or manual .deb: https://github.com/cyberbotics/webots/releases/tag/R2025a" >&2
  exit 1
fi

# shellcheck source=/dev/null
eval "$("${SCRIPT_DIR}/find_webots.sh" --export)"

set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
set -u

if [[ -f "${WS_ROOT}/install/setup.bash" ]]; then
  set +u
  # shellcheck source=/dev/null
  source "${WS_ROOT}/install/setup.bash"
  set -u
else
  echo "Workspace not built. Run: ${WS_ROOT}/scripts/build_ros_ws.sh" >&2
  exit 1
fi

export WEBOTS_HOME

echo "Launching Webots MVP (Lite-VLA VLA-23)"
echo "  WEBOTS_BIN=${WEBOTS_BIN}"
echo "  WEBOTS_HOME=${WEBOTS_HOME}"
echo "  ROS_DISTRO=${ROS_DISTRO}"
echo

exec ros2 launch litevla_bridge webots_sim.launch.py "$@"
