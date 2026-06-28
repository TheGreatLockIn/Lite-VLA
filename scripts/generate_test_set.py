"""Generate a baseline evaluation dataset of 20 augmented simulation frames."""

from __future__ import annotations

import json
import os
from pathlib import Path
import cv2
import numpy as np

# Source images and their associated ground truth actions
SOURCE_IMAGES = {
    "red_cone_centered.png": "MOVE_FORWARD",
    "red_cone_left.png": "TURN_LEFT",
    "red_cone_right.png": "TURN_RIGHT",
    "stop_barrier_close.png": "STOP",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "data" / "examples"
EVAL_DIR = REPO_ROOT / "data" / "evaluation"


def add_gaussian_noise(image: np.ndarray, mean: float = 0, sigma: float = 15) -> np.ndarray:
    """Add Gaussian noise to simulate sensor noise in Webots camera feeds."""
    h, w, c = image.shape
    noise = np.random.normal(mean, sigma, (h, w, c))
    noisy = image.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def generate_variations(img: np.ndarray) -> list[tuple[np.ndarray, str]]:
    """Generate 5 distinct variations of an image using OpenCV augmentations."""
    variations = []

    # 1. Original (as is)
    variations.append((img.copy(), "original"))

    # 2. Brightness Jitter (Simulating brighter arena lights)
    brighter = cv2.convertScaleAbs(img, alpha=1.0, beta=45)
    variations.append((brighter, "brightness_high"))

    # 3. Low Contrast (Simulating dusty or foggy conditions)
    darker = cv2.convertScaleAbs(img, alpha=0.7, beta=-20)
    variations.append((darker, "contrast_low"))

    # 4. Motion / Gaussian Blur (Simulating camera vibrations)
    blurred = cv2.GaussianBlur(img, (9, 9), 0)
    variations.append((blurred, "gaussian_blur"))

    # 5. Sensor Noise (Simulating low-light compression noise)
    noisy = add_gaussian_noise(img, sigma=18)
    variations.append((noisy, "sensor_noise"))

    return variations


def main() -> None:
    print("Generating baseline evaluation dataset...")
    
    # Ensure directories exist
    os.makedirs(EVAL_DIR, exist_ok=True)

    metadata = []
    index = 1

    for filename, action in SOURCE_IMAGES.items():
        src_path = EXAMPLES_DIR / filename
        if not src_path.is_file():
            print(f"Error: Source image not found at {src_path}")
            return

        # Load raw BGR image
        img = cv2.imread(str(src_path))
        if img is None:
            print(f"Error: Failed to load image at {src_path}")
            return

        # Generate 5 variations
        variations = generate_variations(img)
        
        for var_img, var_type in variations:
            out_filename = f"eval_{index:02d}.png"
            dest_path = EVAL_DIR / out_filename
            
            # Save the image
            cv2.imwrite(str(dest_path), var_img)
            
            # Append metadata entry
            metadata.append({
                "image_id": f"eval_{index:02d}",
                "image_path": f"data/evaluation/{out_filename}",
                "instruction": "go to the red block",
                "expected_action": action,
                "source_image": filename,
                "variation_type": var_type,
            })
            
            print(f"  Saved: data/evaluation/{out_filename} (Source: {filename}, Var: {var_type})")
            index += 1

    # Save metadata JSON file
    meta_path = EVAL_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    print()
    print(f"Successfully generated {index - 1} test images and saved metadata to {meta_path}")


if __name__ == "__main__":
    main()
