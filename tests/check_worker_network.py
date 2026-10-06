#!/usr/bin/env python3
"""Bounded real-model connectivity/native-skill check, not a benchmark trial.

One request session per selected CLI, 90 seconds, no automatic retry. Protocol
and network-denial checks should pass before spending model calls here.
"""
import argparse
import json
from pathlib import Path
import tempfile
import uuid

from agent_adapters import get_adapter
from evaluation_runtime import (DEFAULT_EVALUATOR, execute, execution_environment,
                                file_hashes, freeze_helpers, write_json)
from model_config import CONFIGS, load_profile
from native_skills import verify_activation
from run_evaluation import freeze_skill


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['codex', 'claude-code'], required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads((CONFIGS / 'agents.json').read_text())
    profile = load_profile(CONFIGS / 'models' / (
        'codex-gpt-6.1-sol.json' if args.agent == 'codex' else 'deepseek-v4.1-flash.json'))
    cli = {'agent': args.agent, 'version': config[args.agent]['version']}
    adapter = get_adapter(args.agent)
    freeze_helpers(DEFAULT_EVALUATOR, output / 'helpers')
    skill = output / 'frozen-skill'
    freeze_skill(args.skill_path.resolve(), skill)
    task = {'environment': {'kind': 'docker', 'worker_image': args.image}}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()
        (work / 'pyproject.toml').write_text('[build-system]\nrequires=["flit_core"]\n'
            'build-backend="flit_core.buildapi"\n[project]\nname="probe"\nversion="0.0.0"\n'
            'description="Connectivity probe"\n')
        (work / 'probe.py').write_text('')
        marker = 'NETWORK_MODEL_OK_' + uuid.uuid4().hex
        (work / 'marker.txt').write_text(marker + '\n')
        before = file_hashes(work)
        prompt = output / 'prompt.txt'
        prompt.write_text(adapter.invocation() +
            'This is a connectivity check, not a development task. Read marker.txt and reply with '
            'its content. Do not modify files or make any other tool calls.')
        with execution_environment(task, work, output, cli, skill,
                model_profile=profile, credentials=args.credentials) as runtime:
            binary, cwd, sandbox, path = runtime
            context = adapter.prepare_context(binary, cwd, output, profile['model'], 'high', sandbox, path)
            result = execute(output / 'helpers', work, output / 'capture',
                adapter.command(binary, cwd, profile['model'], 'high', sandbox, context),
                90, prompt, adapter)
        activation = verify_activation(args.agent, output, skill, path)
        final = None
        for line in (output / 'capture/stdout.log').read_text().splitlines():
            event = json.loads(line)
            if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                final = event['item'].get('text')
            if event.get('type') == 'result':
                final = event.get('result')
        result.update(activation=activation, workspace_unchanged=before == file_hashes(work),
                      final_matches_marker=isinstance(final, str) and final.strip() == marker,
                      scope='One real-model native-skill connectivity session; no benchmark')
        write_json(output / 'result.json', result)
        if (result['run_status'] != 'completed' or activation['status'] != 'verified'
                or not result['workspace_unchanged'] or not result['final_matches_marker']):
            raise RuntimeError('Connectivity check incomplete; inspect retained evidence')
        print(json.dumps({'agent': args.agent, 'status': result['run_status'],
                          'native_skill': activation['status']}))


if __name__ == '__main__':
    main()
