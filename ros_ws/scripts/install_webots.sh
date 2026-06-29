#!/usr/bin/env bash
# Install Cyberbotics Webots (simulator app) for Lite-VLA VLA-23.
# Note: ros-jazzy-webots-ros2 is only the ROS bridge — Webots itself is separate.
set -euo pipefail

WEBOTS_VERSION="${WEBOTS_VERSION:-R2025a}"
# Release tag R2025a -> deb name webots_2025a_amd64.deb
DEB_TAG="${WEBOTS_VERSION#R}"
DEB_NAME="webots_${DEB_TAG,,}_amd64.deb"
DOWNLOAD_URL="https://github.com/cyberbotics/webots/releases/download/${WEBOTS_VERSION}/${DEB_NAME}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/lite-vla"
DEB_PATH="${CACHE_DIR}/${DEB_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
if "${SCRIPT_DIR}/find_webots.sh" >/dev/null 2>&1; then
  echo "Webots is already installed:"
  "${SCRIPT_DIR}/find_webots.sh"
  exit 0
fi

echo "Webots simulator not found."
echo "ROS package ros-jazzy-webots-ros2 is installed, but the Webots application is not."
echo
echo "Downloading ${DOWNLOAD_URL}"
mkdir -p "${CACHE_DIR}"
if [[ ! -f "${DEB_PATH}" ]]; then
  if command -v wget >/dev/null 2>&1; then
    wget -O "${DEB_PATH}" "${DOWNLOAD_URL}"
  elif command -v curl >/dev/null 2>&1; then
    curl -fL -o "${DEB_PATH}" "${DOWNLOAD_URL}"
  else
    echo "Install wget or curl to download Webots." >&2
    exit 1
  fi
else
  echo "Using cached ${DEB_PATH}"
fi

echo
echo "Installing Webots (requires sudo)..."
sudo apt-get update -qq
sudo apt-get install -y "${DEB_PATH}"

echo
echo "Verifying install..."
"${SCRIPT_DIR}/find_webots.sh"
echo
echo "Done. Launch the MVP with:"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  source ros_ws/install/setup.bash"
echo "  ./ros_ws/scripts/run_webots_mvp.sh"
