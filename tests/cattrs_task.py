"""Freeze and preflight the adapted cattrs task without invoking any model.

The public source, private user requirements and trusted verifier remain separate.
The original test.sh base/new commands run on a disposable validation copy;
SWE-Interact's five-step commit-shape wrapper is intentionally not used.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

from evaluation_runtime import DEFAULT_EVALUATOR, digest, file_hashes, load_helper, write_json
from functional_checks import xml_counts, xml_fingerprint
from task_adapters import apply_patch

BENCH_COMMIT = 'b32f98c3b8f76ca65e84341d1f30e5af7135f85d'
BASE_COMMIT = '6bc4708fb9b2ac52d9a18997e923da6a58916102'
SOURCE_HASH = '325a6d8a6adb2f7cfba39de58b353e3d5c05ed6e35be9359e0f226ed866bb688'
TASK_ID = 'deepswe_cattrs-partial-structuring-recovery'
ROOT = Path(__file__).resolve().parents[1]


def unpack(archive, destination):
    with tarfile.open(archive) as tar:
        tar.extractall(destination, filter='data')


def prepare(benchmark, source_archive, image, output):
    if digest(source_archive) != SOURCE_HASH:
        raise ValueError('cattrs source archive differs from the pinned input')
    head = subprocess.check_output(['git', '-C', str(benchmark), 'rev-parse', 'HEAD'], text=True).strip()
    task_dir = benchmark / 'data/multiturn' / TASK_ID
    dirty = subprocess.check_output(['git', '-C', str(benchmark), 'status', '--porcelain', '--',
                                    str(task_dir)], text=True)
    if head != BENCH_COMMIT or dirty.strip():
        raise ValueError('Benchmark task must match the pinned, unmodified commit')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('An immutable Docker image ID is required')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source_archive, output / 'source.tar.gz')
    shutil.copyfile(task_dir / 'tests/test.patch', output / 'test.patch')
    shutil.copyfile(task_dir / 'tests/test.sh', output / 'upstream-verifier.sh')
    shutil.copyfile(task_dir / 'solution/solution.patch', output / 'reference.patch')
    shutil.copyfile(task_dir / 'instruction.md', output / 'user-requirements.md')
    with tempfile.TemporaryDirectory(prefix='cattrs-freeze-') as tmp:
        source = Path(tmp) / 'source'
        unpack(source_archive, source)
        project = source / ('cattrs-' + BASE_COMMIT)
        if not (project / 'pyproject.toml').is_file():
            raise ValueError('Unexpected source archive layout')
        with tarfile.open(output / 'public.tar.gz', 'w:gz') as tar:
            for path in sorted(project.iterdir()):
                tar.add(path, arcname=path.name)
        # Test files are restored from trusted source, not from a solver submission.
        apply_patch(project, output / 'test.patch')
        shutil.copytree(project / 'tests', output / 'validator/tests')
        shutil.copyfile(project / 'test.sh', output / 'validator/test.sh')
    environment = {'kind': 'docker', 'image': image, 'network': 'none'}
    write_json(output / 'environment.json', environment)
    write_json(output / 'inputs.json', {
        'id': TASK_ID, 'base_commit': BASE_COMMIT, 'benchmark_commit': BENCH_COMMIT,
        'adapted': True, 'files': file_hashes(output),
        'adaptation': 'Original base/new commands; independent trusted test overlay; no five-step wrapper'})
    return output


def verify_inputs(bundle):
    manifest = json.loads((bundle / 'inputs.json').read_text())
    if (manifest['id'], manifest['base_commit'], manifest['benchmark_commit']) != (
            TASK_ID, BASE_COMMIT, BENCH_COMMIT):
        raise ValueError('Unexpected cattrs task identity')
    actual = file_hashes(bundle)
    actual.pop('inputs.json', None)
    if actual != manifest['files']:
        raise ValueError('Frozen cattrs inputs changed')
    return manifest


def check_status(result):
    counts = result['counts']
    if result['timed_out'] or result['exit_code'] not in (0, 1, 2) or not counts:
        return 'unknown'
    if counts['errors'] or counts['skipped'] or counts['xfailed'] or not counts['tests']:
        return 'unknown'
    if result['exit_code'] == 0 and not counts['failures']:
        return 'pass'
    return 'fail' if result['exit_code'] == 1 and counts['failures'] else 'unknown'


def run_checks(bundle, artifacts, output, timeout=300):
    """Preserve the submission and execute only trusted test commands, offline."""
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    environment = json.loads((bundle / 'environment.json').read_text())
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    before = file_hashes(artifacts)
    report = {'status': 'unknown', 'groups': [], 'environment': environment}
    with tempfile.TemporaryDirectory(prefix='cattrs-verifier-') as tmp:
        work = Path(tmp) / 'workspace'
        for path in artifacts.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(artifacts.resolve()):
                raise ValueError('Submitted symlink escapes workspace')
        shutil.copytree(artifacts, work, symlinks=True)
        for relative in ('tests', 'test.sh'):
            target = work / relative
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            source = bundle / 'validator' / relative
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)
        container = 'cattrs-check-' + uuid.uuid4().hex[:12]
        subprocess.run(['docker', 'run', '-d', '--name', container, '--network', 'none',
            '--cpus', '2', '--memory', '3g', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '-v', f'{work}:/testbed', '-v', f'{output}:/results', '-w', '/testbed',
            environment['image'], 'sleep', '1800'], check=True, capture_output=True)
        try:
            install = capture(work, output / 'install', ['docker', 'exec', container,
                'uv', 'pip', 'install', '--python', '/opt/testenv/bin/python', '--offline',
                '--no-deps', '--no-build-isolation', '-e', '/testbed'], 90)
            if install['exit_code'] != 0 or install['timed_out']:
                raise RuntimeError('Offline editable installation failed')
            location = subprocess.check_output(['docker', 'exec', container, 'python', '-c',
                'import cattrs; print(cattrs.__file__)'], text=True, timeout=20).strip()
            if not location.startswith('/testbed/'):
                raise RuntimeError('cattrs is not imported from the submitted workspace')
            report['import_path'] = location
            for group in ('base', 'new'):
                run = capture(work, output / group, ['docker', 'exec', '-e',
                    f'PYTEST_ADDOPTS=--junitxml=/results/{group}.xml', container,
                    'bash', '/testbed/test.sh', group], timeout)
                result = {'group': group, 'exit_code': run['exit_code'], 'timed_out': run['timed_out'],
                          'counts': xml_counts(output / f'{group}.xml'),
                          'outcome_sha256': xml_fingerprint(output / f'{group}.xml')}
                result['status'] = check_status(result)
                report['groups'].append(result)
            report['reward'] = int(all(g['exit_code'] == 0 and not g['timed_out'] for g in report['groups']))
            report['status'] = ('pass' if all(g['status'] == 'pass' for g in report['groups']) else
                                'fail' if any(g['status'] == 'fail' for g in report['groups']) else 'unknown')
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            report['error'] = str(exc)
        finally:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
    report['submission_unchanged'] = file_hashes(artifacts) == before
    if not report['submission_unchanged']:
        raise RuntimeError('Verifier mutated the submitted artifact')
    write_json(output / 'checks.json', report)
    return report


def qualify(bundle, output):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    report = {'qualified': False, 'model_calls': 0, 'inputs_sha256': digest(bundle / 'inputs.json'),
              'verifier_sha256': digest(Path(__file__)), 'runs': []}
    for variant in ('control', 'reference'):
        with tempfile.TemporaryDirectory(prefix='cattrs-preflight-') as tmp:
            work = Path(tmp) / 'workspace'
            unpack(bundle / 'public.tar.gz', work)
            if variant == 'reference':
                apply_patch(work, bundle / 'reference.patch')
            checks = run_checks(bundle, work, output / variant)
            # The upstream new suite imports PartialResult at collection time.
            # Retain that error as unknown in generic results, but identify the
            # expected missing API separately for the untouched control only.
            log = output / variant / 'new/stdout.log'
            known_absence = (variant == 'control' and log.is_file() and
                "cannot import name 'PartialResult' from 'cattrs'" in log.read_text(errors='replace'))
            row = {'variant': variant, 'checks': checks, 'expected_control_missing_api': known_absence}
            report['runs'].append(row)
            write_json(output / 'qualification.json', report)
    control, reference = (r['checks'] for r in report['runs'])
    report['qualified'] = bool(
        len(control['groups']) == 2 and control['groups'][0]['status'] == 'pass'
        and control.get('reward') == 0 and report['runs'][0]['expected_control_missing_api']
        and reference['status'] == 'pass' and reference.get('reward') == 1)
    report['reason'] = ('Environment/verifier preflight passed; collaboration protocol not yet qualified'
                        if report['qualified'] else 'Unexpected control/reference outcome; see raw checks')
    write_json(output / 'qualification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--benchmark', type=Path, required=True)
    prep.add_argument('--source-archive', type=Path, required=True)
    prep.add_argument('--image', required=True)
    preflight = sub.add_parser('preflight')
    preflight.add_argument('--inputs', type=Path, required=True)
    for item in (prep, preflight):
        item.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.benchmark.resolve(), args.source_archive.resolve(), args.image, args.output.resolve())
        print(args.output)
        return 0
    result = qualify(args.inputs.resolve(), args.output.resolve())
    print(json.dumps({'qualified': result['qualified'], 'reason': result['reason']}))
    return 0 if result['qualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
