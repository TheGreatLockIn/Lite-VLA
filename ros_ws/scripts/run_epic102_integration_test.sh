#!/usr/bin/env bash
# End-to-end integration test for Epic 102 work (VLA-19 through VLA-25).
# Requires: ROS Jazzy, built ros_ws, Webots app installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
SIM_STARTUP_SEC="${SIM_STARTUP_SEC:-150}"
LOG_DIR="${REPO_ROOT}/outputs/integration-test-$(date +%Y%m%d-%H%M%S)"
SIM_PID=""

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }

cleanup() {
  if [[ -n "${SIM_PID}" ]] && kill -0 "${SIM_PID}" 2>/dev/null; then
    info "Stopping Webots launch (pid ${SIM_PID})"
    kill "${SIM_PID}" 2>/dev/null || true
    wait "${SIM_PID}" 2>/dev/null || true
  fi
  pkill -f "webots.*mvp_arena" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "${LOG_DIR}"
info "Logs → ${LOG_DIR}"

if [[ ! -f "${ROS_SETUP}" ]]; then
  fail "ROS setup not found: ${ROS_SETUP}"
fi

if ! "${SCRIPT_DIR}/find_webots.sh" >/dev/null 2>&1; then
  fail "Webots not installed. Run: ./ros_ws/scripts/install_webots.sh"
fi

# shellcheck source=/dev/null
eval "$("${SCRIPT_DIR}/find_webots.sh" --export)"
set +u
# shellcheck source=/dev/null
source "${ROS_SETUP}"
# shellcheck source=/dev/null
source "${WS_ROOT}/install/setup.bash"
set -u
export WEBOTS_HOME

info "=== 1/6 Build + colcon test ==="
"${SCRIPT_DIR}/build_ros_ws.sh" >"${LOG_DIR}/build.log" 2>&1
set +u
# shellcheck source=/dev/null
source "${WS_ROOT}/install/setup.bash"
set -u
colcon test --packages-select litevla_bridge >"${LOG_DIR}/colcon-test.log" 2>&1
if ! colcon test-result --verbose >"${LOG_DIR}/colcon-test-result.log" 2>&1; then
  cat "${LOG_DIR}/colcon-test-result.log" >&2
  fail "colcon test failed"
fi
pass "colcon test (9 unit tests)"

info "=== 2/6 workspace_ping smoke ==="
timeout 10 ros2 run litevla_bridge workspace_ping >"${LOG_DIR}/workspace_ping.log" 2>&1
pass "workspace_ping"

info "=== 3/6 Start Webots sim (background, up to ${SIM_STARTUP_SEC}s) ==="
ros2 launch litevla_bridge webots_sim.launch.py >"${LOG_DIR}/webots_sim.log" 2>&1 &
SIM_PID=$!

deadline=$((SECONDS + SIM_STARTUP_SEC))
image_ready=0
while (( SECONDS < deadline )); do
  if ros2 topic list 2>/dev/null | grep -q '^/image_raw$'; then
    if timeout 15 ros2 topic echo /image_raw --once >"${LOG_DIR}/image_once.log" 2>&1; then
      image_ready=1
      break
    fi
  fi
  sleep 2
done

if [[ "${image_ready}" -ne 1 ]]; then
  tail -40 "${LOG_DIR}/webots_sim.log" >&2 || true
  fail "/image_raw not available within ${SIM_STARTUP_SEC}s"
fi
pass "Webots sim + /image_raw publishing"

info "=== 4/6 spawn_verifier (VLA-117) ==="
if ros2 run litevla_bridge spawn_verifier >"${LOG_DIR}/spawn_verifier.log" 2>&1; then
  pass "spawn_verifier"
else
  cat "${LOG_DIR}/spawn_verifier.log" >&2
  fail "spawn_verifier exited non-zero"
fi

info "=== 5/6 camera_subscriber (VLA-24) ==="
timeout 15 ros2 run litevla_bridge camera_subscriber --ros-args \
  -p record_frames:=false >"${LOG_DIR}/camera_subscriber.log" 2>&1 &
CAM_PID=$!
sleep 8
kill "${CAM_PID}" 2>/dev/null || true
wait "${CAM_PID}" 2>/dev/null || true
if grep -q "First frame:" "${LOG_DIR}/camera_subscriber.log"; then
  pass "camera_subscriber received frames"
else
  cat "${LOG_DIR}/camera_subscriber.log" >&2
  fail "camera_subscriber did not log first frame"
fi

info "=== 6/6 cmd_vel_tester (VLA-25) ==="
timeout 12 ros2 run litevla_bridge cmd_vel_tester >"${LOG_DIR}/cmd_vel_tester.log" 2>&1 &
VEL_PID=$!
sleep 3
if timeout 5 ros2 topic echo /cmd_vel --once >"${LOG_DIR}/cmd_vel_echo.log" 2>&1; then
  pass "/cmd_vel topic active during tester"
else
  cat "${LOG_DIR}/cmd_vel_echo.log" >&2
  fail "/cmd_vel not publishing during tester"
fi
wait "${VEL_PID}" 2>/dev/null || true
if grep -q "forward" "${LOG_DIR}/cmd_vel_tester.log" && \
   grep -q "linear.x=" "${LOG_DIR}/cmd_vel_tester.log"; then
  pass "cmd_vel_tester published movement steps"
else
  cat "${LOG_DIR}/cmd_vel_tester.log" >&2
  fail "cmd_vel_tester did not cycle commands"
fi

echo
echo "=========================================="
echo "All integration checks passed."
echo "Logs: ${LOG_DIR}"
echo "=========================================="
