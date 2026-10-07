#!/usr/bin/env python3
"""Run one bounded target-present development case in a temporary fixture.

Requires installed Codex and skill-evaluator's capture.py. Model/effort are
carried from the user's config; other user configuration is not loaded by this
test invocation. This is not proof that all competing skill contexts are absent.
Raw evidence stays outside the executing workspace under ignored tests/runs/.
No baseline comparison, global installation, or app thread is created.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / 'tests/cases/behavior'
DEFAULT_D_TIMEOUT_SECONDS = 1800


def budget_notice(seconds):
    return (f'Execution budget: {float(seconds):g} seconds total for this run, '
            'including tool calls, experiments, checks and documentation.\n\n')


def case_ids():
    return sorted((p.stem for p in CASE_DIR.glob('*.json')),
                  key=lambda value: (len(value), value))


def load_case(case_id):
    if case_id not in case_ids():
        raise ValueError(f'Unknown runnable case: {case_id}')
    path = CASE_DIR / f'{case_id}.json'
    case = json.loads(path.read_text())
    if (not isinstance(case, dict) or case.get('id') != case_id
            or not isinstance(case.get('request'), str) or not case['request'].strip()):
        raise ValueError(f'Invalid case identity or request: {path}')
    if not isinstance(case.get('files'), dict):
        raise ValueError(f'Invalid fixture mapping: {path}')
    for name, content in case['files'].items():
        relative = Path(name)
        if (not name or '\x00' in name or relative.is_absolute() or '..' in relative.parts
                or relative == Path('.') or not isinstance(content, str)):
            raise ValueError(f'Invalid fixture file in {path}: {name}')
    if (not isinstance(case.get('acceptance'), list) or not case['acceptance']
            or any(not isinstance(item, str) or not item.strip() for item in case['acceptance'])):
        raise ValueError(f'Missing acceptance criteria: {path}')
    return case


def case_input_hash(case):
    body = json.dumps({key: case[key] for key in ('request', 'files')},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(body.encode()).hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts}


def main():
    from evaluation_runtime import positive_seconds
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=case_ids())
    parser.add_argument('--codex-bin', type=Path,
                        help='Use this exact CLI entrypoint instead of resolving codex through PATH')
    parser.add_argument('--capture', type=Path,
                        default=Path.home() / '.codex/skills/skill-evaluator/scripts/capture.py')
    parser.add_argument('--timeout', type=positive_seconds, default=DEFAULT_D_TIMEOUT_SECONDS,
                        help='Total seconds per run (default: 1800 / 30 minutes)')
    args = parser.parse_args()
    try:
        case = load_case(args.case)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    case_definition = {
        'path': str(CASE_DIR / f'{args.case}.json'),
        'sha256': hashlib.sha256((CASE_DIR / f'{args.case}.json').read_bytes()).hexdigest(),
        'input_sha256': case_input_hash(case)}
    capture = args.capture.resolve()
    if not capture.is_file():
        parser.error('Provide installed skill-evaluator capture.py with --capture')
    binary = str(args.codex_bin.expanduser().absolute()) if args.codex_bin else shutil.which('codex')
    if not binary:
        parser.error('codex is required')
    if not Path(binary).is_file() or not os.access(binary, os.X_OK):
        parser.error('Selected codex CLI is not an executable file')
    config_path = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    if config.get('model_provider') not in (None, 'openai'):
        parser.error('Custom model provider requires a reviewed evaluation configuration')
    settings = {key: config[key] for key in ('model', 'model_reasoning_effort') if key in config}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence = ROOT / 'tests/runs' / f'{args.case}-{stamp}'
    evidence.mkdir(parents=True, exist_ok=False)
    instruction_files = [ROOT / 'SKILL.md', ROOT / 'agents/openai.yaml', ROOT / '.claude-plugin/plugin.json']
    instruction_files += list((ROOT / 'references').rglob('*')) + list((ROOT / 'assets').rglob('*'))
    target_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in instruction_files if p.is_file()}
    prompt = ('Use the skill at ' + str(ROOT / 'SKILL.md') + '. Read its entrypoint and only relevant references. '
              'This is a disposable local task. Work only on the supplied fixture and read-only skill references; '
              'Do not browse, use connectors, inspect evaluation scripts, '
              'case definitions, grader-only material or sibling evidence, '
              'change global settings, or access unrelated projects.\n\n' + budget_notice(args.timeout) + case['request'])
    (evidence / 'prompt.txt').write_text(prompt)
    (evidence / 'case.json').write_text(json.dumps(case, ensure_ascii=False, indent=2) + '\n')
    with tempfile.TemporaryDirectory(prefix='agent-led-swe-case-') as tmp:
        fixture = Path(tmp).resolve()
        for name, content in case['files'].items():
            path = fixture / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        before = hashes(fixture)
        shutil.copytree(fixture, evidence / 'before')
        argv = [binary, 'exec', '--ignore-user-config', '--ephemeral', '--json',
                '--sandbox', 'workspace-write', '--skip-git-repo-check',
                '-C', str(fixture)]
        for key, value in settings.items():
            argv += ['-c', key + '=' + json.dumps(value)]
        argv += ['-']
        captured = subprocess.run([sys.executable, str(capture), '--cwd', str(fixture),
                        '--out', str(evidence / 'capture'), '--timeout', str(args.timeout),
                        '--stdin-file', str(evidence / 'prompt.txt'), '--'] + argv,
                       check=False, timeout=args.timeout + 15, capture_output=True, text=True)
        after = hashes(fixture)
        shutil.copytree(fixture, evidence / 'after')
        manifest = {'case': args.case,
                    'timeout_seconds': args.timeout,
                    'case_definition': case_definition,
                    'target': str(ROOT), 'target_files': target_hashes,
                    'cli': subprocess.check_output([binary, '--version'], text=True).strip(),
                    'cli_path': binary, 'cli_resolved_path': str(Path(binary).resolve()),
                    'execution_overrides': {'agents.enabled': False},
                    'settings': settings, 'sandbox': 'workspace-write',
                    'fixture_before': before, 'fixture_after': after,
                    'baseline': 'not run', 'routing': 'forced target use; not measured',
                    'isolation': 'temporary writable fixture; no claim of uncontaminated baseline'}
        (evidence / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(evidence)
    return captured.returncode


if __name__ == '__main__':
    raise SystemExit(main())
