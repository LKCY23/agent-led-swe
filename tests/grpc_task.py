"""Scenario C: empty project, live delivery evidence and independent service replay."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid

from cattrs_task import unpack, check_status
from evaluation_runtime import DEFAULT_EVALUATOR, digest, file_hashes, load_helper, write_json
from functional_checks import xml_counts, xml_fingerprint

TASK_ID = 'kv-store-grpc'
BASE_COMMIT = '2fd12b88aafdd04a52c298e3940bcb189f9766d6'
SOURCES = {
    'instruction.md': 'f4b3facc199d5b1c78db6e603ffa29ec1b93a77ff7d291e1a92b42e6bf582bed',
    'test_outputs.py': '115de2e964bbe689d07930527113422ef8a9e4be4eb958ad84594e3fcd2b1b0e',
    'solve.sh': '6bee2938ac9731d1156b0ca02b28c3d5793bf2cbe5f995c863d397093af01cb7'}


def prepare(source, image, output):
    if any(digest(source / name) != value for name, value in SOURCES.items()):
        raise ValueError('Task source differs from the selected immutable revision')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('Immutable dependency image required')
    output.mkdir(parents=True, exist_ok=False)
    for name in SOURCES:
        shutil.copyfile(source / name, output / name)
    shutil.copyfile(Path(__file__).with_name('grpc_live_probe.py'), output / 'live-probe.py')
    (output / 'user-requirements.md').write_text(
        '# 原始功能与协议要求\n\n' + (source / 'instruction.md').read_text()
        + '\n# 环境适配与交付说明\n\ngrpcio 和 grpcio-tools 1.73.0 已系统级预装，安装工作已移到环境准备阶段。'
          '工作目录为 /app。保留协议、路径、类名、端口及交付时服务仍运行的要求。'
          '提供简短的构建与启动说明，方便后续修改；不要求特定文档数量。\n')
    with tarfile.open(output / 'public.tar.gz', 'w:gz') as archive:
        directory = tarfile.TarInfo('.')
        directory.type, directory.mode = tarfile.DIRTYPE, 0o755
        archive.addfile(directory)
    write_json(output / 'environment.json', {'kind': 'docker', 'image': image,
        'network': 'none', 'workdir': '/app', 'install_argv': []})
    write_json(output / 'inputs.json', {'id': TASK_ID, 'adapter': 'grpc', 'base_commit': BASE_COMMIT,
        'adaptation': 'Dependencies preinstalled offline; empty public project; original seven assertions',
        'files': file_hashes(output)})


def verify_inputs(bundle):
    manifest = json.loads((bundle / 'inputs.json').read_text())
    if (manifest['id'], manifest['base_commit']) != (TASK_ID, BASE_COMMIT):
        raise ValueError('Unexpected gRPC task identity')
    actual = file_hashes(bundle)
    actual.pop('inputs.json', None)
    if actual != manifest['files']:
        raise ValueError('Frozen gRPC inputs changed')
    return manifest


def probe_container(bundle, container, output):
    """Observe only: never start or repair the developer's service."""
    output.mkdir(parents=True, exist_ok=False)
    try:
        run = subprocess.run(['docker', 'exec', '-i', container, 'python', '-I', '-'],
            input=(bundle / 'live-probe.py').read_text(), capture_output=True, text=True, timeout=30)
        (output / 'stdout.log').write_text(run.stdout)
        (output / 'stderr.log').write_text(run.stderr)
        result = json.loads(run.stdout.strip())
        if run.returncode not in (0, 1) or result.get('status') not in ('pass', 'fail'):
            raise ValueError('Unexpected live probe result')
        result['exit_code'] = run.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = {'status': 'unknown', 'error': str(exc)}
    write_json(output / 'result.json', result)
    return result


def capture_live(bundle, worker, output):
    verify_inputs(bundle)
    return probe_container(bundle, worker.container, output)


def run_checks(bundle, artifacts, output, timeout=120):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    before = file_hashes(artifacts)
    environment = json.loads((bundle / 'environment.json').read_text())
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    report = {'status': 'unknown', 'groups': []}
    with tempfile.TemporaryDirectory(prefix='grpc-verifier-') as tmp:
        work = Path(tmp) / 'app'
        for path in artifacts.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(artifacts.resolve()):
                raise ValueError('Submitted symlink escapes workspace')
        shutil.copytree(artifacts, work, symlinks=True)
        oracle = Path(tmp) / 'oracle'
        oracle.mkdir()
        shutil.copyfile(bundle / 'test_outputs.py', oracle / 'test_outputs.py')
        container = 'grpc-check-' + uuid.uuid4().hex[:12]
        subprocess.run(['docker', 'run', '-d', '--name', container, '--network', 'none',
            '--cpus', '2', '--memory', '3g', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '-v', f'{work}:/app', '-v', f'{oracle}:/oracle:ro', '-v', f'{output}:/results',
            '-w', '/app', environment['image'], 'sleep', 'infinity'], check=True, capture_output=True)
        try:
            if (work / 'server.py').is_file():
                subprocess.run(['docker', 'exec', '-d', container, 'sh', '-c',
                    'exec python /app/server.py > /results/server.log 2>&1'], check=True)
                # Readiness is separate from correctness; the original RPC tests follow.
                ready = 'import socket,time\nfor _ in range(100):\n try:\n  s=socket.create_connection(("127.0.0.1",5328),.1);s.close();break\n except OSError: time.sleep(.1)\nelse: raise SystemExit(1)'
                readiness = subprocess.run(['docker', 'exec', container, 'python', '-c', ready],
                                           capture_output=True, text=True, timeout=15)
                report['startup_exit_code'] = readiness.returncode
            report['replay_rpc'] = probe_container(bundle, container, output / 'replay-rpc')
            run = capture(work, output / 'canonical', ['docker', 'exec', '-e',
                'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1', container, 'python', '-m', 'pytest',
                '-c', '/dev/null', '--confcutdir=/oracle', '/oracle/test_outputs.py', '-v',
                '--junitxml=/results/canonical.xml'], timeout)
            group = {'group': 'canonical', 'exit_code': run['exit_code'], 'timed_out': run['timed_out'],
                'counts': xml_counts(output / 'canonical.xml'),
                'outcome_sha256': xml_fingerprint(output / 'canonical.xml')}
            group['status'] = check_status(group)
            report['groups'] = [group]
            report['status'] = group['status']
            if report['status'] == 'pass' and report['replay_rpc']['status'] != 'pass':
                report['status'] = report['replay_rpc']['status']
        finally:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
    report['submission_unchanged'] = file_hashes(artifacts) == before
    if not report['submission_unchanged']:
        raise RuntimeError('Verifier changed submission')
    write_json(output / 'checks.json', report)
    return report


def qualify(bundle, output):
    verify_inputs(bundle)
    output.mkdir(parents=True, exist_ok=False)
    report = {'qualified': False, 'model_calls': 0, 'inputs_sha256': digest(bundle / 'inputs.json'),
              'verifier_sha256': digest(Path(__file__)), 'runs': []}
    image = json.loads((bundle / 'environment.json').read_text())['image']
    for variant in ('control', 'reference'):
        with tempfile.TemporaryDirectory(prefix='grpc-preflight-') as tmp:
            work = Path(tmp) / 'app'
            work.mkdir()
            if variant == 'reference':
                container = 'grpc-reference-' + uuid.uuid4().hex[:10]
                subprocess.run(['docker', 'run', '-d', '--name', container, '--network', 'none',
                    '-e', 'PIP_NO_INDEX=1', '-e', 'PIP_DISABLE_PIP_VERSION_CHECK=1',
                    '-v', f'{work}:/app', '-v', f'{bundle}:/private:ro', '-w', '/app', image,
                    'sleep', 'infinity'], check=True, capture_output=True)
                try:
                    run = subprocess.run(['docker', 'exec', container, 'bash', '/private/solve.sh'],
                                         capture_output=True, text=True, timeout=60)
                    (output / 'reference-setup.log').write_text(run.stdout + run.stderr)
                    if run.returncode:
                        raise RuntimeError('Original reference script failed')
                    time.sleep(.5)
                    report['reference_live'] = probe_container(bundle, container, output / 'reference-live')
                    stop = "import pathlib,os,signal\nfor p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):\n try:\n  a=p.read_bytes().split(b'\\0')\n  if len(a)>1 and a[1]==b'server.py': os.kill(int(p.parent.name),signal.SIGTERM)\n except (FileNotFoundError,ProcessLookupError): pass"
                    subprocess.run(['docker', 'exec', container, 'python', '-c', stop],
                                   check=True, capture_output=True)
                    report['stopped_live'] = probe_container(bundle, container, output / 'stopped-live')
                finally:
                    subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
            checks = run_checks(bundle, work, output / variant)
            report['runs'].append({'variant': variant, 'checks': checks})
            write_json(output / 'qualification.json', report)
    control, reference = (r['checks'] for r in report['runs'])
    report['qualified'] = (control['status'] == 'fail' and reference['status'] == 'pass'
        and reference['groups'][0]['counts']['tests'] == 7
        and report['reference_live']['status'] == 'pass' and report['stopped_live']['status'] == 'fail')
    write_json(output / 'qualification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--source', type=Path, required=True)
    prep.add_argument('--image', required=True)
    preflight = sub.add_parser('preflight')
    preflight.add_argument('--inputs', type=Path, required=True)
    for command in (prep, preflight):
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.source.resolve(), args.image, args.output.resolve())
        return 0
    report = qualify(args.inputs.resolve(), args.output.resolve())
    print(json.dumps({'qualified': report['qualified']}))
    return 0 if report['qualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
