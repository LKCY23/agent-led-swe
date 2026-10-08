"""Scenario D: continue a frozen real artifact with the existing cattrs verifier."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

import cattrs_task
from evaluation_runtime import digest, file_hashes, snapshot, write_json
from task_adapters import apply_patch

TASK_ID = 'cattrs-continuation-repair'
BASE_COMMIT = cattrs_task.BASE_COMMIT
SNAPSHOT_HASH = '73293608b5759f45971b62e835edd6dab5dd6feae11f26dd1b35513a5ed25a1b'
CONTROL_OUTCOMES = (
    'df74753e4718bba5574fff1306c27a9398f19c0c6e9bd157a4f37922a4c1f17d',
    '1f19fb9250c52fad918d11f98cf4b19ea9a45baf8e90381e8673f0f4d8d3386b')
CACHES = ('.pytest_cache', '.hypothesis', '.ruff_cache', '.benchmarks')


def source_hash(source):
    return hashlib.sha256(json.dumps(file_hashes(source), sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def prepare(upstream, artifacts, output):
    cattrs_task.verify_inputs(upstream)
    if source_hash(artifacts) != SNAPSHOT_HASH:
        raise ValueError('Continuation source differs from the selected real artifact')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(upstream, output / 'upstream')
    shutil.copyfile(upstream / 'environment.json', output / 'environment.json')
    request = (Path(__file__).parent / 'cases/collaboration/cattrs-repair/request.md').read_text()
    (output / 'user-requirements.md').write_text(
        '# 本轮修复要求\n\n' + request + '\n# 其余保留的原始功能要求\n\n'
        + (upstream / 'user-requirements.md').read_text())
    shutil.copyfile(Path(__file__).parent / 'cases/swe/cattrs-repair/reference.patch',
                    output / 'reference.patch')
    with tempfile.TemporaryDirectory(prefix='cattrs-repair-input-') as tmp:
        public = Path(tmp) / 'public'
        snapshot(artifacts, public, exclude=CACHES)
        with tarfile.open(output / 'public.tar.gz', 'w:gz') as archive:
            for path in sorted(public.iterdir()):
                archive.add(path, arcname=path.name)
    write_json(output / 'inputs.json', {
        'id': TASK_ID, 'adapter': 'cattrs-repair', 'base_commit': BASE_COMMIT,
        'source_snapshot_sha256': SNAPSHOT_HASH, 'source': str(artifacts),
        'removed_cache_directories': CACHES, 'upstream_inputs_sha256': digest(upstream / 'inputs.json'),
        'adaptation': 'Same real artifact for both variants; original full base/new verifier',
        'files': file_hashes(output)})


def verify_inputs(bundle):
    manifest = json.loads((bundle / 'inputs.json').read_text())
    if (manifest['id'], manifest['base_commit'], manifest['source_snapshot_sha256']) != (
            TASK_ID, BASE_COMMIT, SNAPSHOT_HASH):
        raise ValueError('Unexpected continuation task identity')
    actual = file_hashes(bundle)
    actual.pop('inputs.json', None)
    if actual != manifest['files']:
        raise ValueError('Frozen continuation inputs changed')
    cattrs_task.verify_inputs(bundle / 'upstream')
    return manifest


def run_checks(bundle, artifacts, output, timeout=300):
    verify_inputs(bundle)
    return cattrs_task.run_checks(bundle / 'upstream', artifacts, output, timeout)


def qualify(bundle, output):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    report = {'qualified': False, 'model_calls': 0, 'inputs_sha256': digest(bundle / 'inputs.json'),
              'verifier_sha256': digest(Path(__file__)), 'runs': []}
    for variant in ('control', 'reference'):
        with tempfile.TemporaryDirectory(prefix='cattrs-repair-preflight-') as tmp:
            work = Path(tmp) / 'workspace'
            cattrs_task.unpack(bundle / 'public.tar.gz', work)
            if variant == 'reference':
                apply_patch(work, bundle / 'reference.patch')
            checks = run_checks(bundle, work, output / variant)
            report['runs'].append({'variant': variant, 'checks': checks})
            write_json(output / 'qualification.json', report)
    control, reference = (r['checks'] for r in report['runs'])
    report['qualified'] = (
        tuple(g['outcome_sha256'] for g in control['groups']) == CONTROL_OUTCOMES
        and control['status'] == 'fail' and reference['status'] == 'pass'
        and [g['counts']['tests'] for g in reference['groups']] == [7, 69])
    report['reason'] = ('Original two failures reproduced; repaired artifact passes full verifier'
                        if report['qualified'] else 'Unexpected control/reference outcome')
    write_json(output / 'qualification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--upstream-inputs', type=Path, required=True)
    prep.add_argument('--artifacts', type=Path, required=True)
    preflight = sub.add_parser('preflight')
    preflight.add_argument('--inputs', type=Path, required=True)
    for command in (prep, preflight):
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.upstream_inputs.resolve(), args.artifacts.resolve(), args.output.resolve())
        return 0
    report = qualify(args.inputs.resolve(), args.output.resolve())
    print(json.dumps({'qualified': report['qualified'], 'reason': report['reason']}))
    return 0 if report['qualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
