#!/usr/bin/env python3
"""No-model checks of both CLI workers against a qualified real task workspace."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from agent_adapters import get_adapter
from evaluation_runtime import build_worker_image, execution_environment, write_json
from model_config import CONFIGS, load_profile
from run_evaluation import freeze_skill
from suite_tasks import NAMES
from task_adapters import load_task, prepare_task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=NAMES)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    task = prepare_task(load_task(args.name, args.inputs), output / 'task')
    versions = json.loads((CONFIGS / 'agents.json').read_text())
    skill = output / 'frozen-skill'
    freeze_skill(args.skill_path.resolve(), skill)
    reports = []
    for name in ('codex', 'claude-code'):
        evidence = output / name
        evidence.mkdir()
        adapter = get_adapter(name)
        version = versions[name]['version']
        image = build_worker_image(task['environment'], version, evidence / 'build', name)
        task['environment']['worker_image'] = image
        profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json') if name == 'claude-code' else None
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp).resolve()
            shutil.copytree(output / task['workspace'], work, dirs_exist_ok=True, symlinks=True)
            with execution_environment(task, work, evidence, {'agent': name, 'version': version},
                    skill, authenticate=False, model_profile=profile) as runtime:
                binary, cwd, sandbox, installed = runtime
                container = binary[binary.index(adapter.executable) - 1]
                actual_skill = subprocess.check_output(['docker', 'exec', container, 'cat', installed], text=True)
                assert actual_skill == (skill / 'SKILL.md').read_text()
                if name == 'codex':
                    adapter.prepare_context(binary, cwd, evidence, 'gpt-6.1-sol', 'high', sandbox, installed)
                # Run as the same user as the Agent and verify copy-mode export.
                prefix = ['docker', 'exec', *(['--user', f'{os.getuid()}:{os.getgid()}'] if name == 'claude-code' else []), container]
                subprocess.run([*prefix, 'python3', '-c',
                    'from pathlib import Path; Path(".worker-check.txt").write_text("captured\\n")'], check=True)
                tool = ('node' if args.name == 'nodebb' else 'go' if args.name == 'navidrome' else 'python')
                command = [tool, 'version'] if tool == 'go' else [tool, '--version']
                actual = subprocess.check_output([*prefix, *command], text=True).strip()
                expected = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none',
                    *(['--platform', task['environment']['platform']] if task['environment'].get('platform') else []),
                    task['environment']['image'], *command], text=True).strip()
                assert actual == expected, (actual, expected)
                probe = (['node', '-e', 'require("mocha")'] if args.name == 'nodebb' else
                         ['go', 'test', '-tags', 'netgo', '-run', '^$', './conf'] if args.name == 'navidrome' else
                         ['python', '-m', 'pytest', '--version'])
                check = subprocess.run([*prefix, *probe], capture_output=True, text=True, timeout=240)
                write_json(evidence / 'task-tool-check.json', {'argv': probe, 'exit_code': check.returncode,
                                                              'stdout': check.stdout, 'stderr': check.stderr})
                if check.returncode:
                    raise RuntimeError('Task tooling failed under the Agent user; inspect task-tool-check.json')
            assert (work / '.worker-check.txt').read_text() == 'captured\n'
        reports.append({'agent': name, 'image': image, 'cli_version': version,
                        'task_runtime_unchanged': actual, 'artifact_capture': 'passed',
                        'skill_installation': 'verified', 'model_calls': 0})
        write_json(output / 'report.json', reports)
        print(reports[-1], flush=True)


if __name__ == '__main__':
    main()
