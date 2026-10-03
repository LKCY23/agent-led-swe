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
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'D1': {
        'files': {'README.md': '# Research utility\nWe are deciding how to organize task loading and evaluation.\n'},
        'request': '我准备做一个研究评测工具，现在只讨论 Tasks 和 Evaluation 的职责边界。请解释两个可行选择及取舍，列出最关键的待定问题。不要写文档或代码，也不要替我确认方案。',
    },
    'D4': {
        'files': {
            'docs/decisions/log.md': '# Decision log\n\n## DEC-001 — Result directory\n\n- Time: 2026-09-20T10:00:00+08:00\n- Decision-maker: human, confirmed in initial design meeting.\n- Decision: save results to results/.\n- Reason: keep outputs easy to locate.\n\n## DEC-002 — Internal parser\n\n- Time: 2026-09-21T10:00:00+08:00\n- Decision-maker: agent, delegated choice of local parsing implementation.\n- Decision: reuse the existing JSON parser.\n',
            'docs/design.md': '# Current design\n\nResults are saved in results/. The existing JSON parser is reused.\n',
        },
        'request': '我现在确定把结果目录从 results/ 改为 artifacts/，因为运行产物不仅是最终结果。请记录这个新的人工决定，关联被替代的决定，并更新现行设计。这里只改文档，不改代码，也不用提交 Git。',
    },
    'D7': {
        'files': {
            'docs/delivery.md': '# Delivery\n\n| Item | Acceptance | State |\n| --- | --- | --- |\n| Local calculation | 2 + 2 returns 4 | verified |\n| Remote result persistence | Integration check against staging storage | unverified |\n',
            'docs/verification.md': '# Checks\n\nCHECK-001: Local calculation passed on the supplied revision.\nCHECK-002: Remote result persistence was not run: staging credentials are unavailable. No remote integration result exists.\n',
        },
        'request': '请根据已有交付清单和验证记录，给我一段这次工作的交付结论。现在不运行新测试，也不要修改清单或记录。',
    },
}


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CASES)
    parser.add_argument('--capture', type=Path,
                        default=Path.home() / '.codex/skills/skill-evaluator/scripts/capture.py')
    args = parser.parse_args()
    capture = args.capture.resolve()
    if not capture.is_file():
        parser.error('Provide installed skill-evaluator capture.py with --capture')
    binary = shutil.which('codex')
    if not binary:
        parser.error('codex is required')
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
    case = CASES[args.case]
    prompt = ('Use the skill at ' + str(ROOT / 'SKILL.md') + '. Read its entrypoint and only relevant references. '
              'This is a disposable local task. Work only on the supplied fixture and read-only skill references; '
              'use local shell/file tools only. Do not browse, use connectors, inspect evaluation scripts or sibling evidence, '
              'invoke other agents, change global settings, or access unrelated projects.\n\n' + case['request'])
    (evidence / 'prompt.txt').write_text(prompt)
    with tempfile.TemporaryDirectory(prefix='agent-led-swe-case-') as tmp:
        fixture = Path(tmp).resolve()
        for name, content in case['files'].items():
            path = fixture / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        before = hashes(fixture)
        shutil.copytree(fixture, evidence / 'before')
        argv = [binary, 'exec', '--ignore-user-config', '--ephemeral', '--json',
                '--sandbox', 'workspace-write', '--skip-git-repo-check', '-C', str(fixture)]
        for key, value in settings.items():
            argv += ['-c', key + '=' + json.dumps(value)]
        argv += ['-']
        subprocess.run([shutil.which('python3'), str(capture), '--cwd', str(fixture),
                        '--out', str(evidence / 'capture'), '--timeout', '180',
                        '--stdin-file', str(evidence / 'prompt.txt'), '--'] + argv,
                       check=False, timeout=195, capture_output=True, text=True)
        after = hashes(fixture)
        shutil.copytree(fixture, evidence / 'after')
        manifest = {'case': args.case, 'target': str(ROOT), 'target_files': target_hashes,
                    'cli': subprocess.check_output([binary, '--version'], text=True).strip(),
                    'settings': settings, 'sandbox': 'workspace-write',
                    'fixture_before': before, 'fixture_after': after,
                    'baseline': 'not run', 'routing': 'forced target use; not measured',
                    'isolation': 'temporary writable fixture; no claim of uncontaminated baseline'}
        (evidence / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(evidence)


if __name__ == '__main__':
    main()
