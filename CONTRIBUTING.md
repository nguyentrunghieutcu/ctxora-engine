# Contributing

Install development dependencies with `python -m pip install -e '.[dev]'`.

Before submitting changes, run:

```bash
python -m unittest discover -s tests -v
ruff check .
python -m py_compile server.py harness_context/*.py harness_context/*/*.py harness_context/*/*/*.py
```

Transport code must call application services rather than implementing retrieval or indexing. Refresh changes must preserve the previous valid snapshot until candidate validation and atomic promotion succeed.
