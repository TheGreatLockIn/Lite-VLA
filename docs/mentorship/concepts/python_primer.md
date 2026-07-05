# Python Concept Primers
**Human-readable version (browser):** [`python_primer.html`](python_primer.html)

---

### Postponed Evaluation of Annotations (`from __future__ import annotations`)

#### Overview
In standard Python, all class and type names must be fully defined before you can use them as type hints. If Class A references Class B, and Class B references Class A, Python throws a `NameError`. Importing `annotations` from `__future__` postpones the evaluation of type hints, storing them as raw strings in memory until training starts. This prevents circular import errors and allows a class to reference itself in its own type hints.

#### Code Example
```python
from __future__ import annotations

class Node:
    # Without the __future__ import, referencing "Node" inside
    # the class definition would crash because Node is not fully built yet.
    def __init__(self, parent: Node | None = None) -> None:
        self.parent = parent
```

#### Use-Case Scenarios
* **General Use-Case:** Used in all modern Python projects employing static type hints (like `mypy`) to make code cleaner and prevent initialization order issues.
* **Robotics & VLA Use-Case:** Crucial when defining linked datasets, tree nodes, or message packets where custom structures contain self-references.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are writing code with type annotations in Python 3.7+ and want to avoid name errors or circular references.
* **Avoid this when:** You are writing legacy scripts in Python 3.6 or older, or when your runtime code relies on immediately inspecting type hints via `typing.get_type_hints()` (though this is rare).

---

### Dataclasses and Fields (`dataclass` and `field`)

#### Overview
Python's `@dataclass` decorator automatically generates common boilerplate code for classes, such as the initializer (`__init__`), object string representations (`__repr__`), and comparison operators (`__eq__`). Setting `frozen=True` makes the class read-only. The `field` utility allows you to configure specific properties for variables, such as initializing mutable defaults (like lists or dicts) safely.

#### Code Example
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class SensorReading:
    sensor_id: str
    value: float
    # We use field(default_factory=dict) because standard Python
    # mutable defaults like `metadata: dict = {}` are shared across all instances
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### Use-Case Scenarios
* **General Use-Case:** Storing clean, structured config data, database rows, or state parameters without writing manual constructors.
* **Robotics & VLA Use-Case:** Representing visual frames, labels, commands, and episodes as read-only packets to guarantee they do not change as they are shared between background threads.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are creating container classes that mainly hold data structures, and you want automatic validation, comparison, and read-only protection.
* **Avoid this when:** You are building complex object-oriented patterns with heavy inheritance, custom setter properties, or dynamic runtime properties.

---

### File Path Resolution (`pathlib.Path`)

#### Overview
Managing file paths as raw strings (e.g. `"data/imgs/a.png"`) causes scripts to crash when moved to different operating systems (Windows uses backslashes `\`, Linux uses forward slashes `/`). Python's `pathlib` module represents paths as clean objects, automatically handling directory mapping, cross-platform slashes, and path existence verification.

#### Code Example
```python
from pathlib import Path

# Find the directory containing the active script, resolve it to an absolute path,
# and navigate up two levels (equivalent to ../..)
repo_root = Path(__file__).resolve().parents[2]
data_dir = repo_root / "data" / "processed" # Enforces correct slashes automatically
```

#### Use-Case Scenarios
* **General Use-Case:** Defining stable file layouts, reading JSON/text files, and navigating parent directories in any script.
* **Robotics & VLA Use-Case:** Loading datasets, visual models, and simulation files robustly, regardless of whether the developer runs the code on a Windows workstation or a Linux robot computer.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are writing, reading, listing, or checking files on disk. Always prefer `pathlib.Path` over the legacy `os.path` strings.
* **Avoid this when:** You are dealing with virtual file systems or streaming remote URI links (like HTTP paths), which require dedicated network clients.

---

### Python Generators and the `yield` Keyword

#### Overview
A generator is a special type of function that returns a lazy-evaluated iterator. Instead of computing a massive list of items in memory and returning them all at once via `return`, a generator uses `yield` to yield one item at a time to the caller and pause. It resumes execution only when the caller asks for the next item.

#### Code Example
```python
from typing import Iterator

def read_numbers(n: int) -> Iterator[int]:
    for i in range(n):
        print(f"Reading index {i}...")
        yield i

# The loop only runs when we request the next item
for number in read_numbers(3):
    print(f"Got {number}")
```

#### Use-Case Scenarios
* **General Use-Case:** Processing massive log files, database rows, or streams of sensor data that are too large to fit in RAM.
* **Robotics & VLA Use-Case:** Reading JSONL dataset files containing thousands of image paths. Using `yield` ensures the computer only holds a single text line in memory at any millisecond.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are reading sequentially from large files, generating infinite data streams, or iterating over collections where memory efficiency is important.
* **Avoid this when:** You need to randomly access items by index (e.g. getting item 500 without reading the first 499), or when you need to write/modify the data collection dynamically.
