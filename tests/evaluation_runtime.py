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
import tarfile

from agent_adapters import get_adapter
from model_config import credential, claude_environment, DEFAULT_CREDENTIALS
from worker_control import WorkerCommand, execution_deadline


DEFAULT_EVALUATOR = Path.home() / '.codex/skills/skill-evaluator'
RUNTIME_CONFIG = Path(__file__).parent / 'configs/runtime.json'


def adapter_hashes():
    root = Path(__file__).parent
    names = [
        'evaluation_runtime.py', 'run_evaluation.py', 'evaluate_results.py', 'run_smoke.py',
        'task_adapters.py', 'functional_checks.py', 'model_config.py', 'native_skills.py', 'packaging_environment.py', 'worker_network.py', 'model_gateway.py', 'suite_tasks.py', 'swe_pro_verifier.py', 'container_workspace.py',
        'grpc_task.py', 'grpc_live_probe.py', 'cattrs_task.py', 'cattrs_repair_task.py', 'ofetch_task.py', 'tomlkit_task.py', 'collaboration_runtime.py', 'check_collaboration_worker.py',
        'simulated_user.py', 'run_collaboration.py', 'check_simulated_user.py',
        'worker_control.py', 'configs/runtime.json']
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


def snapshot(source, destination, exclude=()):
    """Preserve project files; omit Git internals and declared environment dependencies."""
    root = Path(source).resolve()
    excluded = {'.git', *exclude}
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in excluded):
        raise ValueError('Unsafe snapshot exclusion')
    def ignore(folder, names):
        relative = Path(folder).relative_to(root)
        return [name for name in names if name == '.git' or str(relative / name) in excluded]
    shutil.copytree(root, destination, symlinks=True, ignore=ignore)
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
    base = environment.get('execution_image', environment['image'])
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', base):
        raise ValueError('Worker base image must be identified by immutable Docker image ID')
    base_tag = 'agent-led-swe-base:' + base[7:]
    if agent == 'codex':
        launcher = ("RUN printf '#!/bin/sh\\nexec /opt/agent-runtime/node /opt/agent-runtime/node_modules/"
                    + adapter.cli_entrypoint + " \"$@\"\\n' > /usr/local/bin/codex && chmod +x /usr/local/bin/codex\n")
    else:
        launcher = f'RUN ln -s /opt/agent-runtime/node_modules/{adapter.cli_entrypoint} /usr/local/bin/{adapter.executable}\n'
    (output / 'Dockerfile').write_text(
        'FROM ' + json.loads(RUNTIME_CONFIG.read_text())['node_image'] + ' AS cli\n'
        f'RUN npm install -g {adapter.npm_package}@{version}\n'
        f'FROM {base_tag}\n'
        'COPY --from=cli /usr/local/bin/node /opt/agent-runtime/node\n'
        f'COPY --from=cli /usr/local/lib/node_modules/{adapter.npm_package.split("/")[0]} '
        f'/opt/agent-runtime/node_modules/{adapter.npm_package.split("/")[0]}\n'
        + launcher +
        'RUN command -v git >/dev/null || (apt-get update && apt-get install -y --no-install-recommends git '
        '&& rm -rf /var/lib/apt/lists/*)\n')
    tag = 'agent-led-swe-worker:' + agent + '-' + version + '-' + digest(output / 'Dockerfile')[:16]
    cached = subprocess.run(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'],
                            capture_output=True, text=True)
    if cached.returncode == 0:
        return cached.stdout.strip()
    subprocess.run(['docker', 'tag', base, base_tag], check=True)
    receipt = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture(
        output, output.parent / (output.name + '-build-log'), ['docker', 'build', *(['--platform', environment['platform']] if environment.get('platform') else []), '-t', tag, str(output)], 600)
    if receipt['exit_code'] != 0 or receipt['timed_out']:
        raise RuntimeError('Agent worker image build failed; inspect retained build logs')
    return subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()


@contextmanager
def execution_environment(task, workspace, evidence, cli, skill=None, authenticate=True,
                          model_profile=None, credentials=DEFAULT_CREDENTIALS, model_upstream=None):
    """Only the public workspace and optional treatment skill reach a Docker executor."""
    agent = cli.get('agent', 'codex')
    adapter = get_adapter(agent)
    if task['environment']['kind'] == 'local':
        if agent != 'codex':
            raise ValueError('Claude Code currently requires a Docker task')
        with tempfile.TemporaryDirectory(prefix='swe-codex-home-') as tmp:
            home = Path(tmp).resolve()
            codex_home = home / '.codex'
            codex_home.mkdir()
            auth = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
            if authenticate and auth.is_file():
                shutil.copyfile(auth, codex_home / 'auth.json')
                (codex_home / 'auth.json').chmod(0o600)
            installed = home / '.agents/skills/agent-led-swe'
            if skill:
                installed.parent.mkdir(parents=True)
                shutil.copytree(skill, installed, ignore=shutil.ignore_patterns('.claude-plugin'))
            binary = ['env', f'HOME={home}', f'CODEX_HOME={codex_home}', cli['path']]
            write_json(evidence / 'skill-installation.json', {'mode': 'native', 'agent': agent,
                       'installed': bool(skill), 'entrypoint': str(installed / 'SKILL.md') if skill else None,
                       'files': file_hashes(installed) if skill else {}})
            try:
                yield binary, workspace, 'workspace-write', str(installed / 'SKILL.md') if skill else None
            finally:
                if (codex_home / 'sessions').exists():
                    shutil.copytree(codex_home / 'sessions', evidence / 'native-codex-session')
        return
    image = task['environment'].get('worker_image')
    if not image:
        raise ValueError('Prepared Docker task requires an agent worker image')
    from worker_network import model_network
    if model_upstream and authenticate:
        raise ValueError('Upstream override is only for unauthenticated protocol checks')
    headers = None
    if agent == 'claude-code':
        if model_profile is None:
            raise ValueError('Claude Code requires an explicit model profile')
        upstream = model_profile['base_url']
        if authenticate:
            headers = {'x-api-key': credential(model_profile, credentials)}
    else:
        auth_path = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
        auth_data = json.loads(auth_path.read_text()) if authenticate and auth_path.exists() else {}
        upstream = ('https://api.openai.com/v1' if auth_data.get('OPENAI_API_KEY')
                    else 'https://chatgpt.com/backend-api/codex')
        if authenticate:
            token = auth_data.get('OPENAI_API_KEY') or auth_data.get('tokens', {}).get('access_token')
            if not token:
                raise ValueError('Existing Codex authentication is required')
            headers = {'Authorization': 'Bearer ' + token}
            if not auth_data.get('OPENAI_API_KEY'):
                account = auth_data.get('tokens', {}).get('account_id')
                if not account:
                    raise ValueError('Codex ChatGPT authentication has no account ID')
                headers['chatgpt-account-id'] = account
    with model_network(image, agent, model_upstream or upstream, evidence, headers) as (network, gateway):
        with docker_worker(task, workspace, evidence, cli, skill, authenticate,
                           model_profile, credentials, network, gateway) as runtime:
            yield runtime


@contextmanager
def docker_worker(task, workspace, evidence, cli, skill, authenticate,
                  model_profile, credentials, network, gateway):
    agent = cli.get('agent', 'codex')
    adapter = get_adapter(agent)
    image = task['environment']['worker_image']
    environment = task['environment']
    workdir = environment.get('workdir', '/testbed')
    copy_mode = environment.get('workspace_mode') == 'copy'
    readonly = environment.get('readonly_workspace', False)
    resources = environment.get('resources', json.loads(RUNTIME_CONFIG.read_text())['worker'])
    if readonly and (copy_mode or environment.get('install_argv') != []):
        raise ValueError('Read-only workers require a bind mount and no project installation')
    from container_workspace import install_workspace, export_workspace, allow_workspace_owner
    name = 'swe-executor-' + uuid.uuid4().hex[:12]
    argv = ['docker', 'run', '-d', '--init', '--name', name,
            '--cpus', str(resources['cpus']), '--memory', resources['memory'],
            '--network', network, '--cap-drop=ALL', '--cap-add=CHOWN', '--security-opt=no-new-privileges',
            *(['--platform', environment['platform']] if environment.get('platform') else []),
            *([] if copy_mode else ['-v', f'{workspace}:{workdir}' + (':ro' if readonly else '')]), '-w', workdir]
    installed = ('/root/.agents/skills/agent-led-swe' if agent == 'codex'
                 else '/tmp/agent-home/.claude/skills/agent-led-swe')
    if skill:
        # Install the skill payload, not its separate plugin packaging metadata.
        payload = evidence / 'installed-skill'
        shutil.copytree(skill, payload, ignore=shutil.ignore_patterns('.claude-plugin'))
        argv += ['-v', f'{payload}:{installed}:ro']
    # The temporary env file is outside artifacts and removed as soon as Docker
    # starts. Capture records only argv, never credential values or Docker inspect.
    with tempfile.TemporaryDirectory(prefix='swe-auth-') as auth_tmp:
        if agent == 'claude-code':
            if model_profile is None:
                raise ValueError('Claude Code requires an explicit model profile')
            # The real credential is mounted only into the external gateway.
            env = claude_environment(model_profile, 'evaluation-gateway')
            env['ANTHROPIC_BASE_URL'] = gateway
            env.update({'HOME': '/tmp/agent-home', 'CLAUDE_CONFIG_DIR': '/tmp/agent-home/.claude'})
            env_file = Path(auth_tmp) / 'worker.env'
            if any('\n' in v or '\r' in v for v in env.values()):
                raise ValueError('Worker environment values must be single-line strings')
            env_file.write_text(''.join(f'{key}={value}\n' for key, value in env.items()))
            env_file.chmod(0o600)
            argv += ['--env-file', str(env_file)]
        argv += [image, 'sleep', 'infinity']
        subprocess.run(argv, check=True, capture_output=True)
    try:
        if copy_mode:
            install_workspace(name, workspace, workdir)
        for relative in environment.get('executor_discard_files', []):
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('Unsafe executor discard path')
            subprocess.run(['docker', 'exec', name, 'rm', '-f', '--', workdir + '/' + relative],
                           check=True, capture_output=True)
        install_argv = environment.get('install_argv', ['uv', 'pip', 'install',
            '--python', '/opt/testenv/bin/python', '--offline', '--no-deps', '--no-build-isolation', '-e', workdir])
        if install_argv:
            record = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture(workspace,
                evidence / 'environment-setup', ['docker', 'exec', name, *install_argv], 90)
            if record['exit_code'] != 0 or record['timed_out']:
                raise RuntimeError('Worker project installation failed')
        if task['environment'].get('audit_packaging_sources'):
            from packaging_environment import audit_container, clean
            audit = audit_container(name)
            write_json(evidence / 'environment-source-audit-before.json', audit)
            if not clean(audit) or not audit['task_import'].startswith('/testbed/'):
                raise RuntimeError('Packaging executor still exposes an alternative implementation or imports the wrong task')
        from worker_network import audit_network
        audit_network(name, evidence)
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
            subprocess.run(['docker', 'exec', name, 'mkdir', '-p', '/tmp/agent-home/.claude'], check=True)
            # The version probe can create root-owned caches before dropping uid.
            # Own the disposable HOME, but leave the read-only skill mount alone.
            allow_workspace_owner(name, '/tmp/agent-home', uid, gid, ['.claude/skills'])
            if copy_mode:
                allow_workspace_owner(name, workdir, uid, gid, environment.get('workspace_excludes', []))
            prefix += ['--user', f'{uid}:{gid}']
        write_json(evidence / 'environment.json', {'image': image, 'cli': actual, 'agent': agent,
                   'boundary': 'Docker container; no evaluator materials or Docker socket mounted',
                   'inner_sandbox': 'danger-full-access', 'skill_mounted': bool(skill),
                   'readonly_workspace': readonly,
                   'resources': resources,
                   'network': 'internal-model-gateway', 'model_gateway': gateway})
        write_json(evidence / 'skill-installation.json', {
            'mode': 'native', 'agent': agent, 'installed': bool(skill),
            'entrypoint': installed + '/SKILL.md' if skill else None,
            'files': file_hashes(payload) if skill else {}})
        # Docker enforces isolation. No elevated caps or host daemon socket are granted.
        if agent == 'codex':
            prefix += ['-e', 'CODEX_GATEWAY_KEY=evaluation-gateway']
        binary = prefix + [name, adapter.executable]
        if agent == 'codex':
            binary += ['-c', 'chatgpt_base_url=' + json.dumps(gateway),
                       '-c', 'model_provider="evaluation-gateway"', '-c',
                       'model_providers.evaluation-gateway={name="Evaluation gateway",base_url='
                       + json.dumps(gateway) + ',wire_api="responses",requires_openai_auth=false,env_key="CODEX_GATEWAY_KEY",'
                       'supports_websockets=false}']
        binary = WorkerCommand(binary, name, network, evidence)
        yield binary, Path(workdir), 'danger-full-access', (
            installed + '/SKILL.md' if skill else None)
        if task['environment'].get('audit_packaging_sources'):
            audit = audit_container(name, import_task=False)
            write_json(evidence / 'environment-source-audit-after.json', audit)
    finally:
        try:
            # Stop every container process before copying any final artifact.
            WorkerCommand([], name, network, evidence).stop()
            state = json.loads((evidence / 'worker-stop.json').read_text())
            actual_resources = json.loads(subprocess.check_output(['docker', 'inspect', '--format',
                '{{json .HostConfig}}', name], text=True, timeout=30))
            write_json(evidence / 'resource-result.json', {'limits': resources,
                'oom_killed': state.get('OOMKilled'), 'exit_code': state.get('ExitCode'),
                'memory_limit_bytes': actual_resources['Memory'],
                'nano_cpus': actual_resources['NanoCpus']})
            if copy_mode:
                export_workspace(name, workdir, workspace, environment.get('workspace_excludes', []))
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
            write_json(evidence / 'workspace-export-error.json', {'error': str(exc)})
            raise RuntimeError('Worker artifact export failed; see workspace-export-error.json') from exc
        finally:
            if agent == 'codex':
                subprocess.run(['docker', 'cp', f'{name}:/root/.codex/sessions',
                                str(evidence / 'native-codex-session')], capture_output=True)
            else:
                exported = subprocess.run(['docker', 'cp', f'{name}:/tmp/agent-home/.claude/projects',
                    str(evidence / 'native-claude-projects')], capture_output=True, text=True, timeout=30)
                write_json(evidence / 'native-session-export.json', {'exit_code': exported.returncode,
                    'stderr': exported.stderr})
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True)


def resolve_codex():
    binary = shutil.which('codex')
    if not binary:
        raise ValueError('codex is not on this process PATH; use an initialized terminal')
    version = subprocess.check_output([binary, '--version'], text=True, timeout=20).strip()
    return {'path': binary, 'resolved_path': str(Path(binary).resolve()), 'version': version}


def execute(helpers, workspace, evidence, command, timeout, prompt, adapter=None):
    adapter = adapter or get_adapter('codex')
    stdin = prompt
    if adapter.name == 'claude-code':
        stdin = prompt.with_suffix('.jsonl')
        stdin.write_text(json.dumps({'type': 'user', 'message': {'role': 'user',
                          'content': prompt.read_text()}}, ensure_ascii=False) + '\n')
    record = load_helper(helpers / 'capture.py').capture(
        workspace, evidence, command, timeout, stdin)
    trace = adapter.inspect_trace(
        (evidence / 'stdout.log').read_text(errors='replace'), helpers)
    write_json(evidence / 'trace.json', trace)
    status = ('timeout' if record['timed_out'] else
              'completed' if record['exit_code'] == 0 and not record['launch_error']
              and trace['telemetry_usable'] else 'error')
    return {'run_status': status, 'usage': trace['usage'],
            'usage_scope': trace.get('usage_scope', 'native_turn'),
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
