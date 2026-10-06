#!/usr/bin/env python3
"""Docker integration check using unchanged/reference artifacts, not model output."""
import argparse
import json
from pathlib import Path
import shutil

from evaluation_runtime import file_hashes, snapshot, write_json
from functional_checks import validate_task
from task_adapters import ROOT, SWE_NAMES, load_task, prepare_task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=SWE_NAMES, default='packaging')
    args = parser.parse_args()
    if args.case != 'packaging':
        from preflight_suite import qualify
        result = qualify(args.case, args.inputs.resolve(), args.output.resolve())
        if not result['qualified']:
            raise SystemExit(1)
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = json.loads((ROOT / 'tests/reports/swe-preflight-2026-10-05.json').read_text())
    results = []
    for name in ('packaging',):
        bundle = output / name
        bundle.mkdir()
        task = prepare_task(load_task(name, args.inputs), bundle / 'task')
        write_json(bundle / 'task.json', task)
        receipt = next(r for r in report['cases'] if r['name'] == name)
        # The frozen preflight data can live outside this tool's worktree.
        reference = args.inputs.resolve() / Path(receipt['evidence']).name / 'reference'
        for variant in ('unchanged', 'reference'):
            submitted = bundle / variant
            snapshot(bundle / task['workspace'], submitted)
            if variant == 'reference':
                # Synthetic oracle submission: copy source only, never hidden tests.
                shutil.rmtree(submitted / 'src')
                shutil.copytree(reference / 'src', submitted / 'src')
            (submitted / 'handoff.md').write_text('Synthetic pipeline check; not an Agent deliverable.\n')
            # A submission cannot make the validator pass by replacing trusted tests.
            hidden = task['validation']['groups']['FAIL_TO_PASS'][0].split('::')[0]
            (submitted / hidden).parent.mkdir(parents=True, exist_ok=True)
            (submitted / hidden).write_text('def test_fake_success():\n    assert True\n')
            before = file_hashes(submitted)
            checks = validate_task(task, bundle, submitted, bundle / f'{variant}-checks')
            assert before == file_hashes(submitted), 'Evaluation modified submitted artifacts'
            states = {c['id']: c['status'] for c in checks}
            expected = {'FAIL_TO_PASS': 'pass' if variant == 'reference' else 'fail', 'PASS_TO_PASS': 'pass'}
            assert states == expected, (name, variant, states)
            results.append({'case': name, 'submission': variant, 'checks': states,
                            'artifact_unchanged': True, 'new_document_preserved': True})
            write_json(output / 'results.json', {'mode': 'synthetic-artifact-validation', 'results': results})
            print(results[-1], flush=True)


if __name__ == '__main__':
    main()
