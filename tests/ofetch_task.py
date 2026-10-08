"""Prepare and independently verify the frozen ofetch collaboration task."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

from cattrs_task import unpack
from evaluation_runtime import DEFAULT_EVALUATOR, digest, file_hashes, load_helper, write_json
from task_adapters import apply_patch

BENCH_COMMIT = 'b32f98c3b8f76ca65e84341d1f30e5af7135f85d'
BASE_COMMIT = 'dfbe3ca4ef8a22fc023fca5a5ef530e525f5e523'
SOURCE_HASH = '3884af9fc3aad212f55d4fb55477dc94d1244e99108871b1933211874c56ad99'
TASK_ID = 'deepswe_ofetch-per-origin-circuit-breaker'
GROUPS = ('base-ok', 'base-baseURL', 'base-404', 'new')
TRUSTED_PATHS = ('test', 'package.json', 'pnpm-lock.yaml', 'vitest.config.ts')


def prepare(benchmark, source_archive, image, output):
    if digest(source_archive) != SOURCE_HASH:
        raise ValueError('Unexpected source archive')
    directory = benchmark / 'data/singleturn' / TASK_ID
    head = subprocess.check_output(['git', '-C', str(benchmark), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(benchmark), 'status', '--porcelain', '--', str(directory)], text=True)
    if head != BENCH_COMMIT or dirty.strip() or not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('Frozen benchmark and immutable image required')
    output.mkdir(parents=True, exist_ok=False)
    for source, name in [('tests/test.patch', 'test.patch'), ('solution/solution.patch', 'reference.patch'),
                         ('instruction.md', 'user-requirements.md')]:
        shutil.copyfile(directory / source, output / name)
    with tempfile.TemporaryDirectory(prefix='ofetch-input-') as tmp:
        source = Path(tmp)
        unpack(source_archive, source)
        project = source / ('ofetch-' + BASE_COMMIT)
        # Avoid silently inheriting a parent Git repository when applying patches.
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        with tarfile.open(output / 'public.tar.gz', 'w:gz') as tar:
            for p in sorted(project.iterdir()):
                if p.name != '.git':
                    tar.add(p, arcname=p.name)
        apply_patch(project, output / 'test.patch')
        if not (project / 'test/circuit-breaker.test.ts').is_file():
            raise ValueError('Trusted test patch was not applied')
        (output / 'validator').mkdir()
        for name in TRUSTED_PATHS:
            p = project / name
            if p.is_dir():
                shutil.copytree(p, output / 'validator' / name)
            else:
                shutil.copyfile(p, output / 'validator' / name)
    write_json(output / 'environment.json', {'kind': 'docker', 'image': image, 'network': 'none',
        'install_argv': [], 'workdir': '/testbed',
        'dependency_note': 'Pinned image dependencies resolve via /node_modules; no reference implementation in image'})
    write_json(output / 'inputs.json', {'id': TASK_ID, 'adapter': 'ofetch', 'base_commit': BASE_COMMIT,
        'benchmark_commit': BENCH_COMMIT, 'files': file_hashes(output),
        'adaptation': 'Original base selectors/new suite, independent trusted tests; no five-step wrapper'})


def verify_inputs(bundle):
    manifest = json.loads((bundle / 'inputs.json').read_text())
    if (manifest['id'], manifest['base_commit'], manifest['benchmark_commit']) != (TASK_ID, BASE_COMMIT, BENCH_COMMIT):
        raise ValueError('Unexpected ofetch task identity')
    actual = file_hashes(bundle)
    actual.pop('inputs.json', None)
    if actual != manifest['files']:
        raise ValueError('Frozen ofetch inputs changed')
    return manifest


def test_result(path, execution, group):
    result = {'group': group, 'exit_code': execution['exit_code'], 'timed_out': execution['timed_out'],
              'status': 'unknown', 'counts': None, 'outcome_sha256': None}
    if not path.is_file():
        return result
    data = json.loads(path.read_text())
    cases = [(case['fullName'], case['status']) for suite in data.get('testResults', [])
             for case in suite.get('assertionResults', [])]
    counts = {'tests': data.get('numTotalTests', 0), 'passed': data.get('numPassedTests', 0),
              'failures': data.get('numFailedTests', 0), 'skipped': data.get('numPendingTests', 0)}
    result.update(counts=counts, outcome_sha256=hashlib.sha256(
        json.dumps(sorted(cases)).encode()).hexdigest())
    selected = [(name, state) for name, state in cases if state not in ('pending', 'skipped', 'todo')]
    if (execution['timed_out'] or not selected or len(cases) != counts['tests']
            or (group == 'new' and counts['skipped'])
            or any(state not in ('passed', 'failed') for _, state in selected)):
        return result
    if execution['exit_code'] == 0 and data.get('success') is True and not counts['failures']:
        result['status'] = 'pass'
    elif execution['exit_code'] == 1 and counts['failures'] > 0:
        result['status'] = 'fail'
    return result


def run_checks(bundle, artifacts, output, timeout=300):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    environment = json.loads((bundle / 'environment.json').read_text())
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    before = file_hashes(artifacts)
    report = {'status': 'unknown', 'groups': [], 'environment': environment}
    with tempfile.TemporaryDirectory(prefix='ofetch-verifier-') as tmp:
        work = Path(tmp) / 'workspace'
        for path in artifacts.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(artifacts.resolve()):
                raise ValueError('Submitted symlink escapes workspace')
        shutil.copytree(artifacts, work, symlinks=True)
        # Solver tests and runner configuration cannot replace the independent oracle.
        for name in (*TRUSTED_PATHS, 'node_modules', '.npmrc'):
            target = work / name
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            trusted = bundle / 'validator' / name
            if trusted.is_dir():
                shutil.copytree(trusted, target)
            elif trusted.is_file():
                shutil.copyfile(trusted, target)
        container = 'ofetch-verify-' + uuid.uuid4().hex[:10]
        subprocess.run(['docker', 'run', '-d', '--name', container, '--network', 'none',
            '--cpus', '2', '--memory', '3g', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '-v', f'{work}:/testbed', '-v', f'{output}:/results', '-w', '/testbed',
            environment['image'], 'sleep', '1800'], check=True, capture_output=True, timeout=30)
        try:
            for group in GROUPS:
                selection = ['test/circuit-breaker.test.ts'] if group == 'new' else [
                    'test/index.test.ts', '-t', group.removeprefix('base-')]
                execution = capture(work, output / group, ['docker', 'exec', container,
                    '/opt/ofetch-deps/node_modules/.bin/vitest', 'run', *selection,
                    '--reporter=default', '--reporter=json', f'--outputFile=/results/{group}.json'], timeout)
                report['groups'].append(test_result(output / f'{group}.json', execution, group))
            report['status'] = ('pass' if all(g['status'] == 'pass' for g in report['groups']) else
                                'fail' if any(g['status'] == 'fail' for g in report['groups']) else 'unknown')
        finally:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=30)
    report['submission_unchanged'] = before == file_hashes(artifacts)
    if not report['submission_unchanged']:
        raise RuntimeError('Verifier changed submitted artifacts')
    write_json(output / 'checks.json', report)
    return report


def qualify(bundle, output):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    report = {'qualified': False, 'model_calls': 0, 'inputs_sha256': digest(bundle / 'inputs.json'),
              'verifier_sha256': digest(Path(__file__)), 'runs': []}
    for variant in ('control', 'reference'):
        with tempfile.TemporaryDirectory(prefix='ofetch-preflight-') as tmp:
            work = Path(tmp) / 'workspace'
            unpack(bundle / 'public.tar.gz', work)
            subprocess.run(['git', 'init', '-q', str(work)], check=True)
            if variant == 'reference':
                apply_patch(work, bundle / 'reference.patch')
                if not (work / 'src/circuit.ts').exists():
                    raise ValueError('Reference patch skipped')
            checks = run_checks(bundle, work, output / variant)
            report['runs'].append({'variant': variant, 'checks': checks})
            write_json(output / 'qualification.json', report)
    control, reference = [r['checks'] for r in report['runs']]
    report['qualified'] = (all(g['status'] == 'pass' for g in control['groups'][:-1])
        and control['groups'][-1]['status'] == 'fail'
        and reference['status'] == 'pass' and reference['groups'][-1]['counts']['passed'] == 54)
    write_json(output / 'qualification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--benchmark', type=Path, required=True)
    prep.add_argument('--source-archive', type=Path, required=True)
    prep.add_argument('--image', required=True)
    preflight = commands.add_parser('preflight')
    preflight.add_argument('--inputs', type=Path, required=True)
    for command in (prep, preflight):
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.benchmark.resolve(), args.source_archive.resolve(), args.image, args.output.resolve())
        return 0
    result = qualify(args.inputs.resolve(), args.output.resolve())
    print(json.dumps({'qualified': result['qualified']}))
    return 0 if result['qualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
