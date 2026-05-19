# Golden Dataset Evaluator Scripts

Python toolkit for parsing and consolidating evaluation datasets for LLM review.
**The scripts handle file I/O only — all evaluation, scoring, and grading is done by the LLM.**

## Quick start

```bash
pip install -r requirements.txt
cd scripts
python golden_evaluator.py ../dataset ../dataset/reports
```

The script splits the dataset into 50-sample chunk files. Read `manifest.json` first, then each chunk in order, evaluating samples as you go.

## Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `golden_evaluator.py` | Parse dataset, write chunks + manifest | `eval_run_<timestamp>/manifest.json`, `chunk_NNN.json` files |
| `dataset_parser.py` | Parser library; standalone structural report | `dataset_analysis_results.json` |

## What the scripts produce

**`golden_evaluator.py`** (primary entry point):
1. Recursively locates all `.yaml`, `.yml`, `.json`, and `.jsonl` files.
2. Parses each file and collects all samples.
3. Splits samples into chunk files of N samples each (default 50, override with `--chunk-size N`).
4. Writes a `manifest.json` with the structural summary and ordered list of chunk files.

Output layout:
```
eval_run_<timestamp>/
├── manifest.json          # structural summary + chunk list — read this first
├── chunk_001.json         # samples 1–50
├── chunk_002.json         # samples 51–100
└── ...
```

Each chunk file contains:
- `chunk` / `total_chunks` — position in the sequence
- `sample_range` — start/end/total sample indices
- `samples` — the actual sample objects

**`dataset_parser.py`** (library + standalone tool):
- File parsing for YAML, JSON, JSONL.
- Structural summary: field coverage, context length stats, sample type breakdown from field presence.
- No keyword matching, no pattern detection, no scoring.

## What the scripts do NOT do

- No scenario classification (core / edge / negative / multi-turn)
- No quality scoring or grading
- No anti-pattern detection
- No representativeness or realism assessment
- No human-verification checking

The LLM reads the consolidated JSON and applies the full Golden Dataset rubric from `SKILL.md`.

## Supported dataset formats

Samples may be in any mix of:
- **YAML** (`.yaml`, `.yml`) — list of samples, or `{ data: [...] }`
- **JSON** (`.json`) — array of samples, or single object
- **JSONL** (`.jsonl`) — one JSON object per line

## Common sample fields

| Field | Purpose |
|-------|---------|
| `user_input` | Query or conversation turn |
| `response` | Expected answer or behavior |
| `context` | RAG source context (string or list) |
| `expected_tools` / `tool_calls` | Agent eval — expected tool usage |
| `ground_truth` | Alternative expected answer field |
| `metadata` | Labels, JTBD tags, persona, verification info, etc. |

## Requirements

- Python 3.8+
- `PyYAML >= 6.0`
