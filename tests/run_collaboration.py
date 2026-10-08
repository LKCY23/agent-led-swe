#!/usr/bin/env python3
"""Run one bounded baseline/skill or current/candidate collaboration pair."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from agent_adapters import get_adapter
import cattrs_task
from cattrs_task import unpack
from collaboration_runtime import converse
from evaluation_runtime import (DEFAULT_EVALUATOR, adapter_hashes, build_worker_image, digest,
                                execution_environment, file_hashes, freeze_helpers, snapshot, write_json)
from model_config import CONFIGS, load_profile, validate_compatibility, allow_subagents
from native_skills import verify_activation
from run_evaluation import COMMON_PROMPT, freeze_skill, skill_source
from simulated_user import SimulatedUser


def task_adapter(name):
    if name == 'cattrs':
        return cattrs_task
    if name == 'ofetch':
        import ofetch_task
        return ofetch_task
    if name == 'tomlkit':
        import tomlkit_task
        return tomlkit_task
    if name == 'cattrs-repair':
        import cattrs_repair_task
        return cattrs_repair_task
    raise ValueError(f'Unknown collaboration task: {name}')


def prepare_pair(inputs, qualification, output, agent, solver, user, effort, skill, limits,
                 user_qualification=None, reference_skill=None, task_name='cattrs'):
    task = task_adapter(task_name)
    task.verify_inputs(inputs)
    qualified = json.loads(qualification.read_text())
    if (qualified.get('qualified') is not True or qualified.get('inputs_sha256') != digest(inputs / 'inputs.json')
            or qualified.get('verifier_sha256') != digest(Path(task.__file__))):
        raise ValueError('Matching task environment/verifier qualification is required')
    validate_compatibility(agent, solver, effort)
    validate_compatibility('claude-code', user, 'high')
    expected_user_cli = {'agent': 'claude-code', 'version': json.loads((CONFIGS / 'agents.json').read_text())['claude-code']['version']}
    # Prior live probes are supporting evidence, not a mandatory certificate.
    # Freeze the actual configuration below and inspect this run's native trace.
    if set(limits) != {'total_seconds'}:
        raise ValueError('The conversation has one budget: total_seconds')
    for key, value in limits.items():
        if type(value) is not int or value < 1:
            raise ValueError(f'{key} must be a positive integer')
    for source in (skill, reference_skill):
        if source is not None and not (source / 'SKILL.md').is_file():
            raise ValueError('Explicit skill sources must contain SKILL.md')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(inputs, output / 'task-inputs')
    shutil.copyfile(qualification, output / 'qualification.json')
    if user_qualification:
        shutil.copyfile(user_qualification, output / 'user-qualification.json')
    shutil.copytree(Path(__file__).parent / 'cases/collaboration' / task_name, output / 'scenario')
    targets = freeze_skill(skill, output / 'frozen-skill')
    reference_files = freeze_skill(reference_skill, output / 'reference-skill') if reference_skill else None
    variants = (['current', 'candidate'] if reference_skill else ['baseline', 'skill'])
    variant_skills = ({'current': 'reference-skill', 'candidate': 'frozen-skill'} if reference_skill
                      else {'baseline': None, 'skill': 'frozen-skill'})
    freeze_helpers(DEFAULT_EVALUATOR, output / 'helpers')
    environment = json.loads((inputs / 'environment.json').read_text())
    environment.setdefault('resources', json.loads((CONFIGS / 'runtime.json').read_text())['worker'])
    cli = {'agent': agent, 'version': json.loads((CONFIGS / 'agents.json').read_text())[agent]['version']}
    environment['worker_image'] = build_worker_image(environment, cli['version'], output / 'worker-build', agent)
    user_cli = expected_user_cli
    user_environment = dict(environment)
    if agent != 'claude-code':
        user_environment['worker_image'] = build_worker_image(environment, user_cli['version'], output / 'user-worker-build', 'claude-code')
    plan = {'task': task.TASK_ID, 'task_adapter': task_name, 'adapted': True, 'base_commit': task.BASE_COMMIT, 'split': 'development',
            'variants': variants, 'variant_skills': variant_skills, 'repetitions': 1, 'automatic_retries': 0,
            'agent': cli, 'solver_profile': solver, 'user_profile': user, 'effort': effort, 'user_effort': 'high',
            'user_agent': user_cli, 'user_environment': user_environment,
            'limits': limits, 'cost_limit': None,
            'allow_subagents': allow_subagents(),
            'budget_semantics': 'One shared solver/user conversation deadline; no per-turn, reply-count, output-token or dollar cap imposed by the runner',
            'environment': environment, 'qualification_sha256': digest(qualification),
            'user_qualification_sha256': digest(user_qualification) if user_qualification else None,
            'input_sha256': digest(inputs / 'inputs.json'), 'scenario_files': file_hashes(output / 'scenario'),
            'skill_source': skill_source(skill), 'skill_files': targets, 'tool_files': adapter_hashes(),
            'reference_skill_source': skill_source(reference_skill) if reference_skill else None,
            'reference_skill_files': reference_files,
            'instruction': 'Native skill invocation only in treatment; no stage scheduling or automatic LLM grading'}
    write_json(output / 'plan.json', plan)
    for variant in plan['variants']:
        (output / variant).mkdir()
        write_json(output / variant / 'result.json', {'status': 'not_started'})
    return plan


def conversation_budget_notice(seconds):
    return (f'The developer and user share {seconds} seconds total for this entire conversation, '
            'including implementation, tool calls, review, checks and documentation. '
            'This is not a fresh budget per turn.\n\n')


def run_pair(output, plan, credentials):
    adapter = get_adapter(plan['agent']['agent'])
    task = task_adapter(plan.get('task_adapter', 'cattrs'))
    inputs = output / 'task-inputs'
    # Frozen source and validator files are outside every solver workspace.
    task.verify_inputs(inputs)
    request = (output / 'scenario/request.md').read_text()
    persona = (output / 'scenario/user.md').read_text()
    requirements = (inputs / 'user-requirements.md').read_text()
    limits = plan['limits']
    budget = conversation_budget_notice(limits['total_seconds'])
    single_agent = not plan.get('allow_subagents', False)
    workspace_excludes = plan['environment'].get('workspace_excludes', [])
    delegation_prompt = ('For this controlled comparison, perform all development in this agent. '
        'Do not delegate, invoke forked skills, or launch additional agent/model processes. '
        'The separate user remains available for questions and review.\n\n') if single_agent else ''
    results = []
    for variant in plan['variants']:
        evidence = output / variant
        skill_directory = plan.get('variant_skills', {'baseline': None, 'skill': 'frozen-skill'})[variant]
        treatment = output / skill_directory if skill_directory else None
        result = {'status': 'error', 'accepted': False, 'task_status': 'unknown'}
        with tempfile.TemporaryDirectory(prefix='swe-collaboration-') as tmp:
            work = Path(tmp) / 'workspace'
            unpack(inputs / 'public.tar.gz', work)
            # A local history permits normal diff/commit work without shipping
            # the upstream Git history (which could reveal later solutions).
            subprocess.run(['git', 'init', '-q', str(work)], check=True)
            subprocess.run(['git', '-C', str(work), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(work), '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                '-c', 'user.name=Evaluation', '-c',
                'user.email=evaluation@local.invalid', 'commit', '-qm', 'Frozen task input'], check=True)
            snapshot(work, evidence / 'before', exclude=workspace_excludes)
            user = SimulatedUser(plan['user_profile'], budget + persona, requirements, evidence / 'before',
                evidence / 'user', plan['user_environment'], plan['user_agent'], credentials,
                effort=plan['user_effort'])
            try:
                with user, execution_environment({'environment': plan['environment']}, work, evidence, plan['agent'], treatment,
                        model_profile=plan['solver_profile'], credentials=credentials) as runtime:
                    binary, cwd, sandbox, entrypoint = runtime
                    context = adapter.prepare_context(binary, cwd, evidence, plan['solver_profile']['model'],
                        plan['effort'], sandbox, entrypoint)
                    context['allow_subagents'] = not single_agent
                    result = converse(adapter, binary, cwd, sandbox, context, plan['solver_profile']['model'],
                        plan['effort'], output / 'helpers', work, evidence / 'conversation',
                        COMMON_PROMPT + budget + delegation_prompt + 'You can ask the user questions in your reply; this conversation can continue.\n\n' + request,
                        user, invocation=adapter.invocation() if treatment else '',
                        timeout=limits['total_seconds'], workspace_excludes=workspace_excludes)
                activation = verify_activation(adapter.name, evidence, treatment, entrypoint,
                                               'conversation/turn-001/capture')
                result['native_activation'] = activation
                result['comparison_validity'] = ('valid' if activation['status'] == 'verified'
                    and result['status'] != 'error' else 'invalid')
                if single_agent and adapter.name == 'claude-code':
                    from agent_adapters.claude_code import DELEGATION_TOOLS
                    traces = [json.loads(p.read_text()) for p in evidence.glob('conversation/turn-*/capture/trace.json')]
                    children = list((evidence / 'native-claude-projects').glob('**/subagents/*.jsonl'))
                    verified = bool(traces) and not children and all(
                        not t.get('subagent_event_lines') and not any(DELEGATION_TOOLS.intersection(i.get('tools', []))
                                                                   for i in t.get('native_init_events', [])) for t in traces)
                    result['single_agent_verified'] = verified
                    if not verified:
                        result['comparison_validity'] = 'invalid'
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                result.update(status='error', error=str(exc), comparison_validity='invalid')
            finally:
                snapshot(work, evidence / 'after', exclude=workspace_excludes)
                result['user_replies'] = user.calls
                write_json(evidence / 'result.json', result)
        # Grade the frozen artifact even when dialogue failed or timed out.
        # Functional correctness does not establish a completed/valid conversation.
        try:
            if (evidence / 'workspace-export-error.json').exists():
                raise ValueError('Worker export failed; local files may not represent the executed artifact')
            checks = task.run_checks(inputs, evidence / 'after', evidence / 'verifier')
            reference = json.loads((output / 'qualification.json').read_text())['runs'][1]['checks']
            if checks['status'] == 'pass' and [g['outcome_sha256'] for g in checks['groups']] != [
                    g['outcome_sha256'] for g in reference['groups']]:
                checks['status'] = 'unknown'
                checks['reason'] = 'Test identities/outcomes differ from the qualified reference'
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            checks = {'status': 'unknown', 'reason': str(exc)}
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
    parser.add_argument('--task', choices=['cattrs', 'ofetch', 'tomlkit', 'cattrs-repair'], default='cattrs')
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--user-qualification', type=Path, help='Optional historical user-probe evidence; not an execution gate')
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--reference-skill-path', type=Path,
                        help='Compare this current skill against --skill-path as candidate; omit the no-skill baseline')
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--agent', choices=['codex', 'claude-code'], required=True)
    parser.add_argument('--solver-profile', type=Path, required=True)
    parser.add_argument('--user-profile', type=Path, required=True)
    parser.add_argument('--effort', choices=['low', 'high', 'max', 'xhigh'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--total-seconds', type=int, required=True)
    parser.add_argument('--prepare-only', action='store_true', help='Freeze the plan without any model call')
    args = parser.parse_args()
    limits = {'total_seconds': args.total_seconds}
    plan = prepare_pair(args.inputs.resolve(), args.qualification.resolve(), args.output.resolve(), args.agent,
        load_profile(args.solver_profile), load_profile(args.user_profile), args.effort, args.skill_path.resolve(), limits,
        args.user_qualification.resolve() if args.user_qualification else None,
        args.reference_skill_path.resolve() if args.reference_skill_path else None, args.task)
    if not args.prepare_only:
        results = run_pair(args.output.resolve(), plan, args.credentials.resolve())
        return 0 if all(r['status'] == 'completed' and r['task_status'] == 'pass'
                        and r.get('comparison_validity') == 'valid' for r in results) else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
