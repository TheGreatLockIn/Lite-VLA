#!/usr/bin/env bash
# Resolve Webots binary and WEBOTS_HOME for Lite-VLA scripts.
# Source this file or call: eval "$(./find_webots.sh --export)"

set -euo pipefail

_export=0
if [[ "${1:-}" == "--export" ]]; then
  _export=1
fi

WEBOTS_BIN=""
WEBOTS_HOME_RESOLVED=""

_candidates() {
  if command -v webots >/dev/null 2>&1; then
    command -v webots
  fi
  printf '%s\n' \
    "/usr/local/webots/webots/bin/webots" \
    "/snap/bin/webots" \
    "${HOME}/.local/bin/webots" \
    "${WEBOTS_HOME:-}/webots/bin/webots" \
    "${WEBOTS_HOME:-}/bin/webots"
}

for candidate in $(_candidates); do
  if [[ -n "${candidate}" && -x "${candidate}" ]]; then
    WEBOTS_BIN="$(readlink -f "${candidate}")"
    break
  fi
done

if [[ -z "${WEBOTS_BIN}" ]]; then
  if [[ "${_export}" -eq 1 ]]; then
    echo "echo 'Webots binary not found. Run: ./ros_ws/scripts/install_webots.sh' >&2; return 1 2>/dev/null || exit 1" 
  else
    echo "Webots binary not found." >&2
    echo "ROS bridge (ros-jazzy-webots-ros2) is separate from the Webots app." >&2
    echo "Install the simulator: ./ros_ws/scripts/install_webots.sh" >&2
    exit 1
  fi
  exit 1
fi

# Resolve WEBOTS_HOME from canonical binary path (deb: .../webots/webots → .../webots).
WEBOTS_HOME_RESOLVED="$(cd "$(dirname "${WEBOTS_BIN}")" && pwd)"
if [[ "$(basename "${WEBOTS_HOME_RESOLVED}")" == "bin" ]]; then
  WEBOTS_HOME_RESOLVED="$(cd "${WEBOTS_HOME_RESOLVED}/.." && pwd)"
fi
if [[ "$(basename "${WEBOTS_HOME_RESOLVED}")" != "webots" ]]; then
  for guess in "/usr/local/webots" "${HOME}/.local/webots"; do
    if [[ -x "${guess}/webots" ]]; then
      WEBOTS_HOME_RESOLVED="${guess}"
      WEBOTS_BIN="$(readlink -f "${guess}/webots")"
      break
    fi
  done
fi

if [[ "${_export}" -eq 1 ]]; then
  printf 'export WEBOTS_BIN=%q\n' "${WEBOTS_BIN}"
  printf 'export WEBOTS_HOME=%q\n' "${WEBOTS_HOME_RESOLVED}"
  printf 'export PATH=%q:${PATH}\n' "$(dirname "${WEBOTS_BIN}")"
else
  echo "WEBOTS_BIN=${WEBOTS_BIN}"
  echo "WEBOTS_HOME=${WEBOTS_HOME_RESOLVED}"
fi
