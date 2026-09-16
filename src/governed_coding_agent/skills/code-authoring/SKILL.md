# Code Authoring Style

You are writing code for an engineering project. Follow every rule below exactly.
Deviation requires explicit justification in a comment.

## Module structure

Every Python module must open with this line first:
```python
from __future__ import annotations
```
Then import groups separated by a blank line:
1. stdlib (`import os`, `from pathlib import Path`, ...)
2. third-party (`import psycopg`, `from pydantic import BaseModel`, ...)
3. local (`from governed_coding_agent.gateway import resolve_model`, ...)

A module-level logger is required in any module that logs:
```python
logger = logging.getLogger(__name__)
```

## Type hints

- **All** function parameters and return types must be annotated.
- Use lowercase generics: `list[str]`, `dict[str, Any]`, `tuple[int, ...]`.
- Prefer `X | None` over `Optional[X]`.

## Docstrings

- Every public function and class **must** have a docstring.
- One-line docstring for functions with <= 2 parameters and an obvious purpose.
- Google-style for anything more complex:

```python
def load(path: str, encoding: str = "utf-8") -> list[dict]:
    """Load records from a JSON file.

    Args:
        path: Absolute or relative path to the JSON file.
        encoding: File encoding (default utf-8).

    Returns:
        List of record dicts parsed from the file.

    Raises:
        FileNotFoundError: If path does not exist.
    """
```

## Naming

| Thing | Convention | Example |
|---|---|---|
| Function / variable / module | `snake_case` | `parse_csv`, `row_count` |
| Class | `PascalCase` | `CsvParser`, `ValidationResult` |
| Constant (module-level) | `UPPER_SNAKE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Private helper | `_snake_case` | `_build_dsn`, `_coerce_row` |

## Error handling

- Raise **specific** exception types. Never `raise Exception("...")`.
- Validate inputs at system boundaries (user input, file I/O, external APIs).
- Always include context in error messages:
  ```python
  raise ValueError(f"Column '{col}' missing from {path!r}")
  ```

## File and path handling

- Always use `pathlib.Path`, never string concatenation.
- Open files with an explicit `encoding` parameter.
- Use context managers for all file I/O.

## Data classes

Prefer `@dataclass` for value objects; use `@dataclass(frozen=True)` when
the object must be hashable or immutable.

## Resource management

Use context managers for database connections, file handles, HTTP sessions:
```python
with psycopg.connect(dsn) as conn:
    rows = conn.execute(sql, params).fetchall()
```

## Comments

Write **no** inline comments that restate what the code already says.
Write a comment only when the *why* is non-obvious.
