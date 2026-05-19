#!/usr/bin/env python3
"""
Golden Dataset Evaluator - Dataset Preparation Script
Parses and consolidates an evaluation dataset directory, then splits it into
LLM-readable chunks so the full dataset can be evaluated without skipping samples.

This script does NOT score, classify, or analyse the dataset — that is
entirely the LLM's responsibility.  It only handles mechanical extraction:
  - Recursively locates and parses all supported files (YAML, JSON, JSONL)
  - Reports structural facts (field coverage, sample counts, file formats)
  - Splits samples into fixed-size chunk files for sequential LLM consumption
  - Writes a manifest that lists every chunk file and its sample range
"""

import json
import math
import os
import sys
from datetime import datetime

from dataset_parser import DatasetParser

DEFAULT_CHUNK_SIZE = 50


def prepare_dataset(dataset_path: str, output_dir: str, chunk_size: int) -> dict:
    """
    Parse the dataset, write chunk files, and return a summary dict.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(output_dir, f"eval_run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    parser = DatasetParser(dataset_path)
    parse_results = parser.parse_directory()
    structural_summary = parser.structural_summary()

    samples = parser.samples
    total = len(samples)

    if total == 0:
        return {"error": "No samples found", "run_dir": run_dir,
                "parse_results": parse_results}

    # Split into chunks — write both full JSON and a compact eval view
    num_chunks = math.ceil(total / chunk_size)
    chunks_written = []

    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, total)
        chunk_samples = samples[start:end]
        chunk_num = chunk_idx + 1

        # Full chunk (all fields intact, for reference)
        chunk_file = os.path.join(run_dir, f"chunk_{chunk_num:03d}.json")
        chunk_data = {
            "chunk": chunk_num,
            "total_chunks": num_chunks,
            "samples_in_chunk": len(chunk_samples),
            "sample_range": {"start": start + 1, "end": end, "total": total},
            "samples": chunk_samples,
        }
        with open(chunk_file, "w", encoding="utf-8") as fh:
            json.dump(chunk_data, fh, indent=2, default=str)

        # Compact eval chunk — fields truncated for LLM consumption
        compact_samples = []
        for s in chunk_samples:
            ctx = s.get("context", "")
            if isinstance(ctx, list):
                ctx = " | ".join(str(c) for c in ctx)
            compact_samples.append({
                "_source_file": s.get("_source_file", ""),
                "user_input": str(s.get("user_input", ""))[:300],
                "response": str(s.get("response", ""))[:300],
                "context": str(ctx)[:300],
                "metadata": s.get("metadata", {}),
                # preserve any extra fields beyond the common ones
                **{k: v for k, v in s.items()
                   if k not in ("user_input", "response", "context", "metadata", "_source_file")},
            })

        compact_file = os.path.join(run_dir, f"chunk_{chunk_num:03d}_eval.json")
        compact_data = {
            "chunk": chunk_num,
            "total_chunks": num_chunks,
            "samples_in_chunk": len(chunk_samples),
            "sample_range": {"start": start + 1, "end": end, "total": total},
            "note": "Fields truncated to 300 chars for LLM evaluation. See chunk_NNN.json for full text.",
            "samples": compact_samples,
        }
        with open(compact_file, "w", encoding="utf-8") as fh:
            json.dump(compact_data, fh, indent=2, default=str)

        chunks_written.append({
            "chunk": chunk_num,
            "eval_file": compact_file,
            "full_file": chunk_file,
            "sample_range": f"{start + 1}–{end} of {total}",
            "sample_count": len(chunk_samples),
        })

    # Write manifest
    manifest = {
        "dataset_path": os.path.abspath(dataset_path),
        "prepared_at": datetime.now().isoformat(),
        "chunk_size": chunk_size,
        "total_samples": total,
        "total_chunks": num_chunks,
        "structural_summary": {
            **structural_summary,
            "files_processed": parse_results["files_processed"],
            "file_formats": dict(parse_results["file_formats"]),
            "parse_errors": parse_results["parse_errors"],
        },
        "chunks": chunks_written,
        "instructions": (
            "Read and evaluate each chunk_NNN_eval.json file in order (compact, truncated fields). "
            "For each chunk, assess every sample against the rubric criteria in SKILL.md. "
            "Record a running tally of findings (scenario types, quality issues, "
            "anti-pattern signals, verification coverage). "
            "Use chunk_NNN.json (full text) only if you need to inspect a specific sample in detail. "
            "After the final chunk, synthesize findings into eval_report_YYYYMMDD.md."
        ),
    }

    manifest_file = os.path.join(run_dir, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    return {
        "run_dir": run_dir,
        "manifest_file": manifest_file,
        "total_samples": total,
        "total_chunks": num_chunks,
        "chunk_size": chunk_size,
        "parse_results": parse_results,
        "structural_summary": structural_summary,
        "chunks": chunks_written,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python golden_evaluator.py <dataset_directory> [output_directory] [--chunk-size N]")
        print(f"  output_directory  defaults to current directory")
        print(f"  --chunk-size N    samples per chunk (default: {DEFAULT_CHUNK_SIZE})")
        sys.exit(1)

    dataset_path = sys.argv[1]
    output_dir = "."
    chunk_size = DEFAULT_CHUNK_SIZE

    args = sys.argv[2:]
    non_flag_args = []
    i = 0
    while i < len(args):
        if args[i] == "--chunk-size" and i + 1 < len(args):
            chunk_size = int(args[i + 1])
            i += 2
        elif not args[i].startswith("--"):
            non_flag_args.append(args[i])
            i += 1
        else:
            i += 1
    if non_flag_args:
        output_dir = non_flag_args[0]

    if not os.path.exists(dataset_path):
        print(f"Error: dataset path '{dataset_path}' does not exist")
        sys.exit(1)

    print(f"Parsing dataset: {dataset_path}")
    result = prepare_dataset(dataset_path, output_dir, chunk_size)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    total = result["total_samples"]
    num_chunks = result["total_chunks"]
    summary = result["structural_summary"]
    parse = result["parse_results"]

    print(f"\nDataset prepared — {total} samples split into {num_chunks} chunks of {chunk_size}")
    print(f"  Output directory : {result['run_dir']}")
    print(f"  Files parsed     : {len(parse['files_processed'])}")
    print(f"  File formats     : {dict(parse['file_formats'])}")
    if parse["parse_errors"]:
        print(f"  Parse errors     : {len(parse['parse_errors'])}")
        for err in parse["parse_errors"]:
            print(f"    {err['file']}: {err['error']}")

    print("\n  Field coverage:")
    for field, info in summary["field_coverage"].items():
        if info["count"] > 0:
            print(f"    {field}: {info['count']}/{total} ({info['percentage']}%)")

    print(f"\n  Sample types (structural): {summary['sample_types_by_structure']}")

    print(f"\n  Chunks written:")
    for c in result["chunks"]:
        print(f"    chunk_{c['chunk']:03d}_eval.json  — samples {c['sample_range']}  (eval/compact)")
        print(f"    chunk_{c['chunk']:03d}.json       — samples {c['sample_range']}  (full text)")

    print(f"\n  Manifest: {result['manifest_file']}")
    print("\nNext step: read manifest.json, then read each chunk_NNN_eval.json in order.")
    print("Track findings per chunk; synthesize into eval_report_YYYYMMDD.md after the last chunk.")


if __name__ == "__main__":
    main()
