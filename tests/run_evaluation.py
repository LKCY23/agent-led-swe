#!/usr/bin/env python3
"""Run bounded baseline/skill pairs on normalized behavior or real SWE tasks.

Independent workspaces isolate mutations. Agent-specific context checks disable
automatic skill discovery; real SWE workers run in Docker. Context checks alone
are not a filesystem boundary. No model calls occur with --help.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from evaluation_runtime import (DEFAULT_EVALUATOR, adapter_hashes, digest, execute,
                                freeze_helpers, positive_seconds, resolve_codex,
                                snapshot, write_json, file_hashes, execution_environment, build_worker_image)
from run_smoke import ROOT, case_ids, case_input_hash
from task_adapters import prepare_task, load_task, SWE_NAMES
from agent_adapters import get_adapter
from model_config import CONFIGS, DEFAULT_CREDENTIALS, load_profile, validate_compatibility, credential
from native_skills import verify_activation


COMMON_PROMPT = (
    'Complete the following disposable local task. Use local shell/file tools only. '
    'Modify only the supplied workspace; read only its inputs and explicitly supplied '
    'guidance. Do not browse, use connectors or other agents, change global settings, '
    'or inspect evaluation definitions, grading material, sibling runs or unrelated projects.\n\n')


def freeze_skill(root, destination):
    destination.mkdir()
    for name in ('SKILL.md', 'references', 'assets', 'agents', '.claude-plugin'):
        source = root / name
        if source.is_dir():
            shutil.copytree(source, destination / name)
        elif source.is_file():
            shutil.copyfile(source, destination / name)
    if not (destination / 'SKILL.md').is_file():
        raise ValueError('Target has no SKILL.md')
    return {str(p.relative_to(destination)): digest(p)
            for p in sorted(destination.rglob('*')) if p.is_file()}


def skill_source(root):
    """Git aids provenance; frozen file hashes identify the actual tested content."""
    result = {'path': str(root), 'git_commit': None, 'git_status': None}
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    if head.returncode == 0:
        result['git_commit'] = head.stdout.strip()
        result['git_status'] = subprocess.check_output(
            ['git', '-C', str(root), 'status', '--porcelain'], text=True).splitlines()
    return result


def run_pair(case, output, cli, model, effort, timeout, repetitions, evaluator,
             model_profile=None, credentials=DEFAULT_CREDENTIALS, skill_path=None,
             reference_skill_path=None, reverse_order=False, include_baseline=True):
    positive_seconds(timeout)
    if type(repetitions) is not int or repetitions <= 0:
        raise ValueError('repetitions must be a positive integer')
    skill_path = Path(skill_path or ROOT).resolve()
    reference_skill_path = Path(reference_skill_path).resolve() if reference_skill_path else None
    if not include_baseline and reference_skill_path is None:
        raise ValueError('Omitting baseline requires a reference skill for a current/candidate comparison')
    for source in (skill_path, reference_skill_path):
        if source is not None and not (source / 'SKILL.md').is_file():
            raise ValueError(f'Skill entrypoint not found: {source}')
        if source is not None and (output.resolve() == source or source in output.resolve().parents):
            # Existing default runs under tests/runs are excluded by freeze_skill.
            if not output.resolve().is_relative_to(source / 'tests/runs'):
                raise ValueError('Output must be outside the skill source or under its tests/runs')
    adapter = get_adapter(cli.get('agent', 'codex'))
    if model_profile:
        validate_compatibility(adapter.name, model_profile, effort)
        if model != model_profile['model']:
            raise ValueError('Model argument differs from the selected profile')
    if adapter.name == 'claude-code':
        if not model_profile:
            raise ValueError('Claude Code requires an explicit model profile')
        credential(model_profile, credentials)
    output.mkdir(parents=True, exist_ok=False)
    original_case = case
    case = prepare_task(case, output / 'task')
    if adapter.name == 'claude-code' and case['environment']['kind'] != 'docker':
        raise ValueError('Initial Claude Code integration supports Docker SWE tasks only')
    if case['environment']['kind'] == 'docker':
        case['environment']['execution_network'] = 'internal-model-gateway-v1'
        case['environment']['worker_image'] = build_worker_image(
            case['environment'], cli['version'].split()[-1], output / 'worker-build', adapter.name)
    write_json(output / 'case.json', case)
    shutil.copyfile(ROOT / 'tests/rubrics.md', output / 'rubrics.md')
    target = freeze_skill(skill_path, output / 'skill')
    variants = ['baseline', 'current', 'candidate'] if reference_skill_path else ['baseline', 'skill']
    if not include_baseline:
        variants.remove('baseline')
    targets = {variants[-1]: {'directory': 'skill', 'files': target, 'source': skill_source(skill_path)}}
    if reference_skill_path:
        targets['current'] = {'directory': 'reference-skill',
                              'files': freeze_skill(reference_skill_path, output / 'reference-skill'),
                              'source': skill_source(reference_skill_path)}
    helpers = freeze_helpers(evaluator, output / 'helpers')
    schedule = [(repetition, variant) for repetition in range(1, repetitions + 1)
                for variant in (variants if bool(repetition % 2) != reverse_order else list(reversed(variants)))]
    trials = [{'id': f'{case["id"]}-{repetition}-{variant}',
               'case_id': case['id'], 'variant': variant, 'repetition': repetition}
              for repetition, variant in schedule]
    plan = {
        'schema_version': 1, 'case_id': case['id'], 'split': 'development',
        'case_sha256': digest(output / 'case.json'),
        'input_sha256': case_input_hash(original_case) if 'files' in original_case else digest(output / 'case.json'),
        'task_files': file_hashes(output / 'task'),
        'target_files': target, 'skill_targets': targets, 'rubric_sha256': digest(output / 'rubrics.md'),
        'helpers': helpers, 'adapter_files': adapter_hashes(),
        'cli': cli, 'agent': adapter.name, 'model': model, 'model_profile': model_profile, 'effort': effort,
        'timeout_seconds': timeout, 'max_executor_calls': len(trials),
        'comparison_reference_variant': 'baseline' if include_baseline else 'current',
        'token_limit': None, 'cost_limit': None,
        'environment': case['environment'], 'routing': 'native explicit invocation; not an implicit routing test',
        'skill_loading_mode': 'native',
        'baseline_isolation': {
            'status': 'unknown',
            'reason': 'Per-trial discovery preflight pending; see each isolation.json and execution trace.'},
        'trials': trials,
    }
    # Freeze the complete planned matrix before the first execution, including missing trials.
    write_json(output / 'plan.json', plan)
    for trial in trials:
        evidence = output / trial['id']
        evidence.mkdir()
        write_json(evidence / 'result.json', {**trial, 'run_status': 'not_started'})
        with tempfile.TemporaryDirectory(prefix='swe-eval-') as tmp:
            workspace = Path(tmp).resolve()
            shutil.copytree(output / case['workspace'], workspace, dirs_exist_ok=True, symlinks=True)
            before = None
            result = {**trial, 'run_status': 'error', 'usage': None, 'elapsed_seconds': None}
            try:
                treatment = output / targets[trial['variant']]['directory'] if trial['variant'] in targets else None
                with execution_environment(case, workspace, evidence, cli, treatment,
                        model_profile=model_profile, credentials=credentials) as runtime:
                    binary, runtime_cwd, sandbox, skill_path = runtime
                    before = snapshot(workspace, evidence / 'before')
                    guidance = adapter.invocation() if skill_path else ''
                    prompt = evidence / 'prompt.txt'
                    prompt.write_text(guidance + COMMON_PROMPT + case['request'])
                    result['isolation'] = adapter.prepare_context(binary, runtime_cwd, evidence, model, effort, sandbox, skill_path)
                    command = adapter.command(binary, runtime_cwd, model, effort, sandbox, result['isolation'])
                    result.update(execute(output / 'helpers', workspace, evidence / 'capture',
                                          command, timeout, prompt, adapter))
                    if adapter.name == 'claude-code':
                        result['isolation']['status'] = result.get('isolation_status') or 'unknown'
                        write_json(evidence / 'isolation.json', result['isolation'])
                        if result['isolation']['status'] != 'verified-discovery':
                            result['execution_validity'] = {'status': 'invalid', 'reason': 'Claude discovery isolation was not verified'}
                        if result.get('models_observed') != [model]:
                            result['execution_validity'] = {'status': 'invalid', 'reason': 'Observed model differs or is unavailable'}
                result['skill_activation'] = verify_activation(adapter.name, evidence, treatment, skill_path)
                write_json(evidence / 'skill-activation.json', result['skill_activation'])
                native_paths = [evidence / 'skill-installation.json', evidence / 'skill-activation.json', prompt]
                native_paths += list((evidence / 'native-codex-session').rglob('*.jsonl'))
                result['native_files'] = {str(p.relative_to(evidence)): digest(p) for p in native_paths if p.is_file()}
                if result['skill_activation']['status'] != 'verified' and result['run_status'] == 'completed':
                    result['execution_validity'] = {'status': 'invalid', 'reason': 'Native skill activation/absence was not verified'}
                audit_path = evidence / 'environment-source-audit-after.json'
                if audit_path.is_file():
                    from packaging_environment import clean
                    if not clean(json.loads(audit_path.read_text())):
                        result['execution_validity'] = {'status': 'invalid', 'reason': 'Alternative packaging implementation appeared during execution'}
                    result['native_files'].update({p.name: digest(p) for p in evidence.glob('environment-source-audit-*.json')})
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                result['run_status'] = 'error'
                result['error'] = str(exc)
            finally:
                network_audit = evidence / 'network-audit.json'
                if network_audit.is_file():
                    checks = json.loads(network_audit.read_text())
                    result['network_isolation'] = {'status': 'verified' if checks and all(checks.values()) else 'invalid'}
                result.setdefault('native_files', {}).update({p.name: digest(p) for p in (
                    evidence / 'network-policy.json', network_audit, evidence / 'model-gateway.log') if p.is_file()})
                result['fixture_before'] = before
                result['fixture_after'] = snapshot(workspace, evidence / 'after')
                previous = before or {}
                write_json(evidence / 'changes.json', {
                    'added': sorted(result['fixture_after'].keys() - previous.keys()),
                    'removed': sorted(previous.keys() - result['fixture_after'].keys()),
                    'modified': sorted(p for p in previous.keys() & result['fixture_after'].keys()
                                       if previous[p] != result['fixture_after'][p])})
                write_json(evidence / 'result.json', result)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=case_ids() + list(SWE_NAMES))
    parser.add_argument('--swe-inputs', type=Path, help='Frozen benchmark rows and source archives')
    parser.add_argument('--agent', choices=['codex', 'claude-code'], default='codex')
    parser.add_argument('--agent-version', help='Pinned container CLI version; defaults to configs/agents.json')
    parser.add_argument('--model')
    parser.add_argument('--model-profile', type=Path)
    parser.add_argument('--credentials', type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    parser.add_argument('--timeout', type=positive_seconds, required=True, help='Seconds per executor')
    parser.add_argument('--repetitions', type=int, default=1)
    parser.add_argument('--skill-path', type=Path, default=ROOT, help='Candidate/target skill source to freeze')
    parser.add_argument('--reference-skill-path', type=Path, help='Add a current-version arm alongside baseline and candidate')
    parser.add_argument('--reverse-order', action='store_true', help='Reverse the first repetition order')
    parser.add_argument('--without-baseline', action='store_true',
                        help='Compare current/candidate only; requires --reference-skill-path')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'tests/runs', help='Parent for a fresh evidence directory')
    parser.add_argument('--evaluator', type=Path, default=DEFAULT_EVALUATOR)
    args = parser.parse_args()
    if args.repetitions <= 0:
        parser.error('--repetitions must be positive')
    try:
        case = load_task(args.case, args.swe_inputs)
        if args.model_profile and args.model:
            raise ValueError('Choose --model-profile or --model, not both')
        profile = load_profile(args.model_profile) if args.model_profile else None
        if not profile:
            if args.agent != 'codex' or not args.model:
                raise ValueError('Provide --model-profile; legacy --model is supported for Codex only')
            profile = {'provider': 'openai', 'protocol': 'codex-native',
                       'model': args.model, 'version_label': args.model}
        validate_compatibility(args.agent, profile, args.effort)
        if args.case in SWE_NAMES:
            versions = json.loads((CONFIGS / 'agents.json').read_text())
            version = args.agent_version or versions[args.agent]['version']
            cli = {'agent': args.agent, 'version': version, 'source': 'pinned container install'}
        else:
            if args.agent != 'codex':
                raise ValueError('Claude Code currently supports Docker SWE cases: pytest, packaging')
            if args.agent_version:
                raise ValueError('--agent-version applies to containers; local behavior tests use the installed CLI')
            cli = resolve_codex()
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        output = args.output_root.resolve() / f'pair-{args.case}-{stamp}'
        plan = run_pair(case, output, cli, profile['model'], args.effort, args.timeout,
                        args.repetitions, args.evaluator.resolve(), profile, args.credentials,
                        args.skill_path, args.reference_skill_path, args.reverse_order,
                        include_baseline=not args.without_baseline)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(output)
    results = [json.loads((output / t['id'] / 'result.json').read_text()) for t in plan['trials']]
    return 0 if all(r['run_status'] == 'completed' and r.get('execution_validity', {}).get('status') != 'invalid'
                    for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
