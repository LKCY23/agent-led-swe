#!/usr/bin/env python3
"""Run one bounded baseline/skill pair on the qualified cattrs collaboration task."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from agent_adapters import get_adapter
from cattrs_task import BASE_COMMIT, TASK_ID, run_checks, unpack, verify_inputs
from collaboration_runtime import converse
from evaluation_runtime import (DEFAULT_EVALUATOR, adapter_hashes, build_worker_image, digest,
                                execution_environment, file_hashes, freeze_helpers, snapshot, write_json)
from model_config import CONFIGS, load_profile, validate_compatibility
from native_skills import verify_activation
from run_evaluation import COMMON_PROMPT, freeze_skill, skill_source
from simulated_user import SimulatedUser

SCENARIO = Path(__file__).parent / 'cases/collaboration/cattrs'


def prepare_pair(inputs, qualification, output, agent, solver, user, effort, skill, limits, user_qualification):
    verify_inputs(inputs)
    qualified = json.loads(qualification.read_text())
    if (qualified.get('qualified') is not True or qualified.get('inputs_sha256') != digest(inputs / 'inputs.json')
            or qualified.get('verifier_sha256') != digest(Path(__file__).with_name('cattrs_task.py'))):
        raise ValueError('Matching cattrs environment/verifier qualification is required')
    validate_compatibility(agent, solver, effort)
    validate_compatibility('claude-code', user, 'high')
    user_receipt = json.loads(user_qualification.read_text())
    user_files = {name: digest(Path(__file__).parent / name) for name in
                  ('simulated_user.py', 'evaluation_runtime.py', 'model_config.py', 'agent_adapters/claude_code.py')}
    expected_user_cli = {'agent': 'claude-code', 'version': json.loads((CONFIGS / 'agents.json').read_text())['claude-code']['version']}
    if (user_receipt.get('qualified') is not True or user_receipt.get('model_profile') != user
            or user_receipt.get('persona_sha256') != digest(SCENARIO / 'user.md')
            or user_receipt.get('requirements_sha256') != digest(inputs / 'user-requirements.md')
            or user_receipt.get('tool_files') != user_files or user_receipt.get('cli') != expected_user_cli):
        raise ValueError('Simulated-user qualification is missing, failed or stale; do not run a skill comparison')
    for key, value in limits.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'{key} must be a positive integer')
    if not (skill / 'SKILL.md').is_file():
        raise ValueError('Explicit accepted skill source is required')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(inputs, output / 'task-inputs')
    shutil.copyfile(qualification, output / 'qualification.json')
    shutil.copyfile(user_qualification, output / 'user-qualification.json')
    shutil.copytree(SCENARIO, output / 'scenario')
    targets = freeze_skill(skill, output / 'frozen-skill')
    freeze_helpers(DEFAULT_EVALUATOR, output / 'helpers')
    environment = json.loads((inputs / 'environment.json').read_text())
    cli = {'agent': agent, 'version': json.loads((CONFIGS / 'agents.json').read_text())[agent]['version']}
    environment['worker_image'] = build_worker_image(environment, cli['version'], output / 'worker-build', agent)
    user_cli = expected_user_cli
    user_environment = dict(environment)
    if agent != 'claude-code':
        user_environment['worker_image'] = build_worker_image(environment, user_cli['version'], output / 'user-worker-build', 'claude-code')
    plan = {'task': TASK_ID, 'adapted': True, 'base_commit': BASE_COMMIT, 'split': 'development',
            'variants': ['baseline', 'skill'], 'repetitions': 1, 'automatic_retries': 0,
            'agent': cli, 'solver_profile': solver, 'user_profile': user, 'effort': effort, 'user_effort': 'high',
            'user_agent': user_cli, 'user_environment': user_environment,
            'limits': limits, 'cost_limit': None,
            'budget_semantics': 'Wall time and turn/model-call counts; no hard dollar/token cap for solver',
            'environment': environment, 'qualification_sha256': digest(qualification),
            'user_qualification_sha256': digest(user_qualification),
            'input_sha256': digest(inputs / 'inputs.json'), 'scenario_files': file_hashes(output / 'scenario'),
            'skill_source': skill_source(skill), 'skill_files': targets, 'tool_files': adapter_hashes(),
            'instruction': 'Native skill invocation only in treatment; no stage scheduling or automatic LLM grading'}
    write_json(output / 'plan.json', plan)
    for variant in plan['variants']:
        (output / variant).mkdir()
        write_json(output / variant / 'result.json', {'status': 'not_started'})
    return plan


def run_pair(output, plan, credentials):
    adapter = get_adapter(plan['agent']['agent'])
    inputs = output / 'task-inputs'
    # Frozen source and validator files are outside every solver workspace.
    verify_inputs(inputs)
    request = (output / 'scenario/request.md').read_text()
    persona = (output / 'scenario/user.md').read_text()
    requirements = (inputs / 'user-requirements.md').read_text()
    limits = plan['limits']
    results = []
    for variant in plan['variants']:
        evidence = output / variant
        treatment = output / 'frozen-skill' if variant == 'skill' else None
        result = {'status': 'error', 'accepted': False, 'task_status': 'unknown'}
        with tempfile.TemporaryDirectory(prefix='cattrs-collaboration-') as tmp:
            work = Path(tmp) / 'workspace'
            unpack(inputs / 'public.tar.gz', work)
            # A local history permits normal diff/commit work without shipping
            # the upstream Git history (which could reveal later solutions).
            subprocess.run(['git', 'init', '-q', str(work)], check=True)
            subprocess.run(['git', '-C', str(work), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(work), '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                '-c', 'user.name=Evaluation', '-c',
                'user.email=evaluation@local.invalid', 'commit', '-qm', 'Frozen task input'], check=True)
            snapshot(work, evidence / 'before')
            user = SimulatedUser(plan['user_profile'], persona, requirements, evidence / 'before',
                evidence / 'user', plan['user_environment'], plan['user_agent'], credentials,
                max_replies=limits['turns'], max_turns=limits['user_max_turns'], effort=plan['user_effort'])
            try:
                with user, execution_environment({'environment': plan['environment']}, work, evidence, plan['agent'], treatment,
                        model_profile=plan['solver_profile'], credentials=credentials) as runtime:
                    binary, cwd, sandbox, entrypoint = runtime
                    context = adapter.prepare_context(binary, cwd, evidence, plan['solver_profile']['model'],
                        plan['effort'], sandbox, entrypoint)
                    result = converse(adapter, binary, cwd, sandbox, context, plan['solver_profile']['model'],
                        plan['effort'], output / 'helpers', work, evidence / 'conversation',
                        COMMON_PROMPT + 'You can ask the user questions in your reply; this conversation can continue.\n\n' + request,
                        user, invocation=adapter.invocation() if treatment else '', max_turns=limits['turns'],
                        timeout=limits['total_seconds'], turn_timeout=limits['turn_seconds'],
                        user_timeout=limits['user_seconds'])
                activation = verify_activation(adapter.name, evidence, treatment, entrypoint,
                                               'conversation/turn-001/capture')
                result['native_activation'] = activation
                result['comparison_validity'] = 'valid' if activation['status'] == 'verified' else 'invalid'
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                result.update(status='error', error=str(exc), comparison_validity='invalid')
            finally:
                snapshot(work, evidence / 'after')
                result['user_replies'] = user.calls
                write_json(evidence / 'result.json', result)
        # Only complete, valid submissions can receive task success. Incomplete
        # artifacts remain available for later diagnosis, without hidden feedback.
        if result['status'] == 'completed' and result.get('comparison_validity') == 'valid':
            checks = run_checks(inputs, evidence / 'after', evidence / 'verifier')
            reference = json.loads((output / 'qualification.json').read_text())['runs'][1]['checks']
            if checks['status'] == 'pass' and [g['outcome_sha256'] for g in checks['groups']] != [
                    g['outcome_sha256'] for g in reference['groups']]:
                checks['status'] = 'unknown'
                checks['reason'] = 'Test identities/outcomes differ from the qualified reference'
            result['task_status'] = checks['status']
            write_json(evidence / 'verifier-result.json', checks)
            write_json(evidence / 'result.json', result)
        print(json.dumps({'variant': variant, 'status': result['status'],
                          'task_status': result['task_status'], 'user_replies': user.calls}), flush=True)
        results.append(result)
        write_json(output / 'results.json', results)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--user-qualification', type=Path, required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--agent', choices=['codex', 'claude-code'], required=True)
    parser.add_argument('--solver-profile', type=Path, required=True)
    parser.add_argument('--user-profile', type=Path, required=True)
    parser.add_argument('--effort', choices=['low', 'high', 'max', 'xhigh'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    for name in ('total-seconds', 'turn-seconds', 'user-seconds', 'turns', 'user-max-turns'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--prepare-only', action='store_true', help='Freeze the plan without any model call')
    args = parser.parse_args()
    limits = {name: getattr(args, name) for name in ('total_seconds', 'turn_seconds', 'user_seconds', 'turns', 'user_max_turns')}
    plan = prepare_pair(args.inputs.resolve(), args.qualification.resolve(), args.output.resolve(), args.agent,
        load_profile(args.solver_profile), load_profile(args.user_profile), args.effort, args.skill_path.resolve(), limits,
        args.user_qualification.resolve())
    if not args.prepare_only:
        results = run_pair(args.output.resolve(), plan, args.credentials.resolve())
        return 0 if all(r['status'] == 'completed' and r['task_status'] == 'pass' for r in results) else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
