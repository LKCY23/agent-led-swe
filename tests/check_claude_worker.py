#!/usr/bin/env python3
"""Exercise the real containerized Claude CLI against a synthetic local API.

No provider credentials or model calls. The fake response asks Claude to read a
fixture (or treatment skill), then completes after the actual tool result.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from agent_adapters import get_adapter
from evaluation_runtime import (DEFAULT_EVALUATOR, build_worker_image, execute,
                                execution_environment, freeze_helpers, write_json)
from model_config import CONFIGS, load_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--version', default='2.1.278')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    image = build_worker_image({'image': args.base_image}, args.version, output / 'worker-build', 'claude-code')
    helpers = output / 'helpers'
    freeze_helpers(DEFAULT_EVALUATOR, helpers)
    adapter = get_adapter('claude-code')
    profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')
    task = {'environment': {'kind': 'docker', 'worker_image': image}}
    cli = {'agent': 'claude-code', 'version': args.version}
    reports = []
    for variant in ('baseline', 'skill'):
        evidence = output / variant
        evidence.mkdir()
        requests = []
        target = '/opt/target-skill/SKILL.md' if variant == 'skill' else '/testbed/fixture.txt'

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                # Evidence excludes HTTP headers, even though this key is synthetic.
                write_json(evidence / 'requests.json', requests)
                blocks = [b for m in payload.get('messages', [])
                          for b in m.get('content', []) if isinstance(b, dict)]
                finished = any(b.get('type') == 'tool_result' and b.get('tool_use_id') == 'probe_read'
                               for b in blocks)
                block = ({'type': 'text', 'text': 'MOCK_WORKER_OK'} if finished else
                         {'type': 'tool_use', 'id': 'probe_read', 'name': 'Read',
                          'input': {'file_path': target}})
                message = {'id': 'msg_probe', 'type': 'message', 'role': 'assistant',
                           'model': 'deepseek-flash', 'content': [block],
                           'stop_reason': 'end_turn' if finished else 'tool_use',
                           'stop_sequence': None, 'usage': {'input_tokens': 10, 'output_tokens': 4,
                              'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}}
                if not payload.get('stream'):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(message).encode())
                    return
                events = [
                    ('message_start', {'type': 'message_start', 'message': {**message, 'content': [],
                                       'stop_reason': None}}),
                    ('content_block_start', {'type': 'content_block_start', 'index': 0,
                     'content_block': {'type': 'text', 'text': ''} if finished else
                     {**block, 'input': {}}}),
                    ('content_block_delta', {'type': 'content_block_delta', 'index': 0,
                     'delta': {'type': 'text_delta', 'text': block['text']} if finished else
                     {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}}),
                    ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
                    ('message_delta', {'type': 'message_delta', 'delta': {
                        'stop_reason': message['stop_reason'], 'stop_sequence': None},
                        'usage': message['usage']}),
                    ('message_stop', {'type': 'message_stop'})]
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for kind, event in events:
                    self.wfile.write(f'event: {kind}\ndata: {json.dumps(event)}\n\n'.encode())
                self.wfile.flush()

        server = ThreadingHTTPServer(('0.0.0.0', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='cc-worker-check-') as tmp:
                work = Path(tmp).resolve()
                (work / 'setup.py').write_text('from setuptools import setup\nsetup(name="probe",version="0.0.0")\n')
                (work / 'fixture.txt').write_text('PUBLIC_FIXTURE_MARKER\n')
                skill = output / 'skill-input'
                if variant == 'skill':
                    skill.mkdir()
                    (skill / 'SKILL.md').write_text('TREATMENT_SKILL_MARKER\n')
                with execution_environment(task, work, evidence, cli,
                        skill if variant == 'skill' else None, authenticate=False, model_profile=profile) as runtime:
                    binary, cwd, sandbox, skill_path = runtime
                    # Override ONLY this disposable process with a synthetic endpoint/key.
                    binary[2:2] = ['-e', f'ANTHROPIC_BASE_URL=http://host.docker.internal:{server.server_port}',
                                   '-e', 'ANTHROPIC_API_KEY=synthetic-key']
                    context = adapter.prepare_context(binary, cwd, evidence, profile['model'], 'high', sandbox)
                    prompt = evidence / 'prompt.txt'
                    prompt.write_text(f'Read {skill_path or "/testbed/fixture.txt"}, then say MOCK_WORKER_OK.')
                    command = adapter.command(binary, cwd, profile['model'], 'high', sandbox, context)
                    result = execute(helpers, work, evidence / 'capture', command, 60, prompt, adapter)
                    write_json(evidence / 'result.json', result)
                trace = json.loads((evidence / 'capture/trace.json').read_text())
                assert result['run_status'] == 'completed', result
                assert trace['isolation_status'] == 'verified-discovery', trace
                assert trace['models_observed'] == ['deepseek-flash'], trace
                assert requests and all(r.get('model') == 'deepseek-flash' for r in requests)
                captured = json.dumps(requests)
                assert ('TREATMENT_SKILL_MARKER' in captured) == (variant == 'skill')
                assert ('PUBLIC_FIXTURE_MARKER' in captured) == (variant == 'baseline')
                reports.append({'variant': variant, 'cli_version': args.version, 'image': image,
                                'status': 'passed', 'requests': len(requests),
                                'scope': 'Real Claude CLI with synthetic API; no provider call'})
                write_json(output / 'report.json', reports)
                print(reports[-1], flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
