#!/usr/bin/env python3
"""
Golden Dataset Evaluator - Dataset Parser
Parses evaluation dataset files and reports structural facts.
No analysis or scoring — that is the LLM's job.
"""

import yaml
import json
import os
import statistics
from collections import Counter
from typing import Dict, List, Any


class DatasetParser:
    """Parses evaluation dataset files and extracts structural metadata."""

    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.samples: List[Dict[str, Any]] = []

    def parse_directory(self) -> Dict[str, Any]:
        """Recursively parse all supported files in the dataset directory."""
        results = {
            'files_processed': [],
            'total_samples': 0,
            'parse_errors': [],
            'file_formats': Counter()
        }

        for root, _dirs, files in os.walk(self.dataset_path):
            for filename in sorted(files):
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ('.yaml', '.yml', '.json', '.jsonl'):
                    continue
                try:
                    samples = self._parse_file(file_path, ext)
                    if samples:
                        for s in samples:
                            s.setdefault('_source_file', file_path)
                        self.samples.extend(samples)
                        results['files_processed'].append(file_path)
                        results['total_samples'] += len(samples)
                        results['file_formats'][ext] += 1
                except Exception as exc:
                    results['parse_errors'].append({'file': file_path, 'error': str(exc)})

        return results

    def _parse_file(self, file_path: str, ext: str) -> List[Dict[str, Any]]:
        """Parse a single file and return a list of sample dicts."""
        with open(file_path, 'r', encoding='utf-8') as fh:
            if ext in ('.yaml', '.yml'):
                data = yaml.safe_load(fh)
                if isinstance(data, dict) and 'data' in data:
                    return data['data']
                return data if isinstance(data, list) else ([data] if data else [])
            elif ext == '.json':
                data = json.load(fh)
                return data if isinstance(data, list) else ([data] if data else [])
            elif ext == '.jsonl':
                return [json.loads(line) for line in fh if line.strip()]
        return []

    def structural_summary(self) -> Dict[str, Any]:
        """
        Return purely structural/factual metadata about the loaded samples.
        Nothing here is scored or analysed — counts and field presence only.
        """
        if not self.samples:
            return {'error': 'No samples loaded'}

        total = len(self.samples)

        # Count which samples have each common field (non-empty)
        common_fields = ['user_input', 'response', 'context', 'metadata',
                         'expected_tools', 'tool_calls', 'ground_truth']
        field_counts: Dict[str, int] = {f: 0 for f in common_fields}
        all_fields: Counter = Counter()

        for sample in self.samples:
            if not isinstance(sample, dict):
                continue
            for field in common_fields:
                if sample.get(field) not in (None, '', [], {}):
                    field_counts[field] += 1
            for key in sample:
                if not key.startswith('_'):
                    all_fields[key] += 1

        field_coverage = {
            f: {'count': c, 'percentage': round(c / total * 100, 1)}
            for f, c in field_counts.items()
        }

        # Structural sample type from field presence (not content analysis)
        sample_types: Counter = Counter()
        for sample in self.samples:
            if not isinstance(sample, dict):
                sample_types['unparseable'] += 1
                continue
            if sample.get('context') not in (None, '', [], {}):
                sample_types['RAG'] += 1
            elif sample.get('expected_tools') or sample.get('tool_calls'):
                sample_types['Agent'] += 1
            elif isinstance(sample.get('user_input'), list):
                sample_types['Multi-turn (list input)'] += 1
            else:
                sample_types['Single-turn'] += 1

        # Context lengths where present (factual)
        context_lengths = []
        for sample in self.samples:
            ctx = sample.get('context')
            if ctx:
                if isinstance(ctx, list):
                    context_lengths.append(sum(len(str(c)) for c in ctx))
                elif isinstance(ctx, str):
                    context_lengths.append(len(ctx))

        context_stats: Dict[str, Any] = {}
        if context_lengths:
            context_stats = {
                'count': len(context_lengths),
                'min_chars': min(context_lengths),
                'max_chars': max(context_lengths),
                'avg_chars': round(statistics.mean(context_lengths)),
            }

        return {
            'total_samples': total,
            'field_coverage': field_coverage,
            'all_fields_seen': dict(all_fields.most_common()),
            'sample_types_by_structure': dict(sample_types),
            'context_length_stats': context_stats,
        }


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dataset_parser.py <dataset_directory>")
        sys.exit(1)

    parser = DatasetParser(sys.argv[1])
    parse_results = parser.parse_directory()

    print(f"Files processed : {len(parse_results['files_processed'])}")
    print(f"Total samples   : {parse_results['total_samples']}")
    print(f"File formats    : {dict(parse_results['file_formats'])}")
    if parse_results['parse_errors']:
        print(f"Parse errors    : {len(parse_results['parse_errors'])}")
        for err in parse_results['parse_errors']:
            print(f"  {err['file']}: {err['error']}")

    if parse_results['total_samples'] == 0:
        sys.exit(1)

    summary = parser.structural_summary()
    print("\nField coverage:")
    for field, info in summary['field_coverage'].items():
        if info['count'] > 0:
            print(f"  {field}: {info['count']} / {summary['total_samples']} ({info['percentage']}%)")
    print(f"\nSample types (by structure): {summary['sample_types_by_structure']}")
    if summary.get('context_length_stats'):
        print(f"Context length stats: {summary['context_length_stats']}")

    output_file = 'dataset_analysis_results.json'
    with open(output_file, 'w') as fh:
        json.dump({'parse_results': parse_results, 'structural_summary': summary,
                   'samples': parser.samples}, fh, indent=2, default=str)
    print(f"\nResults written to {output_file}")


if __name__ == "__main__":
    main()
