# image-preprocessing-pipeline
**Jira Key:** [VLA-36](https://yashrajmote2001.atlassian.net/browse/VLA-36)
**Epic:** Baseline Vision-Language Inference Prototype (VLA-5)
**Human-readable version (browser):** [`image-preprocessing-pipeline.html`](image-preprocessing-pipeline.html)

---

## 1. Intent & Context
To prepare raw simulation camera frames (typically high-resolution BGR images from Webots or ROS `/image_raw`) for the `SmolVLM-256M-Instruct` vision model. The preprocessor standardizes visual inputs by performing:
- BGR to RGB color-space conversion.
- Resizing to specified target dimensions.
- Optional color depth/grayscale reduction.
- In-memory JPEG/PNG compression to match the format expected by the `llama-cpp-python` / `clip.cpp` visual handler.

---

## 2. Configuration Settings
The preprocessing behavior is validated against the schema and loaded via `configs/default.example.yaml`:

```yaml
preprocessing:
  resize_width: 512
  resize_height: 512
  color_format: rgb
  encoding: jpeg
```

---

## 3. Core Interface & Implementation
The core logic resides in `litevla/preprocessing.py`.

### ImagePreprocessor Class
- **`__init__(self, config: dict)`**: Sets parameters and validates dimensions, color formats, and encoding options.
  - *Validation Logic:* Ensures `resize_width` and `resize_height` are positive integers (minimum `16`). It verifies that `color_format` is one of `rgb`, `bgr`, or `gray`, and that `encoding` is one of `jpeg`, `png`, or `none`. Invalid values raise a `PreprocessingError` immediately during node startup.
- **`preprocess(self, image: np.ndarray) -> bytes | np.ndarray`**: Processes the BGR image numpy array. Returns standard file bytes (JPEG/PNG) or a raw preprocessed numpy array.
  - *Validation:* Checks that the input image is a 3-channel (`H`, `W`, `3`) NumPy array.
  - *Color Space Handling:* Converts colors using OpenCV (`cv2.cvtColor`). Swapping channels from BGR to RGB is essential because the pre-trained vision encoder (SigLIP) was trained on RGB images. If skipped, colors like Red and Blue are inverted, causing model control errors. Grayscale reduces the array to a single intensity channel.
  - *Resizing:* Scales the image using bilinear interpolation to the target shape (e.g. `512x512` or `224x224`).
  - *In-Memory Compression:* Compresses the processed array into a byte stream based on the `encoding` format:
    - **`jpeg`:** Lossy compression. Produces a very small byte footprint in RAM, maximizing transfer speed to the model engine. This is the default.
    - **`png`:** Lossless compression. Retains absolute pixel quality at the cost of a larger memory footprint.
    - **`none`:** Bypasses compression and returns the raw processed NumPy array (useful for offline testing or native PyTorch pipelines).

---

## 4. Technical Decisions & ADR Notes

### ADR: In-Memory Compression
* **Status:** Accepted
* **Context:** The `llama-cpp-python` LLaVA handler requires image files or raw file bytes (JPEG/PNG) to feed into the underlying C++ vision projector (`clip.cpp`). It cannot directly ingest raw NumPy arrays.
* **Decision:** The preprocessor compresses NumPy arrays into `.jpg`/`.png` buffers using `cv2.imencode` in RAM, avoiding SSD write wear and reducing latency.
* **Consequences:** Returns a `bytes` object representing the raw data of a JPEG/PNG file. This stream can be loaded directly by `llama-cpp-python` in RAM, enabling ultra-fast real-time control (5-10 Hz) with zero disk I/O.

---

## 5. Validation & Unit Tests
Tests are located in `tests/test_preprocessing.py`:
- **`test_preprocessor_init_with_defaults`**: Confirms fallback parameters are applied when configuration section is empty or missing.
- **`test_preprocessor_init_invalid_configs`**: Ensures that invalid sizes (e.g. negative) or unsupported formats throw clean exceptions during instantiation.
- **`test_preprocessing_resize_and_color_rgb`**: Verifies that a `640x480` BGR image is resized to `224x224` and that color channels are swapped correctly. It asserts color coordinates to ensure top/bottom half colors are swapped to RGB format.
- **`test_preprocessing_gray`**: Confirms color reduction to grayscale outputs a 2D array.
- **`test_preprocessing_encoding_jpeg`**: Validates the in-memory compression logic. It passes the image through the preprocessor with `encoding: "jpeg"`, asserts that a `bytes` object is returned, and attempts to decode it using `cv2.imdecode` to verify the resulting bytes form a valid, uncorrupted JPEG image.
- **`test_preprocessing_input_validation`**: Asserts that incorrect input types or shapes are caught and raise a `PreprocessingError`.
