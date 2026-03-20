# PhraseTools

## GUI Smoke Tests (pytest-qt)

Install dependencies in your local environment:

```bash
python3 -m pip install pytest pytest-qt PyQt5
```

Run GUI smoke tests:

```bash
pytest -q tests/gui_smoke_pytestqt.py
```

Run all unit tests (existing unittest suite):

```bash
python3 -m unittest discover -s tests
```

Run slow fuzz profile:

```bash
RUN_SLOW_TESTS=1 python3 -m unittest tests.test_clustering_fuzz_slow
```
