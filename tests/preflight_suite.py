#!/usr/bin/env python3
"""Qualify control/reference twice using the same validators as submitted artifacts."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from evaluation_runtime import digest, file_hashes, write_json
from functional_checks import validate_task
from suite_tasks import NAMES, ROOT, load_spec, unpack, verify_inputs
from task_adapters import apply_patch


def qualify(name, inputs, output):
    spec, spec_hash = load_spec(name)
    source = inputs / name
    verify_inputs(source, spec)
    output.mkdir(parents=True, exist_ok=False)
    environment = json.loads((source / 'environment.json').read_text())
    environment['executor_discard_files'] = spec.get('executor_discard_files', [])
    validation = json.loads((source / 'validation.json').read_text())
    validation['overlay'] = str(source / 'validator')
    task = {'environment': environment, 'validation': validation}
    report = {'task': name, 'qualified': False, 'spec_sha256': spec_hash,
              'inputs_sha256': digest(source / 'inputs.json'), 'environment': environment,
              'validation': {k: v for k, v in validation.items() if k != 'overlay'},
              'runs': [], 'model_calls': 0}
    states = {}
    for repetition in (1, 2):
        for variant in ('control', 'reference'):
            with tempfile.TemporaryDirectory(prefix='swe-suite-preflight-') as tmp:
                work = Path(tmp) / 'workspace'
                unpack(source / 'public.tar.gz', work)
                if variant == 'reference':
                    apply_patch(work, source / 'reference.patch')
                before = file_hashes(work)
                checks = validate_task(task, source, work, output / f'{variant}-{repetition}')
                if file_hashes(work) != before:
                    raise RuntimeError('Verifier modified the submitted workspace')
            row = {'variant': variant, 'repetition': repetition, 'checks': checks}
            report['runs'].append(row)
            required_ids = (list(validation['groups']) if validation['kind'] == 'pytest'
                            else ['OFFICIAL', *[c['id'] for c in validation.get('supplemental', [])]])
            expected = {key: ('fail' if variant == 'control' and key in ('OFFICIAL', 'FAIL_TO_PASS')
                             else 'pass') for key in required_ids}
            actual = {c['id']: c['status'] for c in checks}
            print(name, variant, repetition, actual, flush=True)
            states[variant, repetition] = [(c['id'], c['status'],
                    (c.get('details') or {}).get('outcome_sha256')) for c in checks]
            if not checks or actual != expected:
                report['reason'] = 'Control/reference check had an unexpected or incomplete result'
                write_json(output / 'qualification.json', report)
                return report
            write_json(output / 'qualification.json', report)
    if any(states[v, 1] != states[v, 2] for v in ('control', 'reference')):
        report['reason'] = 'Repeated outcomes differed'
    elif validation['kind'] == 'pytest' and (
            next(x for x in states['control', 1] if x[0] == 'PASS_TO_PASS')
            != next(x for x in states['reference', 1] if x[0] == 'PASS_TO_PASS')):
        report['reason'] = 'Control/reference regression outcomes differed'
    else:
        report.update(qualified=True, reason='Control failures and reference/regression passes repeated twice')
        if validation['kind'] == 'pytest':
            ref = next(r for r in report['runs'] if r['variant'] == 'reference')
            report['validation']['expected_outcomes'] = {
                c['id']: c['details']['outcome_sha256'] for c in ref['checks']}
    write_json(output / 'qualification.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=NAMES)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--register', action='store_true', help='Register only a passed qualification')
    args = parser.parse_args()
    report = qualify(args.name, args.inputs.resolve(), args.output.resolve())
    if args.register and report['qualified']:
        destination = ROOT / f'tests/reports/qualifications/{args.name}.json'
        destination.parent.mkdir(exist_ok=True)
        write_json(destination, report)
    raise SystemExit(0 if report['qualified'] else 1)
