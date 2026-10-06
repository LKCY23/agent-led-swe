"""Read boundaries, model protocol and feedback semantics without paid calls."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch

from chat_completion import complete
from model_config import CONFIGS, load_profile
from evaluation_runtime import digest, write_json
from simulated_user import SimulatedUser, SnapshotReader


def answer(content, finish='stop'):
    return {'model': 'deepseek-flash', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
            'choices': [{'finish_reason': finish, 'message': {'role': 'assistant', 'content': content}}]}


def read_call(path):
    result = answer(None, 'tool_calls')
    result['choices'][0]['message'].update(reasoning_content='inspect supplied artifact', tool_calls=[
        {'id': 'read-1', 'type': 'function', 'function': {'name': 'read_file', 'arguments': json.dumps({'path': path})}}])
    return result


class UserTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.initial, self.current = self.root / 'initial', self.root / 'current'
        for p in (self.initial, self.current):
            p.mkdir()
            (p / 'api.md').write_text('PartialResult is defined')
        self.profile = load_profile(CONFIGS / 'models/user-deepseek-flash.json')

    def user(self, responses, **options):
        self.payloads = []
        def transport(profile, key, payload, timeout):
            self.payloads.append(json.loads(json.dumps(payload)))
            return responses.pop(0)
        return SimulatedUser(self.profile, 'SECRET_VALUE', 'Fixed user rules', 'Fixed requirements',
            self.initial, self.root / 'evidence', transport=transport, **options)

    def test_clarification_is_not_final_acceptance(self):
        user = self.user([answer('{"reply":"缺失字段算失败。","accepted":false}')])
        result = user([{'role': 'assistant', 'content': '缺失字段算什么？'}], self.current, 5)
        self.assertFalse(result.accepted)
        self.assertEqual(user.calls, 1)
        self.assertNotIn('SECRET_VALUE', (self.root / 'evidence/reply-001/call-01/request.json').read_text())

    def test_inspection_then_acceptance_retains_reasoning_tool_context(self):
        user = self.user([read_call('api.md'), answer('{"reply":"交付可以接受。","accepted":true}')])
        result = user([{'role': 'assistant', 'content': '请检查产物'}], self.current, 5)
        self.assertTrue(result.accepted)
        messages = self.payloads[1]['messages']
        self.assertEqual(messages[-2]['reasoning_content'], 'inspect supplied artifact')
        self.assertIn('PartialResult', messages[-1]['content'])

    def test_no_acceptance_without_inspection(self):
        user = self.user([answer('{"reply":"好","accepted":true}')])
        with self.assertRaisesRegex(ValueError, 'inspecting'):
            user([], self.current, 5)

    def test_typed_reply_tool_distinguishes_design_approval_from_delivery(self):
        response = read_call('unused')
        response['choices'][0]['message']['tool_calls'][0]['function'] = {
            'name': 'respond_to_agent', 'arguments': '{"reply":"方案可以，继续实现。","accepted":false}'}
        user = self.user([response])
        self.assertFalse(user([], self.current, 5).accepted)

    def test_typed_reply_still_rejects_missing_acceptance_field(self):
        response = read_call('unused')
        response['choices'][0]['message']['tool_calls'][0]['function'] = {
            'name': 'respond_to_agent', 'arguments': '{"reply":"可以"}'}
        user = self.user([response])
        with self.assertRaises(ValueError):
            user([], self.current, 5)

    def test_typed_reply_cannot_approve_and_inspect_in_same_batch(self):
        response = read_call('api.md')
        response['choices'][0]['message']['tool_calls'].append({'id': 'reply', 'type': 'function', 'function': {
            'name': 'respond_to_agent', 'arguments': '{"reply":"完成","accepted":true}'}})
        user = self.user([response])
        with self.assertRaises(ValueError):
            user([], self.current, 5)

    def test_observed_call_wrapper_is_normalized_without_relaxing_reply_contract(self):
        response = read_call('unused')
        response['choices'][0]['message']['tool_calls'][0]['function'] = {
            'name': 'call', 'arguments': '{"function":"respond_to_agent","reply":"继续。","accepted":false}'}
        user = self.user([response], max_calls=1)
        self.assertFalse(user([], self.current, 5).accepted)
        self.assertEqual(self.payloads[0]['tool_choice']['function']['name'], 'respond_to_agent')
        self.assertEqual(len(self.payloads[0]['tools']), 1)

    def test_malformed_or_truncated_output_is_not_feedback(self):
        for index, response in enumerate([answer('not JSON'), answer('{}'), answer('{}', 'length'), {}]):
            with self.subTest(index=index):
                path = self.root / f'case-{index}'
                user = SimulatedUser(self.profile, 'secret', 'rules', 'requirements', self.initial, path,
                    transport=lambda *args: response)
                with self.assertRaises(ValueError):
                    user([], self.current, 5)
                self.assertTrue((path / 'reply-001/error.json').exists())

    def test_call_budget_is_shared_across_user_replies(self):
        user = self.user([answer('{"reply":"继续","accepted":false}')], max_calls=1)
        user([], self.current, 5)
        with self.assertRaises(TimeoutError):
            user([], self.current, 5)
        self.assertEqual(user.calls, 1)

    def test_unknown_tool_cannot_execute_a_command(self):
        call = read_call('api.md')
        call['choices'][0]['message']['tool_calls'][0]['function'] = {'name': 'shell', 'arguments': '{"command":"touch marker"}'}
        user = self.user([call, answer('{"reply":"我无法核查。","accepted":false}')])
        with self.assertRaisesRegex(ValueError, 'not offered'):
            user([], self.current, 5)
        self.assertFalse((self.current / 'marker').exists())

    def test_last_call_cannot_use_a_removed_read_tool(self):
        user = self.user([read_call('api.md')], max_calls=1)
        with self.assertRaisesRegex(ValueError, 'not offered'):
            user([], self.current, 5)

    def test_paths_symlinks_git_and_extra_arguments_are_rejected(self):
        (self.root / 'private.txt').write_text('PRIVATE')
        (self.current / 'escape').symlink_to(self.root / 'private.txt')
        reader = SnapshotReader(self.initial, self.current)
        for name in ('../private.txt', str(self.root / 'private.txt'), 'escape', '.git/config'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                reader.call('read_file', {'path': name})
        with self.assertRaises(ValueError):
            reader.call('read_file', {'path': 'api.md', 'command': 'anything'})

    def test_uncommitted_changes_and_new_documents_are_visible(self):
        (self.current / 'api.md').write_text('Updated API')
        (self.current / 'design.md').write_text('Design evidence')
        reader = SnapshotReader(self.initial, self.current)
        changes = reader.call('list_changes', {})
        self.assertEqual(changes['added'], ['design.md'])
        self.assertEqual(changes['modified'], ['api.md'])
        self.assertIn('+Updated API', reader.call('read_diff', {'path': 'api.md'})['diff'])

    def test_long_file_read_is_explicitly_paginated(self):
        (self.current / 'large.md').write_text('\n'.join(str(i) for i in range(400)))
        result = SnapshotReader(self.initial, self.current).call('read_file', {'path': 'large.md', 'lines': 100})
        self.assertEqual(result['next_line'], 101)

    def test_real_pair_is_blocked_by_failed_user_qualification(self):
        from run_collaboration import prepare_pair
        inputs = self.root / 'inputs'
        inputs.mkdir()
        (inputs / 'inputs.json').write_text('{}')
        (inputs / 'user-requirements.md').write_text('requirements')
        qualification = self.root / 'qualification.json'
        write_json(qualification, {'qualified': True, 'inputs_sha256': digest(inputs / 'inputs.json'),
                                  'verifier_sha256': digest(Path(__file__).with_name('cattrs_task.py'))})
        user_qualification = self.root / 'user-qualification.json'
        write_json(user_qualification, {'qualified': False})
        with patch('run_collaboration.verify_inputs'), patch('run_collaboration.build_worker_image') as build:
            with self.assertRaisesRegex(ValueError, 'Simulated-user qualification'):
                prepare_pair(inputs, qualification, self.root / 'pair', 'claude-code',
                    load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json'), self.profile,
                    'high', self.root, {'turns': 2}, user_qualification)
            build.assert_not_called()
        self.assertFalse((self.root / 'pair').exists())


class TransportTest(unittest.TestCase):
    def run_server(self, mode):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if mode == 'slow':
                    time.sleep(.4)
                self.send_response(401 if mode == 'error' else 200)
                self.end_headers()
                try:
                    self.wfile.write(b'SECRET_FROM_ERROR' if mode == 'error' else json.dumps(answer('{}')).encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return {'base_url': f'http://127.0.0.1:{server.server_port}'}

    def test_real_http_transport_to_mock_endpoint(self):
        result = complete(self.run_server('ok'), 'secret', {'messages': []}, 3)
        self.assertEqual(result['model'], 'deepseek-flash')

    def test_http_error_is_sanitized_and_not_retried(self):
        with self.assertRaisesRegex(RuntimeError, '401') as error:
            complete(self.run_server('error'), 'secret', {}, 3)
        self.assertNotIn('SECRET_FROM_ERROR', str(error.exception))

    def test_deadline_stops_http_child(self):
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            complete(self.run_server('slow'), 'secret', {}, .1)
        self.assertLess(time.monotonic()-started, .35)


if __name__ == '__main__':
    unittest.main()
