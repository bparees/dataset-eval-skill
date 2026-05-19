# Golden Dataset Evaluator

An [Agent Skill](https://docs.anthropic.com/en/docs/claude-code/skills) that evaluates domain-specific evaluation datasets against **Golden Evaluation Dataset** standards. Use it when building or reviewing eval sets for RAG, agents (tools/skills), or multi-turn conversation systems.

The skill uses Python scripts for the mechanical work of parsing and consolidating your dataset files. **All evaluation, scoring, classification, and grading is performed by the LLM** by reading the actual samples and applying the rubric in `SKILL.md`.

## What it does

Given a **directory of evaluation files on disk**, the skill:

1. **Parses** all supported files recursively (YAML, JSON, JSONL) via the Python script.
2. **Consolidates** all samples and structural metadata into a single JSON file for LLM review.
3. **Evaluates** (LLM) the samples against the Golden Dataset rubric: distribution, quality checklist, anti-pattern detection, and grading.
4. **Grades** (LLM) the dataset — Gold, Silver, Bronze, or Did Not Meet — with prioritized recommendations.

**In scope:** Application-level eval data tied to real domain workflows and Jobs-To-Be-Done (JTBD).

**Out of scope:** General NLU, toxicity/safety, or MMLU-style benchmarks (penalized or rejected per rubric).

### Mandatory requirement

At least **30% of samples must be human-verified** by a domain expert. Failing this blocks a passing grade regardless of other scores.

## Repository layout

```
dataset-eval-skill/
├── SKILL.md                 # Skill instructions and full evaluation rubric
├── README.md                # This file
└── scripts/
    ├── requirements.txt     # Python dependencies (PyYAML)
    ├── golden_evaluator.py  # Parses dataset, writes chunks + manifest for LLM
    ├── dataset_parser.py    # Parser library (also runnable standalone)
    └── README.md            # Script reference
```

## Installation

### 1. Install the skill (Cursor or Claude Code)

Skills are directories containing a `SKILL.md` file. Clone or copy this repository so the layout looks like:

```
<skill-install-dir>/golden-dataset-evaluator/
├── SKILL.md
└── scripts/
    └── ...
```

| Environment | Personal (all projects) | Project (team, repo-scoped) |
|-------------|-------------------------|-----------------------------|
| **Cursor** | `~/.cursor/skills/golden-dataset-evaluator/` | `.cursor/skills/golden-dataset-evaluator/` |
| **Claude Code** | `~/.claude/skills/golden-dataset-evaluator/` | `.claude/skills/golden-dataset-evaluator/` |

**Example — personal install (Cursor):**

```bash
git clone https://github.com/bparees/dataset-eval-skill.git ~/.cursor/skills/golden-dataset-evaluator
```

**Example — personal install (Claude Code):**

```bash
git clone https://github.com/bparees/dataset-eval-skill.git ~/.claude/skills/golden-dataset-evaluator
```

> **Note:** Do not install into `~/.cursor/skills-cursor/` — that path is reserved for Cursor's built-in skills.

### 2. Install Python dependencies

```bash
pip install -r scripts/requirements.txt
```

## Usage

### With an AI agent (recommended)

Point the agent at your evaluation dataset directory:

> *"Evaluate `/path/to/my-eval-dataset` against the golden dataset standards."*
> *"Grade my RAG eval set in `./eval-data`."*

The agent will:
1. Run `scripts/golden_evaluator.py` to parse and consolidate the dataset.
2. Read the consolidated output.
3. Apply the full rubric criteria from `SKILL.md` using its own judgment.
4. Report findings using the structured output template.

### From the command line

Run the parser/chunking step manually (the LLM then reads the output files):

```bash
cd scripts
python golden_evaluator.py /path/to/your/dataset ./reports
# optional: python golden_evaluator.py /path/to/your/dataset ./reports --chunk-size 30
```

**Output** in `./reports/eval_run_<timestamp>/`:

| File | Description |
|------|-------------|
| `manifest.json` | Structural summary + ordered list of all chunk files — read this first |
| `chunk_001_eval.json` … `chunk_NNN_eval.json` | Compact (truncated) 50-sample slices for LLM evaluation |
| `chunk_001.json` … `chunk_NNN.json` | Full-text versions for deep-diving specific samples |

The LLM reads the manifest, then processes every `_eval.json` chunk file in order, keeping a running tally of scenario types, grounding issues, verification coverage, and anti-pattern signals. After the last chunk it synthesizes findings into `eval_report_<YYYYMMDD>.md`.

## Try it: real-world sample dataset

A production-scale RAG evaluation dataset (501 samples, single YAML) for the Red Hat Developer Hub product is available at:

[`https://github.com/redhat-ai-dev/developer-lightspeed-evaluation/blob/main/dataset/dataset_raw.yaml`](https://github.com/redhat-ai-dev/developer-lightspeed-evaluation/blob/main/dataset/dataset_raw.yaml)

Download it, then ask the agent to evaluate it:

```bash
mkdir devhub-eval && curl -Lo devhub-eval/dataset_raw.yaml \
  https://raw.githubusercontent.com/redhat-ai-dev/developer-lightspeed-evaluation/main/dataset/dataset_raw.yaml
```

> *"Evaluate `./devhub-eval` against the golden dataset standards."*

This is a real dataset you can use as a reference for what a large synthetic-only RAG eval set looks like and where it falls short of the Golden Dataset standards.

## Dataset format

Place evaluation samples in a directory tree. The parser walks subdirectories and reads:

- **YAML** (`.yaml`, `.yml`) — list of samples, or `{ "data": [ ... ] }`
- **JSON** (`.json`) — array of samples, or single object
- **JSONL** (`.jsonl`) — one JSON object per line

Common sample fields:

| Field | Role |
|-------|------|
| `user_input` | Query or conversation input |
| `response` | Expected response or behavior |
| `context` | RAG source context (string or list) |
| `metadata` | Labels, JTBD tags, verification info, etc. |
| `expected_tools` / `tool_calls` | Agent eval — expected tool usage |

## Grading rubric (summary)

| Grade | Threshold | Notes |
|-------|-----------|-------|
| **Gold** | ~90%+ | Criteria comprehensively met; verification across all categories |
| **Silver** | ~70%+ | Most criteria met; gaps documented with a plan |
| **Bronze** | ~50%+ | Baseline met; known gaps documented |
| **Did not meet** | &lt;50% | Not recommended for product/model claims |

**Distribution target (within JTBD slices):**

| Category | Target |
|----------|--------|
| Core / happy path | ~50% |
| Edge cases & domain boundaries | ~15% |
| Negative scenarios | ~20% |
| Multi-turn | ~15% (or redistribute if N/A) |

## Anti-patterns detected

The LLM evaluates against these five common failure modes:

1. Bulk synthetic generation with minimal expert verification
2. Happy-path-only coverage
3. No domain expert in the loop
4. Generic or templated queries instead of real user language
5. Stale, one-time datasets with no maintenance plan

## Requirements

- Python 3.8+
- `PyYAML >= 6.0` (see `scripts/requirements.txt`)
- A Cursor or Claude Code environment that supports Agent Skills

## Related documentation

- [`SKILL.md`](SKILL.md) — Full skill instructions, rubric, and output template
- [`scripts/README.md`](scripts/README.md) — Script reference
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
