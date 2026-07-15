#!/usr/bin/env bash
# Stop Lite-VLA Webots teleop stack (Webots + ROS nodes).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/sim_common.sh"

cleanup_stale_sim_processes
echo "Lite-VLA teleop sim stopped."
