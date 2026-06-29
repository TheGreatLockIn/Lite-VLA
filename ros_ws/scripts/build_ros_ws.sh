#!/usr/bin/env bash
# Build the Lite-VLA ROS 2 workspace (VLA-19).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "ROS setup file not found: ${ROS_SETUP}" >&2
  echo "Install ROS 2 ${ROS_DISTRO} or set ROS_DISTRO to your installed distribution." >&2
  exit 1
fi

set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
set -u

cd "${WS_ROOT}"
colcon build --symlink-install "$@"

echo
echo "Build complete. Source the workspace overlay:"
echo "  source ${WS_ROOT}/install/setup.bash"
