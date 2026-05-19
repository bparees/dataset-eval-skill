---
name: golden-dataset-evaluator
description: Evaluates a domain-specific evaluation dataset (provided as a directory of files on disk) against the Golden Evaluation Dataset standards and provides recommendations for gap closure. Includes a Python script that parses and consolidates the dataset for LLM review.
version: 2.0.0
---

# Skill: Golden Dataset Evaluator

## Description
This skill acts as an expert Quality Engineer and AI Engineer to evaluate domain-specific evaluation datasets for RAG, agent/tool/skill, and multi-turn conversation systems. It scans a **directory of files on disk**, reads the samples, and ensures the dataset achieves the properties of a **Golden Evaluation Dataset**: fidelity to production traffic, comprehensive failure-mode coverage, and stable levels for regression testing.

The Python script handles only mechanical file parsing and consolidation. **All evaluation, scoring, classification, and grading is performed by the LLM** by reading and reasoning about the actual sample content against the rubric below.

## Instructions

When a user provides a path to a directory containing their evaluation dataset files:

**Step 1 — Parse and split the dataset into chunks:**

First, verify the required Python dependency is available:
```bash
python -c "import yaml" 2>/dev/null || pip install -r scripts/requirements.txt
```

Then run the evaluator:
```bash
python scripts/golden_evaluator.py <dataset_directory> <output_directory> [--chunk-size N]
```
Always pass the user's current working directory as `<output_directory>` so outputs land alongside their project files. The default chunk size is 50 samples; adjust with `--chunk-size` if needed.

The script produces an `eval_run_<timestamp>/` directory containing:
- `manifest.json` — structural summary and the ordered list of chunk files
- `chunk_001.json`, `chunk_002.json`, … — 50-sample slices of the full dataset

**Step 2 — Read the manifest:**
Read `manifest.json` first. Note the structural summary (total samples, field coverage, sample type breakdown). This tells you what you are about to evaluate before you read any samples.

**Step 3 — Read and evaluate every chunk in order:**
For each chunk listed in the manifest, read the `chunk_NNN_eval.json` file (compact, fields truncated to 300 chars — sufficient for evaluation). Read the full `chunk_NNN.json` only if you need to inspect a specific sample's complete text.

For every sample in each chunk, assess it against the rubric criteria below. Maintain a running tally as you go:
   - **Scenario counts:** how many samples are Core / Edge / Negative / Multi-turn (based on reading what they actually ask, not keywords)
   - **Grounding issues:** samples where the response does not appear grounded in the provided context, or where the context and query topic do not match
   - **Verification signals:** count of samples with any human-verification metadata (`verified_by`, `reviewed`, `validated`, `human_checked`, etc.)
   - **Realism issues:** samples with mechanical or templated phrasing (note the sample index and the pattern)
   - **Anti-pattern signals:** any evidence of the 5 anti-patterns (note sample indices)
   - **Quality flags:** any other content problems (wrong answers, missing ground truth, etc.)

Keep the tally as running counts/notes so you can synthesize at the end. You do not need to report on each chunk individually.

**Step 4 — Write the evaluation report:**
After reading all chunks, synthesize your full-dataset findings using the output template below. Write the report to `eval_report_<YYYYMMDD>.md` in the same `eval_run_<timestamp>/` directory. Then display a brief summary to the user.

---

## Context & Rules

### 1. Scope Constraints
* **In Scope:** Application-level evaluation focused on specific use cases grounded in the team's actual domain workflows. Data quality principles, human vs. synthetic balance, and sizing recommendations are strictly enforced.
* **Out of Scope:** Reject or heavily penalize datasets that rely on general NLU, toxicity/safety benchmarks, or MMLU-style benchmarks, as these are handled separately.

### 2. Sizing & Distribution
A recommended starting point is **100 samples**. Ensure the data across the files adheres to the following distribution (applied within Jobs-To-Be-Done slices):
* **Core / Happy Path (~50%):** Standard domain-specific queries that represent the primary intended use of the system.
* **Edge Cases & Domain Boundaries (~15%):** Queries that test the limits of system support, unusual configurations, or complex multi-step scenarios.
* **Negative Scenarios (~20%):** Out-of-scope questions, adversarial inputs, ambiguous queries, "I don't know" responses, and domain boundaries.
* **Multi-turn (~15%):** Multi-turn conversations with follow-up queries (if applicable; otherwise redistribute to Core and Edge cases).

Classify each sample based on what the query is actually asking and what the expected response does. Do not use keyword matching — a query about an error can be a happy-path troubleshooting guide, not a negative scenario. Your running tally from the chunk passes is your distribution data.

### 3. Data Quality Checklist

Evaluate each criterion by synthesizing what you observed across all chunks:

**Representativeness:**
* Data reflects real-world, domain-specific usage patterns — queries read like something a real user of this system would actually type.
* Multiple user personas and complexity levels are represented, with no single topic or phrasing pattern dominating.
* Every scenario slice is traceable to a documented **Jobs To Be Done (JTBD)** defined by the PM. For each JTBD, the set must include at least one happy-path and one non-happy case.

**Grounding & Expected References:**
* Every sample has a domain-specific expected reference or ground truth.
* **For RAG:** Source context is provided or can be fetched at run-time, and the expected response is clearly grounded in that context (not hallucinated).
* **For Agents:** Expected tool calls and parameters are clearly specified and match what the system would actually need to do.
* **For Multi-turn:** Expected behavior is defined at each turn, not just the final turn.

**Human Verification (Mandatory):**
* At least **30% of samples must be human-verified** by a domain expert (typically a QE).
* Look for explicit verification signals in metadata (`verified_by`, `reviewed`, `validated`, `human_checked`, etc.), but also assess overall whether the dataset has the hallmarks of expert curation: accurate domain terminology, realistic queries, correct and nuanced expected responses.
* Verification must cover queries, labels, and expected responses/behavior, and be distributed across all categories (not just happy paths).
* **This is a hard requirement.** If it is clearly not met, the dataset cannot receive a passing grade regardless of other scores.

**Realism:**
* Queries read as natural human language with varied phrasing and intents, rather than templates.
* Watch for signs of bulk LLM generation: overly formal language ("Certainly, I would be happy to assist"), repetitive response structures, identical phrasing across many queries, or responses that are far more detailed than a real user would need.

**Synthetic Data Quality (if applicable):**
* Synthetic data must be multi-LLM generated (using at least 2 different LLMs) to avoid monoculture.
* All synthetic samples are grounded in source material and quality filtered — not free-generated.

**Environment Setup & Cleanup:**
* Pre-conditions (required environment state before evaluation), setup steps, and cleanup steps (how to reset the environment after evaluation) are thoroughly documented somewhere in the dataset or its accompanying documentation.

### 4. Anti-Patterns to Flag

Identify any of the following and explain why they are a problem:

1. **Bulk synthetic data generation with minimal verification:** Evidence includes uniform response structure, very formal language, lack of variation in query phrasing, no or minimal human verification signals, and all samples generated with the same obvious template.
2. **Happy-path only:** The dataset lacks meaningful coverage of failure cases, edge conditions, or out-of-scope queries. A system evaluated only against happy paths cannot detect real-world regressions.
3. **No domain expert in the loop:** The queries or expected responses contain terminology errors, unrealistic scenarios, or incorrect expected outputs that a domain expert would have caught.
4. **No real user-aligned data:** Queries use generic or templated phrasing rather than modeling how actual users of this specific system talk. Contrast with real support tickets or user interviews.
5. **Stale evaluation data:** The dataset appears to be a one-time artifact with no versioning, timestamps, or maintenance plan, rather than a living artifact updated as the system evolves.

### 5. Grading Rubric
Grade the dataset based on how well it meets the applicable checklist criteria. **Note: At least 30% human verification by domain experts is mandatory for all levels.**
* **Gold (~90%+):** Met criteria comprehensively + human verification across all categories.
* **Silver (~70%):** Met most criteria; remaining gaps are documented with a plan to address them.
* **Bronze (~50%):** Met baseline criteria; essential coverage is in place but known gaps are documented.
* **Did not meet (<50%):** Fails to meet the baseline and is not recommended for model/product claims.

---

## Automation Scripts

The `scripts/` directory provides Python tooling for the mechanical parts of evaluation:

### `scripts/golden_evaluator.py` — Dataset Preparation
Parses all files in the dataset directory and writes a single consolidated JSON containing all samples and structural metadata (field coverage, file counts, sample type breakdown by structure).

```bash
python scripts/golden_evaluator.py <dataset_directory> [output_directory]
```

### `scripts/dataset_parser.py` — Parser Library
Used by `golden_evaluator.py`. Can also be run standalone to inspect a dataset's structure without writing a full consolidated file.

```bash
python scripts/dataset_parser.py <dataset_directory>
```

### Installation
```bash
pip install -r scripts/requirements.txt
```

---

## Output Format
*When responding to the user's directory submission, use the following template:*

**1. Dataset Overview**
Summary of what was parsed: file count, total samples, file formats, and structural field coverage (e.g. what percentage have `context`, `response`, `metadata`). Note any files that failed to parse.

**2. Scenario Distribution**
Your assessment of how samples are distributed across Core / Edge Cases / Negative / Multi-turn, based on reading the actual content. Compare to the 50/15/20/15 target and explain any significant gaps.

**3. Checklist Assessment**
For each criterion — Representativeness, Grounding, Human Verification, Realism, Synthetic Data Quality, Environment Setup — give a **Pass / Partial / Fail** rating with specific evidence from the samples you read. Quote or describe actual examples where they illustrate a pass or a problem.

**4. Detected Anti-Patterns**
List any of the 5 anti-patterns found, with concrete evidence from the dataset. If none are found, say so.

**5. Current Grade**
Gold / Silver / Bronze / Did Not Meet — with a brief justification referencing specific checklist outcomes and any mandatory failures.

**6. Recommendations for Closing Gaps**
Actionable, specific steps prioritized by criticality:
- **P0 (Mandatory):** Must be addressed before any grade can be awarded (e.g. human verification below 30%).
- **P1 (High):** Required to reach Silver or above.
- **P2 (Important):** Required to reach Gold.
Include concrete guidance: how many samples to add, what kinds, what fields to add to metadata, etc.
