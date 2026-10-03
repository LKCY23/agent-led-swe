#!/usr/bin/env python3
"""Check real host discovery without an LLM request or global skill installation.

Adapted from claudespace programming-practice/tests/check_hosts.py.
Uses installed Codex app-server skills/list and Claude plugin details. It creates
only a temporary fixture workspace and symlink. Hosts may perform their normal
runtime logging. This does not evaluate development behavior or automatic routing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(f'{args[0]} command failed (exit {result.returncode})')
    return result.stdout.strip()


class Rpc:
    def __init__(self, process):
        self.process = process
        self.selector = selectors.DefaultSelector()
        self.selector.register(process.stdout, selectors.EVENT_READ)
        self.buffer = b''

    def send(self, obj):
        self.process.stdin.write((json.dumps(obj) + '\n').encode())
        self.process.stdin.flush()

    def response(self, request_id):
        deadline = time.monotonic() + 20
        while True:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                if not line.strip():
                    continue
                message = json.loads(line)
                if message.get('id') == request_id:
                    if 'error' in message:
                        raise RuntimeError(f'RPC {request_id} error: {message["error"]}')
                    return message['result']
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError(f'RPC {request_id} timed out')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError('Codex app-server closed before answering')
            self.buffer += chunk

    def close(self):
        self.selector.close()


def codex_check(root):
    binary = shutil.which('codex')
    if binary is None:
        raise RuntimeError('codex is not installed')
    with tempfile.TemporaryDirectory(prefix='agent-led-swe-host-') as tmp:
        learner = Path(tmp).resolve() / 'learner'
        discovery = learner / '.agents/skills'
        discovery.mkdir(parents=True)
        (discovery / root.name).symlink_to(root, target_is_directory=True)
        run(['git', 'init', '-q', str(learner)])
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([binary, '-c', 'projects.' + json.dumps(str(learner)) + '.trust_level="trusted"', 'app-server', '--stdio'], cwd=learner,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=errors, start_new_session=True)
            rpc = Rpc(process)
            try:
                rpc.send({'id': 1, 'method': 'initialize', 'params': {
                    'clientInfo': {'name': 'agent_led_swe_check', 'version': '0.1.0'}}})
                rpc.response(1)
                rpc.send({'method': 'initialized', 'params': {}})
                rpc.send({'id': 2, 'method': 'skills/list', 'params': {
                    'cwds': [str(learner)], 'forceReload': True}})
                result = rpc.response(2)
                entries = [entry for entry in result['data'] if Path(entry['cwd']).resolve() == learner]
                if len(entries) != 1:
                    raise AssertionError('Missing fixture workspace result')
                entry = entries[0]
                matches = [s for s in entry['skills'] if Path(s['path']).resolve() == root / 'SKILL.md']
                if len(matches) != 1 or not matches[0]['enabled']:
                    raise AssertionError('Target skill discovery mismatch: ' + json.dumps({'candidates': [s for s in entry['skills'] if 'agent-led-swe' in s['name']], 'errors': entry.get('errors', [])}, ensure_ascii=False))
                target = matches[0]
                if target['name'] not in ('agent-led-swe', 'agent-led-swe:agent-led-swe'):
                    raise AssertionError('Unexpected discovered invocation name')
                interface = target.get('interface') or {}
                if interface.get('displayName') != 'Agent 主导的软件工程':
                    raise AssertionError('Codex did not load display_name from openai.yaml')
                if '$agent-led-swe' not in (interface.get('defaultPrompt') or ''):
                    raise AssertionError('Codex did not load the default prompt')
                if target['scope'] != 'repo':
                    raise AssertionError('Expected project-scoped discovery')
                return {'status': 'passed', 'version': run([binary, '--version']),
                        'name': target['name'], 'scope': target['scope'],
                        'display_name': interface['displayName'],
                        'default_prompt': interface['defaultPrompt'],
                        'explicit_invocation': '$' + target['name'],
                        'skill_path': str(root / 'SKILL.md'),
                        'other_discovery_errors': len(entry.get('errors', []))}
            finally:
                rpc.close()
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                process.stdin.close()
                process.stdout.close()


def claude_check(root):
    binary = shutil.which('claude')
    if binary is None:
        raise RuntimeError('claude is not installed')
    with tempfile.TemporaryDirectory(prefix='agent-led-swe-claude-') as tmp:
        run([binary, 'plugin', 'validate', str(root)], cwd=tmp)
        inventory = run([binary, '--plugin-dir', str(root), 'plugin', 'details', 'agent-led-swe'], cwd=tmp)
    if 'Skills (1)' not in inventory or 'agent-led-swe@inline' not in inventory:
        raise AssertionError('Expected exactly one skill from the session-local plugin')
    expected_version = json.loads((root / '.claude-plugin/plugin.json').read_text())['version']
    if f'agent-led-swe {expected_version}' not in inventory:
        raise AssertionError('Unexpected plugin name/version in inventory')
    return {'status': 'passed', 'version': run([binary, '--version']), 'inventory': inventory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.skill.resolve()
    if root.name != 'agent-led-swe' or not (root / 'SKILL.md').is_file():
        parser.error('--skill must point to the agent-led-swe skill directory')
    results = {}
    for host, check in [('codex', codex_check), ('claude_code', claude_check)]:
        try:
            results[host] = check(root)
        except Exception as exc:
            results[host] = {'status': 'failed', 'reason': str(exc)}
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r['status'] == 'passed' for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
