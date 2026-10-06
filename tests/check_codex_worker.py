#!/usr/bin/env python3
"""Native Codex skill installation/injection against a local synthetic Responses API."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread

from agent_adapters import get_adapter
from evaluation_runtime import (DEFAULT_EVALUATOR, execute, execution_environment,
                                freeze_helpers, resolve_codex, write_json)
from native_skills import verify_activation
from run_evaluation import freeze_skill


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--image', help='Existing pinned Codex worker image; omit for isolated local HOME')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    freeze_skill(args.skill_path.resolve(), output / 'frozen-skill')
    freeze_helpers(DEFAULT_EVALUATOR, output / 'helpers')
    adapter = get_adapter('codex')
    cli = {'agent': 'codex', 'version': '0.160.0'} if args.image else resolve_codex()
    task = {'environment': {'kind': 'docker', 'worker_image': args.image}} if args.image else {'environment': {'kind': 'local'}}
    body = (output / 'frozen-skill/SKILL.md').read_text()
    reports = []
    for variant in ('baseline', 'skill'):
        evidence = output / variant
        evidence.mkdir()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                write_json(evidence / 'requests.json', requests)
                message = {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'status': 'completed',
                           'content': [{'type': 'output_text', 'text': 'READY', 'annotations': []}]}
                response = {'id': 'resp_1', 'object': 'response', 'status': 'completed',
                            'model': 'gpt-6.1-sol', 'output': [message],
                            'usage': {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}}
                events = [{'type': 'response.created', 'response': {**response, 'status': 'in_progress', 'output': []}},
                          {'type': 'response.output_item.added', 'output_index': 0, 'item': {**message, 'status': 'in_progress', 'content': []}},
                          {'type': 'response.output_text.delta', 'item_id': 'msg_1', 'output_index': 0, 'content_index': 0, 'delta': 'READY'},
                          {'type': 'response.output_item.done', 'output_index': 0, 'item': message},
                          {'type': 'response.completed', 'response': response}]
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for index, event in enumerate(events):
                    self.wfile.write(('data: ' + json.dumps({**event, 'sequence_number': index}) + '\n\n').encode())

        server = ThreadingHTTPServer(('0.0.0.0' if args.image else '127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp).resolve()
                (work / 'pyproject.toml').write_text('[build-system]\nrequires=["flit_core"]\nbuild-backend="flit_core.buildapi"\n[project]\nname="probe"\nversion="0.0.0"\ndescription="Protocol probe"\n')
                (work / 'probe.py').write_text('')
                skill = output / 'frozen-skill' if variant == 'skill' else None
                with execution_environment(task, work, evidence, cli, skill, authenticate=False,
                        model_upstream=f'http://host.docker.internal:{server.server_port}/v1' if args.image else None) as runtime:
                    binary, cwd, sandbox, path = runtime
                    context = adapter.prepare_context(binary, cwd, evidence, 'gpt-6.1-sol', 'high', sandbox, path)
                    command = adapter.command(binary, cwd, 'gpt-6.1-sol', 'high', sandbox, context)
                    host = 'model-gateway' if args.image else '127.0.0.1'
                    port = 8080 if args.image else server.server_port
                    if not args.image:
                        command[-1:-1] = ['-c', 'model_provider="probe"', '-c',
                            'model_providers.probe={name="probe",base_url="http://' + host + ':' + str(port) +
                            '",wire_api="responses",requires_openai_auth=false}']
                    prompt = evidence / 'prompt.txt'
                    prompt.write_text((adapter.invocation() if skill else '') + 'Reply READY without tools.')
                    result = execute(output / 'helpers', work, evidence / 'capture', command, 60, prompt, adapter)
                activation = verify_activation('codex', evidence, skill, path)
                injected = [block.get('text', '') for item in requests[0]['input'] for block in item.get('content', [])
                            if block.get('text', '').startswith('<skill>\n<name>agent-led-swe</name>')]
                assert result['run_status'] == 'completed' and activation['status'] == 'verified', (result, activation)
                assert (len(injected) == 1 and body in injected[0]) if skill else not injected
                reports.append({'variant': variant, 'status': 'passed', 'activation': activation,
                                'first_request_contains_full_native_skill': bool(injected), 'requests': len(requests)})
                write_json(output / 'report.json', reports)
                print(reports[-1], flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
