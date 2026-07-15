#!/usr/bin/env bash
# Capture Pioneer-style 640x480 BGR PNG reference frames for Purshottam's VLA pipeline.
#
# Usage:
#   ./capture_block_reference_images.sh centered
#   ./capture_block_reference_images.sh left
#   ./capture_block_reference_images.sh right
#   ./capture_block_reference_images.sh close
#   ./capture_block_reference_images.sh all
#
# Output (repo root relative — share this folder with Purshottam):
#   data/reference_images/red_cone_centered.png   → MOVE_FORWARD
#   data/reference_images/red_cone_left.png       → TURN_LEFT
#   data/reference_images/red_cone_right.png      → TURN_RIGHT
#   data/reference_images/stop_barrier_close.png  → STOP
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PKG_ROOT="${WS_ROOT}/src/litevla_bridge"
REPO_ROOT="$(cd "${WS_ROOT}/.." && pwd)"
OUT_DIR="${REPO_ROOT}/data/reference_images"
TARGET="${1:-all}"
CAM_W=640
CAM_H=480

# shellcheck source=/dev/null
eval "$("${SCRIPT_DIR}/find_webots.sh" --export)"

mkdir -p "${OUT_DIR}"

write_world() {
  local world_path="$1"
  local cube_x="$2"
  local cube_y="$3"
  local cube_size="${4:-0.2}"
  local half_size
  half_size=$(awk -v s="${cube_size}" 'BEGIN {printf "%.3f", s / 2}')
  cat >"${world_path}" <<EOF
#VRML_SIM R2023b utf8

EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2023b/projects/objects/backgrounds/protos/TexturedBackground.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2023b/projects/objects/backgrounds/protos/TexturedBackgroundLight.proto"
EXTERNPROTO "https://raw.githubusercontent.com/cyberbotics/webots/R2023b/projects/objects/floors/protos/RectangleArena.proto"

WorldInfo {
  basicTimeStep 16
}
Viewpoint {
  orientation 0.35 -0.35 -0.85 1.4
  position 2.8 1.5 2.5
}
TexturedBackground {
}
TexturedBackgroundLight {
}
RectangleArena {
  floorSize 5 5
  wallHeight 0.4
}
Solid {
  translation ${cube_x} ${cube_y} ${half_size}
  children [
    Shape {
      appearance PBRAppearance {
        baseColor 1 0 0
        roughness 0.4
        metalness 0
      }
      geometry Box {
        size ${cube_size} ${cube_size} ${cube_size}
      }
    }
  ]
  name "red_cube"
  boundingObject Box {
    size ${cube_size} ${cube_size} ${cube_size}
  }
}
Robot {
  translation 0 0 0.02
  rotation 0 0 1 0
  children [
    Transform {
      children [
        Shape {
          appearance PBRAppearance {
            baseColor 0.15 0.45 0.75
            roughness 1
            metalness 0
          }
          geometry Box {
            size 0.12 0.08 0.04
          }
        }
      ]
    }
    HingeJoint {
      jointParameters HingeJointParameters {
        axis 0 1 0
        anchor 0 0.03 0
      }
      device [
        RotationalMotor {
          name "left wheel motor"
          maxVelocity 10
        }
      ]
      endPoint Solid {
        translation 0 0.03 0
        rotation 1 0 0 1.5708
        children [
          Shape {
            appearance PBRAppearance {
              baseColor 0.1 0.1 0.1
            }
            geometry Cylinder {
              height 0.02
              radius 0.02
            }
          }
        ]
        name "left wheel"
        boundingObject Cylinder {
          height 0.02
          radius 0.02
        }
        physics Physics {
          density -1
          mass 0.01
        }
      }
    }
    HingeJoint {
      jointParameters HingeJointParameters {
        axis 0 1 0
        anchor 0 -0.03 0
      }
      device [
        RotationalMotor {
          name "right wheel motor"
          maxVelocity 10
        }
      ]
      endPoint Solid {
        translation 0 -0.03 0
        rotation 1 0 0 1.5708
        children [
          Shape {
            appearance PBRAppearance {
              baseColor 0.1 0.1 0.1
            }
            geometry Cylinder {
              height 0.02
              radius 0.02
            }
          }
        ]
        name "right wheel"
        boundingObject Cylinder {
          height 0.02
          radius 0.02
        }
        physics Physics {
          density -1
          mass 0.01
        }
      }
    }
    Camera {
      translation 0.06 0 0.03
      rotation 0 1 0 0
      name "camera"
      width ${CAM_W}
      height ${CAM_H}
      fieldOfView 1.2
    }
  ]
  name "litevla_robot"
  controller "capture_one_frame"
  supervisor FALSE
  boundingObject Box {
    size 0.12 0.08 0.04
  }
  physics Physics {
    density -1
    mass 0.15
  }
}
EOF
}

capture_one() {
  local tag="$1"
  local filename="$2"
  local cube_x="$3"
  local cube_y="$4"
  local cube_size="${5:-0.2}"
  local world_file="${PKG_ROOT}/worlds/.capture_${tag}.wbt"
  local out_png="${OUT_DIR}/${filename}"

  write_world "${world_file}" "${cube_x}" "${cube_y}" "${cube_size}"

  echo "Capturing ${filename} (cube x=${cube_x}, y=${cube_y}, size=${cube_size}) ..."
  export WEBOTS_PROJECT_PATH="${PKG_ROOT}"
  export LITEVLA_CAPTURE_PATH="${out_png}"
  export PYTHONPATH="${WEBOTS_HOME}/lib/controller/python:${PYTHONPATH:-}"

  timeout 90s "${WEBOTS_BIN}" --mode=fast --minimize --batch --stdout "${world_file}" >/dev/null

  if [[ ! -f "${out_png}" ]]; then
    echo "Capture failed: ${out_png}" >&2
    exit 1
  fi

  python3 - <<PY
from pathlib import Path
import struct, zlib

path = Path("${out_png}")
data = path.read_bytes()
if data[:8] != b"\\x89PNG\\r\\n\\x1a\\n":
    raise SystemExit(f"Not a PNG: {path}")
w = struct.unpack(">I", data[16:20])[0]
h = struct.unpack(">I", data[20:24])[0]
print(f"  -> {path} ({w}x{h})")
if (w, h) != (${CAM_W}, ${CAM_H}):
    raise SystemExit(f"Expected ${CAM_W}x${CAM_H}, got {w}x{h}")
PY

  rm -f "${world_file}" "${world_file%.wbt}.wbproj" 2>/dev/null || true
}

echo "Output directory: ${OUT_DIR}"
echo

# Robot faces +X. Positive Y = left side of camera image.
case "${TARGET}" in
  centered)
    capture_one "centered" "red_cone_centered.png" 1.75 0.00 ;;
  left)
    capture_one "left" "red_cone_left.png" 1.55 0.55 ;;
  right)
    capture_one "right" "red_cone_right.png" 1.55 -0.55 ;;
  close)
    capture_one "close" "stop_barrier_close.png" 0.32 0.00 0.22 ;;
  all)
    capture_one "centered" "red_cone_centered.png" 1.75 0.00
    capture_one "left" "red_cone_left.png" 1.55 0.55
    capture_one "right" "red_cone_right.png" 1.55 -0.55
    capture_one "close" "stop_barrier_close.png" 0.32 0.00 0.22
    ;;
  *)
    echo "Unknown target: ${TARGET}" >&2
    echo "Usage: $0 [centered|left|right|close|all]" >&2
    exit 1
    ;;
esac

echo
echo "Done."
