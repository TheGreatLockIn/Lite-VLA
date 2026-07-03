# prepare-model-training-format
**Jira Key:** [VLA-1036](https://yashrajmote2001.atlassian.net/browse/VLA-1036)
**Epic:** Supervised Fine-Tuning and Model Evaluation (VLA-7)
**Human-readable version (browser):** [`prepare-model-training-format.html`](prepare-model-training-format.html)

---

## 1. Executive Summary
The model training format module converts raw VLA demonstration records (consisting of camera frames, instruction prompts, and target movement commands) into tokenized inputs and targets formatted specifically for the vision-language model (`SmolVLM-256M-Instruct`). It enforces standard conversational structuring, standardizes multiple camera image formats (OpenCV BGR matrices, RGB matrices, PIL images), and applies prompt label masking using a parallel target tensor where prompt tokens are replaced by `-100` to prevent gradient updates on the instruction text.

---

## 2. Mental Model, Backstory, Prerequisites, and Vocabulary

### Mental Model
Think of this module as a **grading scorecard mask** or **scorecard compiler**. 

It exists because we want the VLM model to learn to predict the robot action, but ignore the instruction prompt itself during gradient descent. The key engineering tension is prompt-vs-response token length alignment. Because visual tokens expand dynamically depending on image dimensions and layout parameters, simple text-only token offset checks trigger index misalignment. 

A beginner mistake is tokenizing the prompt text without the image to determine the label offset. A senior engineer watches for identical visual placeholder counts across both the prompt and full target tokenizations.

### Backstory: why this exists
Before this module existed, training a visual-language model on flat sequences would calculate loss on both the prompt instruction (input) and the action word (output).

The naive solution would be to evaluate cross-entropy loss on every single generated token. However, this breaks down because the model wastes its capacity predicting the prompt itself (which is already given by the user). It causes the VLM to overfit to instruction prefixes, degrade output precision, and generate noisy textual descriptions instead of deterministic steering signals.

So this design chooses **label masking**, replacing all prompt tokens in the training labels tensor with the ignore-index constant `-100`. This pattern appears in real systems as instruction-masking or SFT prefix-masking in large language model fine-tuning.

### Vocabulary
| Term | Meaning in this project |
|------|-------------------------|
| `input_ids` | PyTorch integer tensor representing tokenized conversation inputs. |
| `labels` | Parallel PyTorch target integer tensor containing action labels masked with `-100`. |
| `-100` | The standard ignore-index constant used by PyTorch `CrossEntropyLoss` to bypass gradient updates. |
| Chat Template | Jinja/Python text templates mapping roles (`user`, `assistant`) to special wrapper tags. |
| `SFTDataFormatter` | Class that converts visual states and commands into SFT target tensors. |
| Conversational Dict | A standard Python dictionary structured with `role` and `content` keys to represent chat turns. |
| VLM Processor | A unified utility class combining a text tokenizer and an image preprocessor to construct model inputs. |

---

## 3. Under the Hood: Step-by-Step Token Masking

In Supervised Fine-Tuning (SFT), we pass the entire combined prompt and response text to the model. We want the model to learn to predict the action token, but ignore the user's instructions. We achieve this by tokenizing the prompt prefix and the full sequence, then masking the prompt prefix tokens in our labels tensor.

### The Role of Conversational Dict Formatting
SmolVLM was pre-trained using very specific chat syntax tags (e.g. `<|im_start|>user\n`, `<|im_start|>assistant\n`). To format our data correctly, we represent our training records as **Conversational Dicts**. By passing these dicts to the processor's chat template compiler (`processor.apply_chat_template`), the processor automatically injects these model-specific separators. This guarantees that our training data matches the exact formatting syntax the model was built on, preventing attention-mask issues.

### The Role of the VLM Processor
Unlike text-only language models that use tokenizers, or vision-only models that use image processors, a VLM uses a unified **multimodal Processor**. It tokenizes the compiled chat template text, standardizes the pixel values of the camera image, and returns a single dictionary containing `input_ids` and `pixel_values` ready for PyTorch.

---

### Deep Dive: How Prompt Masking Works in Memory

Let's look at a concrete sequence trace for a single training record:
* **Instruction:** `"Go left."`
* **Target Action:** `"TURN_LEFT"`

#### 1. Tokenizing the Prompt Prefix
First, we format and tokenize the prompt prefix: `"USER: <image> Go left. ASSISTANT:"`.
The tokenizer converts this to **5 tokens** ($N = 5$):
`[1002, 3811, 492, 18, 93]`

#### 2. Tokenizing the Full Sequence
Next, we format and tokenize the full conversation: `"USER: <image> Go left. ASSISTANT: TURN_LEFT </s>"`.
The tokenizer converts this to **7 tokens** ($M = 7$):
`[1002, 3811, 492, 18, 93, 14325, 2]`
*(where `14325` represents the action token "TURN_LEFT", and `2` represents the End-of-Sequence token `</s>`)*

#### 3. Creating the Labels Mask
We clone the full sequence token IDs for our target labels, and replace the first $N$ ($5$) tokens with `-100`:
`[-100, -100, -100, -100, -100, 14325, 2]`

During backpropagation, PyTorch scans through the tensors token-by-token:

| Index | Token Text | Input ID (`input_ids`) | Target ID in `labels` | Does PyTorch calculate loss? | Why? |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **0** | `USER:` | `1002` | `-100` | **No** | Prompt token; ignored by PyTorch |
| **1** | `<image>` | `3811` | `-100` | **No** | Prompt token; ignored by PyTorch |
| **2** | `Go` | `492` | `-100` | **No** | Prompt token; ignored by PyTorch |
| **3** | `left.` | `18` | `-100` | **No** | Prompt token; ignored by PyTorch |
| **4** | `ASSISTANT:` | `93` | `-100` | **No** | Prompt token; ignored by PyTorch |
| **5** | `TURN_LEFT` | `14325` | `14325` | **Yes!** | Model is graded on predicting the correct action |
| **6** | `</s>` | `2` | `2` | **Yes!** | Model is graded on generating the end tag |

---

## 4. Guided Code Reading and File Index

### Guided Code Reading
Read these in order:
1. [`litevla/training/formatter.py`](file:///C:/Projects/Lite-VLA/litevla/training/formatter.py)
   - First inspect the `format_conversation` method to see how system prompts and user inputs are nested.
   - Look at the `__call__` operator to see how images are standardized and token lengths are computed.
2. [`tests/test_training_formatter.py`](file:///C:/Projects/Lite-VLA/tests/test_training_formatter.py)
   - Inspect `test_formatter_label_masking` to see how the `-100` mask is verified at the token-offset level.

### File Index
| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/training/formatter.py` | Data formatting class | Prepares PyTorch inputs and labels for training | The alignment between prompt token length and masking offset |
| `tests/test_training_formatter.py` | Executable unit tests | Defends the formatting and masking contract | Mock setup for the Hugging Face processor |

---

## 5. API Contract and Data Flow

The formatter maps inputs through conversation templates and processor tokenizers to yield training tensors.

```text
Camera Frame (PIL/Numpy) ──┐
Goal Instruction ──────────┼──> [SFTDataFormatter] ──> input_ids (Tokens sequence)
Ground-Truth Action ───────┘                          labels (Prompt masked sequence)
                                                      pixel_values (Normalized image)
```

### Data Contract
- **Input:**
  - `image` (`PIL.Image.Image` or `numpy.ndarray`): Input visual frame.
  - `instruction` (`str`): Goal command text.
  - `action` (`str`): The correct navigation action (e.g. `"MOVE_FORWARD"`).
- **Output:** A dictionary containing:
  - `input_ids` (`torch.Tensor`): 1D integer tensor representing the tokenized conversation tokens.
  - `labels` (`torch.Tensor`): 1D target integer tensor matching `input_ids`, where prompt tokens are set to `-100` and the action tokens are kept intact.
  - `pixel_values` (`torch.Tensor`): Vision features extracted by the VLM processor.

### Naive Approach vs Chosen Approach
| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Tokenize prompt without image to find offset | Faster execution, fewer inputs passed during the offset check | **Rejected.** Mismatches offsets due to dynamic visual placeholder expansion in Hugging Face multimodal templates. |
| Tokenize prompt and full text using the same image | Guarantees exact token alignment | **Chosen.** Expanded visual placeholders occupy identical token lengths in both passes, making offset calculations robust. |

---

## 6. Implementation Breakdown

### Conversational Structuring
The `SFTDataFormatter` class formats inputs into standard Hugging Face messages:
```python
# litevla/training/formatter.py
def format_conversation(self, instruction: str, action: str) -> list[dict[str, Any]]:
    user_text = self.user_template.format(instruction=instruction)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": f"{self.system_instruction}\n\n{user_text}"},
            ],
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": action},
            ],
        },
    ]
    return messages
```
**What to notice:** The formatting groups system instructions and user templates into the user's turn, while the target action word belongs strictly to the assistant's turn.

### Prompt Masking Implementation
To calculate prompt lengths accurately across visual tokens, the formatter runs the processor twice, passing the same image to both:
```python
# litevla/training/formatter.py
prompt_encoding = self.processor(text=prompt_text, images=image, return_tensors="pt")
full_encoding = self.processor(text=full_text, images=image, return_tensors="pt")

prompt_len = prompt_encoding["input_ids"].shape[1]
full_len = full_encoding["input_ids"].shape[1]

# Squeeze batch dimension and clone for labels
input_ids = full_encoding["input_ids"].squeeze(0)
labels = input_ids.clone()
# Mask prompt prefix with -100
labels[:prompt_len] = -100
```
**What to notice:** Image matrices are converted from OpenCV BGR to PIL RGB format before they are tokenized, ensuring compatibility with Hugging Face's image preprocessing expectations.

---

## 7. Engineering Decisions

### ADR: Unified Multimodal Token Length Alignment
- **Status:** Accepted
- **Context:** To construct the labels mask, we need the exact token offset where the prompt ends and the assistant's action starts. Visual placeholder tokens are expanded dynamically by the processor based on the model's visual projection layout. Tokenizing the prompt without the image causes mismatching offsets.
- **Decision:** Pass the same image matrix to both the prompt prefix tokenization and the full conversation tokenization passes.
- **Consequences:** The expanded vision tokens map to identical offsets in both passes, making sequence length subtraction perfectly deterministic and safe.

---

## 8. Verification Patterns and Debugging

### Executable Unit Tests
Unit tests in [`tests/test_training_formatter.py`](file:///C:/Projects/Lite-VLA/tests/test_training_formatter.py) cover:
- **Initialization validation:** Formatter checks config prompt version validity.
- **Conversational dict generation:** Verifies correct system prompt injection and roles layout.
- **Image standardization:** Confirms that PIL, BGR matrices (OpenCV), and RGB matrices are mapped safely.
- **Prompt masking accuracy:** Validates that the first $N$ tokens in `labels` are exactly `-100` and target tokens are preserved.

Run tests:
```bash
.venv\Scripts\pytest tests/test_training_formatter.py -v
```

### Failure Modes and Debugging Path
| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Formatter crashes with `TypeError` | Raw image is not a PIL Image or numpy array | Check input type in log metrics | Ensure image inputs go through OpenCV/PIL loading before passing to formatter |
| Formatter offsets mismatch | Different images or `None` passed to the prompt tokenizer | Verify token shape outputs for both encodings | Pass the identical image reference to both `prompt_encoding` and `full_encoding` |

---

## 9. Engineering Principle and Active Learning

### Engineering Principle Taught by this Task
This task teaches the **"prefix-masking"** pattern. When training autoregressive language or visual models on instruction datasets, we must configure target masks to ignore the prompt tokens. Calculating loss on prompt prefixes causes model degradation because it shifts training updates away from generating outputs toward memorizing user queries.

### Active Learning Checks
1. Why does PyTorch use `-100` as the default ignore index in its loss function?
2. What happens if we do not mask the prompt tokens during training?
3. How does the processor handle image inputs when they are passed as numpy BGR matrices vs. PIL images?
4. How would you adjust `SFTDataFormatter` if the visual model starts using multi-image input sequences?
