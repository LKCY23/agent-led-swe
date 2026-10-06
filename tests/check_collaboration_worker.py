#!/usr/bin/env python3
"""Two native CLI turns against a fake API; no credentials or real model calls."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from agent_adapters import get_adapter
from collaboration_runtime import UserReply, converse
from evaluation_runtime import (DEFAULT_EVALUATOR, build_worker_image, execution_environment,
                                freeze_helpers, write_json)
from model_config import CONFIGS, load_profile
from native_skills import verify_activation
from run_evaluation import freeze_skill


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['codex', 'claude-code'], required=True)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    versions = json.loads((CONFIGS / 'agents.json').read_text())
    cli = {'agent': args.agent, 'version': versions[args.agent]['version']}
    image = build_worker_image({'image': args.base_image}, cli['version'], output / 'build', args.agent)
    freeze_helpers(DEFAULT_EVALUATOR, output / 'helpers')
    freeze_skill(args.skill_path.resolve(), output / 'frozen-skill')
    adapter = get_adapter(args.agent)
    profile = (load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')
               if args.agent == 'claude-code' else None)
    model = profile['model'] if profile else 'gpt-6.1-sol'
    task = {'environment': {'kind': 'docker', 'worker_image': image}}
    reports = []
    for variant in ('baseline', 'skill'):
        evidence = output / variant
        evidence.mkdir()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                write_json(evidence / 'requests.json', requests)
                rendered = json.dumps(payload, ensure_ascii=False)
                text = 'REPLY_TWO' if 'USER_FEEDBACK_TOKEN' in rendered else 'REPLY_ONE'
                if args.agent == 'codex':
                    item = {'id': f'msg_{len(requests)}', 'type': 'message', 'role': 'assistant',
                            'status': 'completed', 'content': [{'type': 'output_text', 'text': text, 'annotations': []}]}
                    response = {'id': f'resp_{len(requests)}', 'object': 'response', 'status': 'completed',
                                'model': model, 'output': [item],
                                'usage': {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}}
                    events = [(None, {'type': 'response.created', 'response': {**response, 'status': 'in_progress', 'output': []}}),
                              (None, {'type': 'response.output_item.added', 'output_index': 0,
                                      'item': {**item, 'status': 'in_progress', 'content': []}}),
                              (None, {'type': 'response.output_text.delta', 'item_id': item['id'], 'output_index': 0,
                                      'content_index': 0, 'delta': text}),
                              (None, {'type': 'response.output_item.done', 'output_index': 0, 'item': item}),
                              (None, {'type': 'response.completed', 'response': response})]
                else:
                    message = {'id': f'msg_{len(requests)}', 'type': 'message', 'role': 'assistant', 'model': model,
                               'content': [{'type': 'text', 'text': text}], 'stop_reason': 'end_turn', 'stop_sequence': None,
                               'usage': {'input_tokens': 10, 'output_tokens': 2, 'cache_read_input_tokens': 0,
                                         'cache_creation_input_tokens': 0}}
                    if not payload.get('stream'):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(message).encode())
                        return
                    events = [('message_start', {'type': 'message_start', 'message': {**message, 'content': [], 'stop_reason': None}}),
                              ('content_block_start', {'type': 'content_block_start', 'index': 0,
                                                       'content_block': {'type': 'text', 'text': ''}}),
                              ('content_block_delta', {'type': 'content_block_delta', 'index': 0,
                                                       'delta': {'type': 'text_delta', 'text': text}}),
                              ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
                              ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
                                                 'usage': message['usage']}),
                              ('message_stop', {'type': 'message_stop'})]
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for index, (event, body) in enumerate(events):
                    prefix = f'event: {event}\n' if event else ''
                    self.wfile.write((prefix + 'data: ' + json.dumps({**body, 'sequence_number': index}) + '\n\n').encode())

        server = ThreadingHTTPServer(('0.0.0.0', 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix='conversation-probe-') as tmp:
                work = Path(tmp).resolve()
                (work / 'pyproject.toml').write_text('[build-system]\nrequires=["hatchling"]\nbuild-backend="hatchling.build"\n'
                    '[project]\nname="probe"\nversion="0.0.0"\n[tool.hatch.build.targets.wheel]\npackages=["probe"]\n')
                (work / 'probe').mkdir()
                (work / 'probe/__init__.py').write_text('')
                (work / 'fixture.txt').write_text('PUBLIC_FIXTURE')
                treatment = output / 'frozen-skill' if variant == 'skill' else None
                def responder(messages, current, timeout):
                    if (current / 'fixture.txt').read_text() != 'PUBLIC_FIXTURE':
                        raise ValueError('User did not receive the public workspace snapshot')
                    if messages[-1]['content'] == 'REPLY_ONE':
                        return UserReply('USER_FEEDBACK_TOKEN')
                    if messages[-1]['content'] == 'REPLY_TWO':
                        return UserReply('Accepted.', accepted=True)
                    raise ValueError('Unexpected mock solver reply')
                with execution_environment(task, work, evidence, cli, treatment, authenticate=False,
                        model_profile=profile, model_upstream=f'http://host.docker.internal:{server.server_port}') as runtime:
                    binary, cwd, sandbox, entrypoint = runtime
                    context = adapter.prepare_context(binary, cwd, evidence, model, 'high', sandbox, entrypoint)
                    result = converse(adapter, binary, cwd, sandbox, context, model, 'high', output / 'helpers',
                        work, evidence / 'conversation', 'NATIVE_CONVERSATION_PROBE', responder,
                        invocation=adapter.invocation() if treatment else '', max_turns=3, timeout=180, turn_timeout=60)
                activation = verify_activation(args.agent, evidence, treatment, entrypoint,
                                               'conversation/turn-001/capture')
                second = [p for p in requests if 'USER_FEEDBACK_TOKEN' in json.dumps(p)]
                history_preserved = bool(second) and all('REPLY_ONE' in json.dumps(p) for p in second)
                passed = (result['status'] == 'completed' and len(result['turns']) == 2
                          and history_preserved and activation['status'] == 'verified')
                reports.append({'variant': variant, 'passed': passed, 'history_preserved': history_preserved,
                                'native_activation': activation, 'result': result})
        finally:
            server.shutdown()
            server.server_close()
        write_json(output / 'report.json', {'model_calls': 0, 'synthetic_api': True, 'variants': reports})
    print(json.dumps([{'variant': r['variant'], 'passed': r['passed']} for r in reports]))
    return 0 if all(r['passed'] for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
