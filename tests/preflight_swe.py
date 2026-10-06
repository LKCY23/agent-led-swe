#!/usr/bin/env python3
"""Validate frozen SWE tasks with no-change and reference implementations.

This is a local ARM64 Docker adaptation, not an official benchmark submission.
Inputs are frozen dataset rows and extracted source archives kept under runs/.
No hosted LLM is called. Tests receive no host credentials; network requirements
are declared per case (DSPy downloads public fixtures).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import uuid

from evaluation_runtime import DEFAULT_EVALUATOR, digest, load_helper, write_json
from task_adapters import test_items, prepare_variants, requirements
from functional_checks import xml_counts, xml_fingerprint, run_test_groups


def summarize_runs(runs):
    expected = {(v, n, g) for v in ('control', 'reference') for n in (1, 2)
                for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')}
    indexed = {(r['variant'], r['repetition'], r['group']): r for r in runs}
    if len(runs) != 8 or set(indexed) != expected:
        return {'test_contract': 'unknown', 'reason': 'Incomplete or duplicate run matrix'}
    for run in runs:
        counts = run['counts']
        if run['timed_out'] or not counts or not counts['tests'] or counts['errors'] or counts['skipped']:
            return {'test_contract': 'unknown', 'reason': 'Timeout, missing, errored or skipped tests'}
    for (variant, repetition, group), run in indexed.items():
        counts = run['counts']
        if group == 'FAIL_TO_PASS' and counts.get('xfailed', 0):
            return {'test_contract': 'unknown', 'reason': 'Target tests must not xfail'}
        should_fail = variant == 'control' and group == 'FAIL_TO_PASS'
        if run['exit_code'] != (1 if should_fail else 0) or bool(counts['failures']) != should_fail:
            return {'test_contract': 'fail', 'reason': 'Control/reference behavior does not match the contract'}
        if counts != indexed[(variant, 3 - repetition, group)]['counts']:
            return {'test_contract': 'fail', 'reason': 'Repeated runs disagree'}
        if run.get('outcome_sha256') != indexed[(variant, 3 - repetition, group)].get('outcome_sha256'):
            return {'test_contract': 'fail', 'reason': 'Repeated test identities or outcomes disagree'}
    for n in (1, 2):
        if indexed[('control', n, 'PASS_TO_PASS')].get('outcome_sha256') != indexed[
                ('reference', n, 'PASS_TO_PASS')].get('outcome_sha256'):
            return {'test_contract': 'fail', 'reason': 'Regression outcomes, including xfails, changed'}
    return {'test_contract': 'pass', 'reason': 'Expected control failures and reference passes repeat twice; '
            'this does not establish that tests cover every written requirement'}


def preflight(spec_path, inputs, output):
    spec = json.loads(spec_path.read_text())
    if spec.get('adapter'):
        raise ValueError('Use prepare_suite_task.py and preflight_suite.py for the four-task suite')
    row = inputs / (spec['instance_id'] + '.json')
    metadata = json.loads(row.read_text())
    original = inputs / spec['instance_id'] / 'source'
    archive = original.parent / 'source.tar.gz'
    if digest(row) != spec['metadata_sha256'] or digest(archive) != spec['source_sha256']:
        raise ValueError('Frozen input hash mismatch')
    if metadata['base_commit'] != spec['base_commit']:
        raise ValueError('Base commit mismatch')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(row, output / 'case.json')
    shutil.copyfile(spec_path, output / 'spec.json')
    control, reference = prepare_variants(original, metadata, output, spec['patch_mode'] == 'mask')
    build = output / 'environment'
    build.mkdir()
    deps, pins = requirements(original, spec['name'])
    (build / 'requirements.txt').write_text('\n'.join(deps) + '\n')
    (build / 'constraints.txt').write_text('\n'.join(pins) + '\n')
    (build / 'Dockerfile').write_text(
        f'FROM {spec["python_image"]}\n'
        'RUN pip install --no-cache-dir uv==0.8.18\n'
        'COPY requirements.txt constraints.txt /tmp/\n'
        'RUN uv venv /opt/testenv && uv pip install --python /opt/testenv/bin/python '
        '-r /tmp/requirements.txt -c /tmp/constraints.txt\n'
        'ENV PATH="/opt/testenv/bin:$PATH"\n'
        'ENV PYTHONDONTWRITEBYTECODE=1\n')
    if spec['name'] == 'dspy':
        with (build / 'Dockerfile').open('a') as file:
            file.write('ENV LITELLM_LOCAL_MODEL_COST_MAP=True\n')
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    image = f'agent-led-swe-preflight-{spec["name"]}:{uuid.uuid4().hex[:10]}'
    network = spec.get('test_network', 'none')
    if network not in ('none', 'bridge'):
        raise ValueError('Unsupported test network mode')
    manifest = {'case': spec['instance_id'], 'image': image, 'platform': 'linux/arm64',
                'adapter_sha256': digest(Path(__file__)), 'max_test_runs': 8,
                'test_timeout_seconds': 180, 'network_during_tests': network, 'runs': []}
    write_json(output / 'manifest.json', manifest)
    record = capture(build, output / 'build-log', ['docker', 'build', '--platform', 'linux/arm64',
                     '-t', image, str(build)], 600)
    if record['exit_code'] != 0:
        raise RuntimeError(f'Dependency image build failed; see {output / "build-log"}')
    manifest['image_id'] = subprocess.check_output(['docker', 'image', 'inspect', image,
                                                   '--format', '{{.Id}}'], text=True).strip()
    for variant, template in [('control', control), ('reference', reference)]:
        for repetition in (1, 2):
            workspace = output / f'{variant}-{repetition}'
            shutil.copytree(template, workspace)
            evidence = output / f'{variant}-{repetition}-results'
            environment = {'image': manifest['image_id'], 'network': network}
            groups = {g: test_items(metadata[g]) for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')}
            results = run_test_groups(workspace, evidence, environment, groups)
            for outcome in results:
                manifest['runs'].append({'variant': variant, 'repetition': repetition, **outcome})
                write_json(output / 'manifest.json', manifest)
                print(manifest['runs'][-1], flush=True)
                counts = outcome['counts']
                expected_exit = 1 if variant == 'control' and outcome['group'] == 'FAIL_TO_PASS' else 0
                incomplete = (outcome['timed_out'] or not counts or not counts['tests']
                              or counts['errors'] or counts['skipped']
                              or outcome['exit_code'] not in (0, 1))
                if incomplete or outcome['exit_code'] != expected_exit:
                    manifest['summary'] = {'test_contract': 'unknown' if incomplete else 'fail',
                        'reason': 'Preflight stopped at the first unexpected outcome'}
                    write_json(output / 'manifest.json', manifest)
                    return manifest
    manifest['summary'] = summarize_runs(manifest['runs'])
    write_json(output / 'manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = preflight(args.spec.resolve(), args.inputs.resolve(), args.output.resolve())
    return 0 if manifest['summary']['test_contract'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
