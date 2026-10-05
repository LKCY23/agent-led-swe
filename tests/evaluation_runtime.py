"""Shared execution environments, capture and evidence helpers."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import tempfile

from agent_adapters import get_adapter
from model_config import credential, claude_environment, DEFAULT_CREDENTIALS


DEFAULT_EVALUATOR = Path.home() / '.codex/skills/skill-evaluator'


def adapter_hashes():
    root = Path(__file__).parent
    names = [
        'evaluation_runtime.py', 'run_evaluation.py', 'evaluate_results.py', 'run_smoke.py',
        'task_adapters.py', 'functional_checks.py', 'model_config.py']
    names += [str(p.relative_to(root)) for p in sorted((root / 'agent_adapters').glob('*.py'))]
    return {name: digest(root / name) for name in names}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError('timeout must be finite and positive')
    return number


def file_hashes(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            result[str(path.relative_to(root))] = {'symlink': str(path.readlink())}
        elif path.is_file():
            result[str(path.relative_to(root))] = digest(path)
    return result


def snapshot(source, destination):
    """Preserve all submitted files, including new documents; omit only Git internals."""
    shutil.copytree(source, destination, symlinks=True, ignore=shutil.ignore_patterns('.git'))
    return file_hashes(destination)


def freeze_helpers(source, destination):
    destination.mkdir()
    for name in ('capture.py', 'inspect_codex_trace.py'):
        shutil.copyfile(source / 'scripts' / name, destination / name)
    return {p.name: digest(p) for p in destination.iterdir()}


def load_helper(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_worker_image(environment, version, output, agent='codex'):
    """Add a pinned agent CLI to a dependency-only image; no task/solution/auth layers."""
    adapter = get_adapter(agent)
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('A pinned agent npm version is required')
    output = output.resolve()
    output.mkdir()
    base = environment['image']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', base):
        raise ValueError('Worker base image must be identified by immutable Docker image ID')
    base_tag = 'agent-led-swe-base:' + base[7:]
    (output / 'Dockerfile').write_text(
        'FROM node:22-bookworm-slim AS cli\n'
        f'RUN npm install -g {adapter.npm_package}@{version}\n'
        f'FROM {base_tag}\n'
        'COPY --from=cli /usr/local/bin/node /usr/local/bin/node\n'
        'COPY --from=cli /usr/local/lib/node_modules /usr/local/lib/node_modules\n'
        f'RUN ln -s /usr/local/lib/node_modules/{adapter.cli_entrypoint} /usr/local/bin/{adapter.executable}\n'
        'RUN apt-get update && apt-get install -y --no-install-recommends git '
        '&& rm -rf /var/lib/apt/lists/*\n')
    tag = 'agent-led-swe-worker:' + agent + '-' + version + '-' + digest(output / 'Dockerfile')[:16]
    cached = subprocess.run(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'],
                            capture_output=True, text=True)
    if cached.returncode == 0:
        return cached.stdout.strip()
    subprocess.run(['docker', 'tag', base, base_tag], check=True)
    receipt = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture(
        output, output.parent / (output.name + '-build-log'), ['docker', 'build', '-t', tag, str(output)], 600)
    if receipt['exit_code'] != 0 or receipt['timed_out']:
        raise RuntimeError('Agent worker image build failed; inspect retained build logs')
    return subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()


@contextmanager
def execution_environment(task, workspace, evidence, cli, skill=None, authenticate=True,
                          model_profile=None, credentials=DEFAULT_CREDENTIALS):
    """Only the public workspace and optional treatment skill reach a Docker executor."""
    agent = cli.get('agent', 'codex')
    adapter = get_adapter(agent)
    if task['environment']['kind'] == 'local':
        if agent != 'codex':
            raise ValueError('Claude Code currently requires a Docker task')
        yield cli['path'], workspace, 'workspace-write', str(skill / 'SKILL.md') if skill else None
        return
    image = task['environment'].get('worker_image')
    if not image:
        raise ValueError('Prepared Docker task requires an agent worker image')
    name = 'swe-executor-' + uuid.uuid4().hex[:12]
    argv = ['docker', 'run', '-d', '--init', '--name', name, '--cpus', '2', '--memory', '3g',
            '--network', 'bridge', '-v', f'{workspace}:/testbed', '-w', '/testbed',
            '-e', 'SETUPTOOLS_SCM_PRETEND_VERSION=7.2.0.dev0']
    if skill:
        argv += ['-v', f'{skill}:/opt/target-skill:ro']
    if authenticate and agent == 'codex':
        auth = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
        if not auth.is_file():
            raise ValueError('Container execution requires existing Codex auth.json; no credential is copied to evidence')
        argv += ['-v', f'{auth}:/root/.codex/auth.json:ro']
    # The temporary env file is outside artifacts and removed as soon as Docker
    # starts. Capture records only argv, never credential values or Docker inspect.
    with tempfile.TemporaryDirectory(prefix='swe-auth-') as auth_tmp:
        if agent == 'claude-code':
            if model_profile is None:
                raise ValueError('Claude Code requires an explicit model profile')
            env = claude_environment(model_profile, credential(model_profile, credentials)
                                     if authenticate else '')
            env.update({'HOME': '/tmp/agent-home', 'CLAUDE_CONFIG_DIR': '/tmp/agent-home/.claude'})
            env_file = Path(auth_tmp) / 'worker.env'
            if any('\n' in v or '\r' in v for v in env.values()):
                raise ValueError('Worker environment values must be single-line strings')
            env_file.write_text(''.join(f'{key}={value}\n' for key, value in env.items()))
            env_file.chmod(0o600)
            argv += ['--env-file', str(env_file)]
        argv += [image, 'sleep', '86400']
        subprocess.run(argv, check=True, capture_output=True)
    try:
        record = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture(workspace,
            evidence / 'environment-setup', ['docker', 'exec', name, 'uv', 'pip', 'install',
            '--python', '/opt/testenv/bin/python', '--no-deps', '--no-build-isolation', '-e', '/testbed'], 90)
        if record['exit_code'] != 0 or record['timed_out']:
            raise RuntimeError('Worker project installation failed')
        actual = subprocess.check_output(['docker', 'exec', name, adapter.executable, '--version'],
                                         text=True, timeout=20).strip()
        actual_version = re.search(r'\d+\.\d+\.\d+', actual)
        expected_version = re.search(r'\d+\.\d+\.\d+', cli['version'])
        if not actual_version or not expected_version or actual_version.group() != expected_version.group():
            raise ValueError(f'Worker CLI version differs from the frozen runtime: {actual}')
        prefix = ['docker', 'exec', '-i']
        if agent == 'claude-code':
            # Claude disallows bypassPermissions as root; match bind-mount owner.
            uid, gid = os.getuid(), os.getgid()
            if uid == 0:
                raise ValueError('Claude Docker worker requires a non-root workspace owner')
            subprocess.run(['docker', 'exec', name, 'mkdir', '-p', '/tmp/agent-home'], check=True)
            subprocess.run(['docker', 'exec', name, 'chown', '-R', f'{uid}:{gid}', '/tmp/agent-home'], check=True)
            prefix += ['--user', f'{uid}:{gid}']
        write_json(evidence / 'environment.json', {'image': image, 'cli': actual, 'agent': agent,
                   'boundary': 'Docker container; no evaluator materials or Docker socket mounted',
                   'inner_sandbox': 'danger-full-access', 'skill_mounted': bool(skill)})
        # Docker enforces isolation. No elevated caps or host daemon socket are granted.
        yield prefix + [name, adapter.executable], Path('/testbed'), 'danger-full-access', (
            '/opt/target-skill/SKILL.md' if skill else None)
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True)


def resolve_codex():
    binary = shutil.which('codex')
    if not binary:
        raise ValueError('codex is not on this process PATH; use an initialized terminal')
    version = subprocess.check_output([binary, '--version'], text=True, timeout=20).strip()
    return {'path': binary, 'resolved_path': str(Path(binary).resolve()), 'version': version}


def execute(helpers, workspace, evidence, command, timeout, prompt, adapter=None):
    record = load_helper(helpers / 'capture.py').capture(
        workspace, evidence, command, timeout, prompt)
    trace = (adapter or get_adapter('codex')).inspect_trace(
        (evidence / 'stdout.log').read_text(errors='replace'), helpers)
    write_json(evidence / 'trace.json', trace)
    status = ('timeout' if record['timed_out'] else
              'completed' if record['exit_code'] == 0 and not record['launch_error']
              and trace['telemetry_usable'] else 'error')
    return {'run_status': status, 'usage': trace['usage'],
            'elapsed_seconds': record['elapsed_seconds'], 'cost': None,
            'models_observed': trace.get('models_observed', []),
            'isolation_status': trace.get('isolation_status'),
            'capture_files': {p.name: digest(p) for p in evidence.iterdir() if p.is_file()}}


# Compatibility entrypoints for the existing Codex judge and historical tests.
def codex_command(*args, **kwargs):
    from agent_adapters.codex import codex_command as command
    return command(*args, **kwargs)


def isolated_context(*args, **kwargs):
    from agent_adapters.codex import isolated_context as prepare
    return prepare(*args, **kwargs)
