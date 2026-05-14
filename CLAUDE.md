# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: my-first-claude-project

A Python CLI tool (`my-first-claude-project/json_to_csv.py`) that filters a JSON array and writes the result to CSV.

### Usage

```bash
python my-first-claude-project/json_to_csv.py <input.json> <output.csv> [--filter KEY=VALUE ...] [--match all|any]
```

Examples:
```bash
python my-first-claude-project/json_to_csv.py sample.json out.csv --filter status=active
python my-first-claude-project/json_to_csv.py sample.json out.csv --filter status=active --filter role=admin --match any
```

### Architecture

The script is a single-file CLI (`json_to_csv.py`) with no external dependencies. Key functions:

- `load_json` — reads and validates the input file (must be a JSON array of objects)
- `matches` — applies `--filter` conditions with AND (`all`) or OR (`any`) logic
- `collect_columns` — unions all keys across filtered records to build CSV headers (insertion-order preserved)
- `write_csv` — writes the filtered records using `csv.DictWriter`
- `main` — wires up `argparse` and calls the above in sequence

Missing keys in a record are treated as empty string for filter comparison and left blank in CSV output.

### Test data

- `sample.json` — valid 3-record array for manual testing
- `broken.json` — intentionally malformed JSON for error-path testing
