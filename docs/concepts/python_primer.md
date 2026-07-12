# Python Concept Primers
**Human-readable version (browser):** [`python_primer.html`](python_primer.html)

---

## Navigation
* [Postponed Annotations](#postponed-annotations)
* [JSON Serialization](#json-serialization)
* [Dataclasses and Fields](#dataclasses-and-fields)
* [Pathlib File Resolution](#pathlib-file-resolution)
* [Typing and Type Checking](#typing-and-type-checking)
* [JSON Schema Validation](#json-schema-validation)
* [Custom Exceptions](#custom-exceptions)
* [Hashing with Hashlib](#hashing-with-hashlib)
* [Deterministic Randomness](#deterministic-randomness)
* [Sorting and Lambdas](#sorting-and-lambdas)
* [Regular Expressions](#regular-expressions)
* [Generators and Yield](#generators-and-yield)

---

### Postponed Annotations

#### Overview
In standard Python, all class and type names must be fully defined before they can be referenced as type hints. If Class A references Class B, and Class B references Class A, Python throws a `NameError`. Importing `annotations` from `__future__` postpones the evaluation of type hints, storing them as raw strings in memory until training starts. This prevents circular import errors and allows a class to reference itself in its own type hints.

#### Code Example
```python
from __future__ import annotations

class Node:
    def __init__(self, parent: Node | None = None) -> None:
        self.parent = parent
```

#### Use-Case Scenarios
* **General Use-Case:** Used in all modern Python projects employing static type hints (like `mypy`) to make code cleaner and prevent initialization order issues.
* **Robotics & VLA Use-Case:** Crucial when defining linked datasets, tree nodes, or message packets where custom structures contain self-references.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are writing code with type annotations in Python 3.7+ and want to avoid name errors or circular references.
* **Avoid this when:** You are writing legacy scripts in Python 3.6 or older.

---

### JSON Serialization

#### Overview
JSON (JavaScript Object Notation) is a standard text format for sharing structured data. Python's `json` module provides:
* `json.loads(string)`: Parse a raw string into a Python dict/list.
* `json.dumps(obj)`: Convert a Python dict/list into a clean string.
* `json.load(file)`: Read JSON directly from an open file.
* `json.dump(obj, file)`: Write JSON directly into an open file.

#### Code Example
```python
import json

raw_text = '{"name": "robot", "speed": 1.5}'
# Parse text to dict
data = json.loads(raw_text)
print(data["name"]) # Output: robot

# Serialize dict back to string
clean_string = json.dumps(data)
```

#### Use-Case Scenarios
* **General Use-Case:** Saving program configurations, reading web API data, and exporting debug states to disk.
* **Robotics & VLA Use-Case:** Reading JSONL metadata rows line-by-line during dataset ingestion, and saving camera/action alignment logs to disk.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need a human-readable, cross-language format to save metadata.
* **Avoid this when:** You are storing raw binary data (like images or high-dimensional weight arrays), which should be saved in formats like PNG or NumPy `.npy`/`.pt` instead.

---

### Dataclasses and Fields

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
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### Use-Case Scenarios
* **General Use-Case:** Storing clean, structured config data, database rows, or state parameters without writing manual constructors.
* **Robotics & VLA Use-Case:** Representing visual frames, labels, commands, and episodes as read-only packets to guarantee they do not change as they are shared between background threads.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are creating container classes that mainly hold data structures, and you want automatic validation, comparison, and read-only protection.
* **Avoid this when:** You are building complex object-oriented patterns with heavy inheritance, custom setter properties, or dynamic runtime properties.

---

### Pathlib File Resolution

#### Overview
Managing file paths as raw strings (e.g. `"data/imgs/a.png"`) causes scripts to crash when moved to different operating systems (Windows uses backslashes `\`, Linux uses forward slashes `/`). Python's `pathlib` module represents paths as clean objects, automatically handling directory mapping, cross-platform slashes, and path existence verification.
* `resolve()`: Expands relative paths (like `.`) to full absolute paths.
* `parents[i]`: Navigates up directories (0 is the parent folder, 1 is parent's parent, etc.).
* `/` operator: Joins folders together regardless of OS slash rules.
* `is_file()`: Checks if the path points to an existing file.

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

### Typing and Type Checking

#### Overview
Python is dynamically typed (variables can hold any data type at runtime). Static type checking (using `typing` module classes like `Any`, `Iterator`, `Sequence`, `Callable`) allows tools like `mypy` to verify your code before running it.
* `Any`: Allows any type (disables typing checks for that variable).
* `Iterator[T]`: Represents a generator stream yielding items of type `T`.
* `Sequence[T]`: Represents a read-only list/tuple of items of type `T`.
* `Callable[[A, B], R]`: Represents a function that receives inputs of type `A` and `B` and returns type `R`.

#### Code Example
```python
from typing import Callable, Sequence

def process_numbers(numbers: Sequence[int], transform: Callable[[int], int]) -> list[int]:
    return [transform(x) for x in numbers]
```

#### Use-Case Scenarios
* **General Use-Case:** Writing large-scale codebases where clear function inputs and outputs prevent bugs.
* **Robotics & VLA Use-Case:** Specifying model input shapes, image transformation functions, and action parser parameters so developers know exactly what variables must be passed.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are developing libraries or collaborating with other developers.
* **Avoid this when:** Writing quick, throw-away scripts where runtime validation and development speed are the only priorities.

---

### JSON Schema Validation

#### Overview
JSON Schema is an open standard to describe and validate JSON data structures. Python's `jsonschema` library allows you to define a schema dictionary (containing required keys and expected types) and check raw files or inputs against it.
* `jsonschema.validate(instance, schema)`: Verifies that the dictionary matches the schema structure.
* `Draft202012Validator`: The official validator class for the modern Draft 2020-12 schema specification.

#### Code Example
```python
import jsonschema
from jsonschema import Draft202012Validator

schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "val": {"type": "number"}
    },
    "required": ["id", "val"]
}

# Verifies that raw matches the schema or throws jsonschema.ValidationError
jsonschema.validate({"id": "read1", "val": 42}, schema)
```

#### Use-Case Scenarios
* **General Use-Case:** Checking API request payloads, validating configuration files, and parsing database schemas.
* **Robotics & VLA Use-Case:** Auditing raw simulation capture logs to guarantee that no keys are missing before compile time.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are loading raw, external files (like JSON or JSONL data records) into your application and need to guarantee structural correctness.
* **Avoid this when:** Checking standard Python internal objects, which should be validated using type checking or direct assertion blocks instead.

---

### Custom Exceptions

#### Overview
In Python, you can define your own error classes by inheriting from standard built-in exceptions like `Exception` or `ValueError`. Creating custom exceptions helps you distinguish between system failures (like network losses) and domain-specific validation errors (like invalid robotic commands).

#### Code Example
```python
class ActionParseError(ValueError):
    """Raised when a steering command cannot be mapped to a robot action."""
    pass

def parse_command(cmd: str) -> str:
    if cmd not in ["MOVE", "STOP"]:
        raise ActionParseError(f"Unknown command: {cmd}")
    return cmd
```

#### Use-Case Scenarios
* **General Use-Case:** Building libraries where users need to catch specific business-logic failures cleanly.
* **Robotics & VLA Use-Case:** Catching schema mismatch issues or parsing problems specifically, allowing the validation script to continue scanning other rows and summary logs instead of crashing immediately.

#### When to Use vs. When NOT to Use
* **Choose this when:** You want callers of your function to catch and handle your specific error scenario while letting other errors bubble up.
* **Avoid this when:** A standard built-in exception (like `FileNotFoundError` or `KeyError`) already describes the error scenario perfectly.

---

### Hashing with Hashlib

#### Overview
A cryptographic hash function converts arbitrary data inputs into a fixed-length string of characters (a hash digest). Python's `hashlib` provides hash algorithms like SHA-256. Cryptographic hashes are one-way (you cannot reconstruct the input from the hash value) and deterministic (the same input always produces the exact same hash).
* `hexdigest()`: Returns the hash value as a clean string of hexadecimal digits.

#### Code Example
```python
import hashlib

data = "robot_episode_12".encode("utf-8")
# Compute SHA-256 hash
sha = hashlib.sha256(data)
print("Hash String:", sha.hexdigest())
```

#### Use-Case Scenarios
* **General Use-Case:** Verifying file integrity (checking if download was corrupted), storing passwords safely, or generating unique signatures.
* **Robotics & VLA Use-Case:** Generating unique, reproducible IDs for visual frames or seeding random generators deterministically based on image properties.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need to check if data has changed, generate a unique ID based on file content, or seed random generators repeatably.
* **Avoid this when:** You need to encrypt data that must be decrypted later (use symmetric encryption libraries instead).

---

### Deterministic Randomness

#### Overview
Computers generate pseudo-random numbers by applying algorithms to a starting seed number. If you use the global `random` module, other libraries (like NumPy or PyTorch) might alter the random state, changing your random sequence. Python's `random.Random(seed)` creates a isolated, local random generator instance. By using a fixed seed, you guarantee that the sequence of random numbers is identical on every machine.
* `shuffle(list)`: Shuffles a list in place.
* `uniform(a, b)`: Returns a random floating-point number between `a` and `b`.
* `random()`: Returns a random float between `0.0` and `1.0`.

#### Code Example
```python
import random

# Setting a fixed seed ensures the output is always [3, 1, 2]
rng = random.Random(42)
items = [1, 2, 3]
rng.shuffle(items)
print("Shuffled:", items)
```

#### Use-Case Scenarios
* **General Use-Case:** Writing tests for randomized logic, generating game levels, or dividing dataset splits consistently.
* **Robotics & VLA Use-Case:** Generating training/validation dataset splits and applying data augmentations (like blurs or contrast changes) identically across multiple train runs.

#### When to Use vs. When NOT to Use
* **Choose this when:** You want random variability but require the results to be 100% reproducible for debugging.
* **Avoid this when:** You need cryptographically secure randomness (like password keys), which requires the `secrets` module instead.

---

### Sorting and Lambdas

#### Overview
Python's built-in `sorted(iterable, key=...)` function returns a new sorted list from the items in any iterable. The `key` parameter accepts a function that extracts a comparison key from each element. Python's `lambda` keyword allows you to write quick, one-line functions on the fly without using `def`.

#### Code Example
```python
# A list of dictionaries representing robot coordinates
coords = [{"x": 3, "y": 1}, {"x": 1, "y": 5}, {"x": 2, "y": 2}]

# Sort by the "x" key value using a lambda function
sorted_coords = sorted(coords, key=lambda item: item["x"])
print("Sorted by X:", sorted_coords)
```

#### Use-Case Scenarios
* **General Use-Case:** Ordering database results, sorting file paths alphabetically, or ranking scores.
* **Robotics & VLA Use-Case:** Ordering camera frames by their numerical timestamps (e.g. `0_000000.png`, `1_000000.png`) to ensure episodes are parsed in chronological order.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need to order elements based on custom attributes or dictionary keys.
* **Avoid this when:** You have high-performance, multi-dimensional array operations (use NumPy's `np.sort` or PyTorch's `torch.sort` which run much faster).

---

### Regular Expressions

#### Overview
Regular Expressions (regex) are strings of characters that define search patterns. Python's `re` module allows you to find, validate, and extract sub-strings from text.
* `re.compile(pattern)`: Compiles a search pattern string into a reusable regex object.
* `re.match(pattern, text)`: Checks if the text matches the pattern from the start.
* Parentheses `( )` in a regex define a capture group, allowing you to extract specific parts of the matching text.

#### Code Example
```python
import re

# Match frame filename format: <seconds>_<nanoseconds>.png
pattern = re.compile(r"(\d+)_(\d+)\.png")
match = pattern.match("12_340000000.png")

if match:
    sec = int(match.group(1)) # Extracts 12
    nanosec = int(match.group(2)) # Extracts 340000000
```

#### Use-Case Scenarios
* **General Use-Case:** Validating email addresses, parsing logs, and scraping specific patterns from raw text.
* **Robotics & VLA Use-Case:** Extracting simulation time counters from file paths when compiling raw simulator logs into training records.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need to extract structured variables from semi-structured strings (like file names or timestamps).
* **Avoid this when:** You are parsing standard structured data formats like JSON or XML, which have dedicated, safer parsers.

---

### Generators and Yield

#### Overview
A generator is a special type of function that returns a lazy-evaluated iterator. Instead of computing a massive list of items in memory and returning them all at once via `return`, a generator uses `yield` to yield one item at a time to the caller and pause. It resumes execution only when the caller asks for the next item.

#### Code Example
```python
from typing import Iterator

def read_numbers(n: int) -> Iterator[int]:
    for i in range(n):
        yield i

# The loop only runs when we request the next item
for number in read_numbers(3):
    print(number)
```

#### Use-Case Scenarios
* **General Use-Case:** Processing massive log files, database rows, or streams of sensor data that are too large to fit in RAM.
* **Robotics & VLA Use-Case:** Reading JSONL dataset files containing thousands of image paths. Using `yield` ensures the computer only holds a single text line in memory at any millisecond.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are reading sequentially from large files, generating infinite data streams, or iterating over collections where memory efficiency is important.
* **Avoid this when:** You need to randomly access items by index, or when you need to write/modify the data collection dynamically.

---

### CSV Parsing

#### Overview
CSV (Comma-Separated Values) is a plain-text format for tabular data. Python's built-in `csv` module provides:
* `csv.DictReader(file)`: Reads CSV rows into Python dictionaries using the header row for keys.
* `csv.DictWriter(file, fieldnames)`: Writes dictionaries to CSV rows using standard header column names.

#### Code Example
```python
import csv
from pathlib import Path

# Writing to a CSV file
fields = ["id", "action"]
with open("actions.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerow({"id": "a1", "action": "STOP"})

# Reading from a CSV file
with open("actions.csv", "r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["id"], row["action"]) # Output: a1 STOP
```

#### Use-Case Scenarios
* **General Use-Case:** Importing and exporting spreadsheet data between databases and programs.
* **Robotics & VLA Use-Case:** Creating review sheets so developers can audit machine labels in Excel.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need to export structured logs or metadata for humans to inspect in tabular sheets.
* **Avoid this when:** Storing highly nested tree structures or model weights (use JSON or HDF5/PyTorch formats instead).

---

### Collections and Counters

#### Overview
Python's `collections` module provides specialized container datatypes. One of the most useful is `Counter`, which counts occurrences of hashable items in a list or sequence automatically.
* `Counter(list)`: Computes counts of all unique items.
* `most_common(n)`: Returns the top `n` most frequent items.

#### Code Example
```python
from collections import Counter

actions = ["STOP", "MOVE", "STOP", "STOP", "TURN"]
counts = Counter(actions)
print(counts["STOP"]) # Output: 3
print(counts.most_common(1)) # Output: [('STOP', 3)]
```

#### Use-Case Scenarios
* **General Use-Case:** Frequency analyses, voting counts, or category counts.
* **Robotics & VLA Use-Case:** Checking label distributions in datasets to warning developers about class imbalance.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need to quickly tally objects or find the most frequent elements in a sequence.
* **Avoid this when:** You are doing complex multi-dimensional filtering (use pandas or NumPy instead).

---

### Timezones & UTC Datetime

#### Overview
In standard Python, `datetime.now()` returns the local time of the computer running the script, which changes depending on time zones. To guarantee consistent timestamps across servers, we use timezone-aware UTC times.
* `datetime.now(timezone.utc)`: Returns the current date and time pinned to the UTC timezone.
* `isoformat()`: Converts the datetime object into a standardized ISO-8601 string (e.g. `2026-07-09T18:00:00+00:00`).

#### Code Example
```python
from datetime import datetime, timezone

# Get current time in UTC timezone
now_utc = datetime.now(timezone.utc)
print("UTC ISO String:", now_utc.isoformat())
```

#### Use-Case Scenarios
* **General Use-Case:** Database logging, network packet timing, and transaction timestamps.
* **Robotics & VLA Use-Case:** Generating unique run IDs and tracking exactly when model logs were reviewed.

#### When to Use vs. When NOT to Use
* **Choose this when:** You need standardized, cross-region timestamps to audit execution histories.
* **Avoid this when:** You are asking a user for their local calendar input (which requires timezone offset translation).
