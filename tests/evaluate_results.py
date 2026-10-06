#!/usr/bin/env python3
"""Run the frozen task verifier; no model judge or process-quality scoring.

Execution state, experimental validity and verifier outcome are separate.
Analyze process/skill quality later using the retained history.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation_runtime import adapter_hashes, digest, file_hashes, write_json
from functional_checks import validate_task


def task_status(checks):
    if any(row['status'] == 'fail' for row in checks):
        return 'fail'
    if not checks or any(row['status'] != 'pass' for row in checks):
        return 'unknown'
    return 'pass'


def check_bundle(bundle, plan):
    if plan.get('direct_guidance_sha256') and digest(bundle / 'direct-guidance.md') != plan['direct_guidance_sha256']:
        raise ValueError('Frozen direct guidance changed')
    for name, expected in [('case.json', plan['case_sha256']), ('rubrics.md', plan['rubric_sha256'])]:
        if digest(bundle / name) != expected:
            raise ValueError(f'Frozen input changed: {name}')
    if 'task_files' in plan and file_hashes(bundle / 'task') != plan['task_files']:
        raise ValueError('Prepared task or trusted validation materials changed')
    for target in plan.get('skill_targets', {}).values():
        if file_hashes(bundle / target['directory']) != target['files']:
            raise ValueError('Frozen skill snapshot changed')


def check_trial(source, result):
    for name, expected in result.get('capture_files', {}).items():
        if digest(source / 'capture' / name) != expected:
            raise ValueError(f'Captured log changed: {source.name}/{name}')
    for name, expected in result.get('native_files', {}).items():
        if digest(source / name) != expected:
            raise ValueError(f'Native invocation evidence changed: {source.name}/{name}')
    for name in ('before', 'after'):
        if (source / name).is_dir() and file_hashes(source / name) != result.get(f'fixture_{name}'):
            raise ValueError(f'Captured artifact changed: {source.name}/{name}')


def comparison_validity(plan, result):
    if result['run_status'] != 'completed':
        return {'status': 'unknown', 'reason': 'Execution did not complete'}
    if plan.get('skill_loading_mode') != 'native':
        return {'status': 'unknown', 'reason': 'Historical document-reading mode, not a native-skill trial'}
    if result.get('isolation', {}).get('status') != 'verified-discovery':
        return {'status': 'invalid', 'reason': 'Discovery isolation was not verified'}
    if result.get('skill_activation', {}).get('status') != 'verified':
        return {'status': 'invalid', 'reason': 'Native target activation/absence was not verified'}
    if plan.get('environment', {}).get('kind') == 'docker':
        if plan['environment'].get('execution_network') != 'internal-model-gateway-v1':
            return {'status': 'unknown', 'reason': 'Historical execution without the model-only network boundary'}
        if result.get('network_isolation', {}).get('status') != 'verified':
            return {'status': 'invalid', 'reason': 'Model-only worker network was not verified'}
    if result.get('execution_validity', {}).get('status') == 'invalid':
        return result['execution_validity']
    return {'status': 'valid', 'reason': 'Recorded execution and native invocation checks passed'}


def compare(plan, results):
    variants = list(dict.fromkeys(t['variant'] for t in plan['trials']))
    pairs = []
    for repetition in sorted({t['repetition'] for t in plan['trials']}):
        rows = {r['variant']: r for r in results if r['repetition'] == repetition}
        reference = plan.get('comparison_reference_variant', 'baseline')
        base = rows.get(reference, {}).get('fixture_before')
        fixtures_match = (None if base is None or any(r.get('fixture_before') is None for r in rows.values())
                          else all(r['fixture_before'] == base for r in rows.values()))
        pairs.append({'repetition': repetition,
                      'task_status': {v: r['task_status'] for v, r in rows.items()},
                      'functional_checks': {v: r['functional_checks'] for v, r in rows.items()},
                      'comparison_validity': {v: r['comparison_validity'] for v, r in rows.items()},
                      'usage': {v: r.get('usage') for v, r in rows.items()},
                      'elapsed_seconds': {v: r.get('elapsed_seconds') for v, r in rows.items()},
                      'fixtures_match': fixtures_match,
                      'comparison_eligible': fixtures_match is True and all(
                          r['comparison_validity']['status'] == 'valid' for r in rows.values())})
    return {'schema_version': 2, 'score_source': 'task_verifier', 'planned_trials': len(plan['trials']),
            'execution_counts': dict(Counter(r['run_status'] for r in results)),
            'task_counts': {v: dict(Counter(r['task_status'] for r in results if r['variant'] == v)) for v in variants},
            'pairs': pairs, 'analysis': 'Not performed; analyze the retained history separately'}


def evaluate_bundle(bundle, output):
    plan = json.loads((bundle / 'plan.json').read_text())
    check_bundle(bundle, plan)
    case = json.loads((bundle / 'case.json').read_text())
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'plan.json', {'schema_version': 2, 'source': str(bundle),
        'source_plan_sha256': digest(bundle / 'plan.json'), 'score_source': 'task_verifier',
        'adapter_files': adapter_hashes(), 'validation': case.get('validation'), 'model_calls': 0})
    results = []
    for number, trial in enumerate(plan['trials'], 1):
        source = bundle / trial['id']
        path = source / 'result.json'
        captured = json.loads(path.read_text()) if path.is_file() else {'run_status': 'not_started'}
        if path.is_file():
            check_trial(source, captured)
        # Never import historical judge scores or analytical conclusions.
        result = {**trial, **{key: captured.get(key) for key in (
            'run_status', 'usage', 'elapsed_seconds', 'fixture_before', 'fixture_after',
            'isolation', 'skill_activation', 'execution_validity', 'network_isolation')}}
        result['comparison_validity'] = comparison_validity(plan, captured)
        directory = output / f'verify-{number}'
        directory.mkdir()
        checks = []
        if not case.get('validation'):
            state, reason = 'not_configured', 'No task verifier is configured; analysis is not a substitute'
        elif not (source / 'after').is_dir():
            state, reason = 'not_run', 'Submitted artifact snapshot is missing'
        elif (source / 'workspace-export-error.json').exists():
            state, reason = 'not_run', 'Worker export failed; local files may not represent the executed artifact'
        else:
            checks = validate_task(case, bundle, source / 'after', directory / 'functional')
            state, reason = 'completed', 'Result determined only by the frozen task verifier'
        result.update(task_status=task_status(checks), functional_checks=checks,
                      verifier={'state': state, 'reason': reason}, score_source='task_verifier')
        write_json(directory / 'result.json', result)
        results.append(result)
    write_json(output / 'summary.json', compare(plan, results))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--output', type=Path, help='New verification directory; never overwrite old results')
    parser.add_argument('--functional-only', action='store_true', help='Compatibility alias; always verifier-only')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    output = args.output.resolve() if args.output else bundle / ('verification-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    try:
        results = evaluate_bundle(bundle, output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(output)
    return 0 if results and all(r['task_status'] == 'pass' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
