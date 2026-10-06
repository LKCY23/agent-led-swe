#!/usr/bin/env python3
"""Two native CLI turns against a fake API; no credentials or real model calls."""
import argparse
from contextlib import ExitStack
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
from simulated_user import SimulatedUser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['codex', 'claude-code'], required=True)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--skill-path', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--with-simulated-user', action='store_true', help='Exercise the user HTTP/tool adapter against a fake API too')
    parser.add_argument('--with-subagent', action='store_true', help='Exercise native CC Task and forwarded child text')
    args = parser.parse_args()
    if args.with_subagent and args.agent != 'claude-code':
        parser.error('--with-subagent currently checks the CC Task protocol')
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
    user_cli = {'agent': 'claude-code', 'version': versions['claude-code']['version']}
    user_image = image
    if args.with_simulated_user and args.agent != 'claude-code':
        user_image = build_worker_image({'image': args.base_image}, user_cli['version'], output / 'user-build', 'claude-code')
    reports = []
    for variant in ('baseline', 'skill'):
        evidence = output / variant
        evidence.mkdir()
        requests = []
        user_requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                is_user = 'NATIVE_USER_TEST_ROLE' in json.dumps(payload.get('system', ''))
                target_requests = user_requests if is_user else requests
                target_requests.append(payload)
                write_json(evidence / ('user-requests.json' if is_user else 'requests.json'), target_requests)
                rendered = json.dumps(payload, ensure_ascii=False)
                text = 'REPLY_TWO' if 'USER_FEEDBACK_TOKEN' in rendered else 'REPLY_ONE'
                if args.agent == 'codex' and not is_user:
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
                    block = {'type': 'text', 'text': text}
                    if args.with_subagent and not is_user:
                        child = any(m.get('role') == 'user' and 'CHILD_REQUEST_TOKEN' in
                                    json.dumps(m.get('content')) for m in payload['messages'])
                        completed = any(b.get('type') == 'tool_result' and b.get('tool_use_id') == 'child-task'
                            for m in payload['messages'] for b in m.get('content', []) if isinstance(b, dict))
                        if child:
                            block = {'type': 'text', 'text': 'CHILD_RESULT_TOKEN'}
                        elif not completed and text == 'REPLY_ONE':
                            block = {'type': 'tool_use', 'id': 'child-task', 'name': 'Task', 'input': {
                                'description': 'Check child trace forwarding', 'subagent_type': 'general-purpose',
                                'model': 'haiku', 'prompt': 'CHILD_REQUEST_TOKEN: return CHILD_RESULT_TOKEN.'}}
                    if is_user:
                        finished = 'REPLY_TWO' in json.dumps(payload['messages'])
                        suffix = '2' if finished else '1'
                        blocks = [b for m in payload['messages'] for b in m.get('content', [])
                                  if isinstance(b, dict)]
                        done_ids = {b.get('tool_use_id') for b in blocks if b.get('type') == 'tool_result'}
                        if 'user-read-' + suffix not in done_ids:
                            block = {'type': 'tool_use', 'id': 'user-read-' + suffix, 'name': 'Read',
                                     'input': {'file_path': '/testbed/current/fixture.txt'}}
                        elif 'user-output-' + suffix not in done_ids:
                            block = {'type': 'tool_use', 'id': 'user-output-' + suffix, 'name': 'StructuredOutput',
                                     'input': {'reply': 'Accepted.' if finished else 'USER_FEEDBACK_TOKEN', 'accepted': finished}}
                        else:
                            block = {'type': 'text', 'text': 'Done.'}
                    message = {'id': f'msg_{len(target_requests)}', 'type': 'message', 'role': 'assistant',
                               'model': 'deepseek-flash' if is_user else model,
                               'content': [block], 'stop_reason': 'tool_use' if block['type'] == 'tool_use' else 'end_turn',
                               'stop_sequence': None,
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
                                                       'content_block': {'type': 'text', 'text': ''} if block['type'] == 'text' else {**block, 'input': {}}}),
                              ('content_block_delta', {'type': 'content_block_delta', 'index': 0,
                                                       'delta': {'type': 'text_delta', 'text': block['text']} if block['type'] == 'text' else
                                                         {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}}),
                              ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
                              ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': message['stop_reason'], 'stop_sequence': None},
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
                for filename in ('AGENTS.md', 'CLAUDE.md'):
                    (work / filename).write_text('PROJECT_GUIDANCE_TOKEN: follow the local project conventions.\n')
                if args.agent == 'claude-code':
                    (work / '.claude').mkdir()
                    write_json(work / '.claude/settings.json', {'hooks': {'SessionStart': [{
                        'hooks': [{'type': 'command', 'command': 'echo PROJECT_HOOK_TOKEN > hook-ran.txt'}]}]}})
                treatment = output / 'frozen-skill' if variant == 'skill' else None
                def responder(messages, current, timeout):
                    if (current / 'fixture.txt').read_text() != 'PUBLIC_FIXTURE':
                        raise ValueError('User did not receive the public workspace snapshot')
                    if messages[-1]['content'] == 'REPLY_ONE':
                        return UserReply('USER_FEEDBACK_TOKEN')
                    if messages[-1]['content'] == 'REPLY_TWO':
                        return UserReply('Accepted.', accepted=True)
                    raise ValueError('Unexpected mock solver reply')
                with ExitStack() as stack:
                    if args.with_simulated_user:
                        from evaluation_runtime import snapshot
                        snapshot(work, evidence / 'user-initial')
                        user_profile = load_profile(CONFIGS / 'models/user-deepseek-flash.json')
                        responder = stack.enter_context(SimulatedUser(user_profile, 'NATIVE_USER_TEST_ROLE',
                            'Inspect fixture.txt before accepting.', evidence / 'user-initial', evidence / 'user-model',
                            {'kind': 'docker', 'worker_image': user_image}, user_cli, Path('/unused'),
                            authenticate=False, model_upstream=f'http://host.docker.internal:{server.server_port}'))
                    runtime = stack.enter_context(execution_environment(task, work, evidence, cli, treatment, authenticate=False,
                        model_profile=profile, model_upstream=f'http://host.docker.internal:{server.server_port}'))
                    binary, cwd, sandbox, entrypoint = runtime
                    context = adapter.prepare_context(binary, cwd, evidence, model, 'high', sandbox, entrypoint)
                    context['allow_subagents'] = args.with_subagent
                    result = converse(adapter, binary, cwd, sandbox, context, model, 'high', output / 'helpers',
                        work, evidence / 'conversation', 'NATIVE_CONVERSATION_PROBE', responder,
                        invocation=adapter.invocation() if treatment else '', timeout=180)
                activation = verify_activation(args.agent, evidence, treatment, entrypoint,
                                               'conversation/turn-001/capture')
                second = [p for p in requests if 'USER_FEEDBACK_TOKEN' in json.dumps(p)]
                history_preserved = bool(second) and all('REPLY_ONE' in json.dumps(p) for p in second)
                passed = (result['status'] == 'completed' and len(result['turns']) == 2
                          and history_preserved and activation['status'] == 'verified')
                project_guidance = bool(requests) and 'PROJECT_GUIDANCE_TOKEN' in json.dumps(requests[0])
                passed = passed and project_guidance
                if not args.with_subagent:
                    if args.agent == 'claude-code':
                        from agent_adapters.claude_code import DELEGATION_TOOLS
                        trace = json.loads((evidence / 'conversation/turn-001/capture/trace.json').read_text())
                        passed = passed and not trace['subagent_event_lines'] and not DELEGATION_TOOLS.intersection(
                            trace['init_context'][0]['tools'])
                    else:
                        namespaces = [n.get('name') for p in requests for i in p.get('input', [])
                                      if i.get('type') == 'additional_tools' for n in i.get('tools', [])]
                        passed = passed and 'collaboration' not in namespaces
                child_forwarded = None
                if args.with_subagent:
                    rows = [json.loads(line) for line in (evidence / 'conversation/turn-001/capture/stdout.log').read_text().splitlines()]
                    child_forwarded = any(e.get('parent_tool_use_id') and 'CHILD_RESULT_TOKEN' in json.dumps(e)
                                          for e in rows)
                    passed = passed and child_forwarded
                if args.agent == 'claude-code':
                    passed = passed and (work / 'hook-ran.txt').read_text().strip() == 'PROJECT_HOOK_TOKEN'
                    trace = json.loads((evidence / 'conversation/turn-001/capture/trace.json').read_text())
                    usage = trace['native_model_usage']
                    passed = passed and bool(usage) and all(v.get('contextWindow') == 1000000 for v in usage.values())
                    passed = passed and sum(row['execution']['usage']['input_tokens'] or 0
                                            for row in result['turns']) == len(requests) * 10
                if args.with_simulated_user:
                    passed = passed and len(user_requests) >= 4
                reports.append({'variant': variant, 'passed': passed, 'history_preserved': history_preserved,
                                'project_guidance_preserved': project_guidance,
                                'child_text_forwarded': child_forwarded,
                                'native_activation': activation, 'result': result})
        finally:
            server.shutdown()
            server.server_close()
        write_json(output / 'report.json', {'model_calls': 0, 'synthetic_api': True, 'variants': reports})
    print(json.dumps([{'variant': r['variant'], 'passed': r['passed']} for r in reports]))
    return 0 if all(r['passed'] for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
