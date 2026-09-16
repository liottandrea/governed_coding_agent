# Test Authoring Style

You are writing pytest tests for an engineering project. Follow every rule below.

## File structure

Test files live alongside the module under `tests/` and are named `test_<module>.py`.
Every test file opens with:
```python
from __future__ import annotations
```

## Naming conventions

| Thing | Convention |
|---|---|
| Test function | `test_<what>_<condition>` |
| Test class (grouping only) | `Test<Subject>` |
| Fixture | `snake_case`, no `test_` prefix |

## What to test

For every public function, write tests covering:
1. **Happy path** — valid inputs produce correct outputs.
2. **Edge cases** — empty inputs, boundary values, None where allowed.
3. **Error paths** — invalid inputs raise the documented exception type.

Do **not** test private helpers directly. Do **not** mock internal collaborators
unless they cross a real I/O boundary (network, filesystem, database).

## Parametrize

Prefer `@pytest.mark.parametrize` over copy-pasted test bodies:
```python
@pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("bad-email",        False),
    ("",                 False),
])
def test_validate_email(email: str, expected: bool) -> None:
    result = validate_email(email)
    assert result.valid == expected
```

## Fixtures

Define shared setup in fixtures, not in `setUp`/`tearDown` methods:
```python
@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    p = tmp_path / "data.csv"
    p.write_text("name,age\nAlice,30\n", encoding="utf-8")
    return p
```

Use `tmp_path` (pytest built-in) for any file I/O — never hardcode paths.

## Assertions

- Use plain `assert` (pytest rewrites them for readable diffs).
- Assert on the *semantics*, not the repr: `assert result.valid is True`, not `assert str(result) == "..."`.
- One logical assertion per test function where practical.

## Type hints

All test functions must be annotated with `-> None`.

## Docstrings

One-line docstrings for non-obvious tests only. Skip for self-explanatory names.

## No print statements

Never use `print()` in tests. Use `pytest.raises`, `capfd`, or `caplog` for
capturing side-effects.
