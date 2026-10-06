"""Conversation transitions and failure handling, independent of any model."""
import json
from pathlib import Path
import tempfile
import unittest

from agent_adapters import get_adapter
from collaboration_runtime import UserReply, completed_turn, converse
from cattrs_task import check_status, verify_inputs, TASK_ID, BASE_COMMIT, BENCH_COMMIT
from evaluation_runtime import file_hashes, write_json

SESSION = '00112233-4455-6677-8899-aabbccddeeff'
OTHER = '10112233-4455-6677-8899-aabbccddeeff'


class ConversationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / 'workspace'
        self.work.mkdir()
        (self.work / 'existing.md').write_text('Existing decision')
        self.prompts, self.commands = [], []
        self.session = SESSION
        self.status = 'completed'

    def capture(self, helpers, workspace, evidence, command, timeout, prompt, adapter):
        self.prompts.append(prompt.read_text())
        self.commands.append(command)
        evidence.mkdir()
        events = [{'type': 'thread.started', 'thread_id': self.session},
                  {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Review this result'}}]
        (evidence / 'stdout.log').write_text('\n'.join(json.dumps(e) for e in events))
        return {'run_status': self.status, 'usage': None}

    def run_conversation(self, responder, **changes):
        return converse(get_adapter('codex'), ['codex'], self.work, 'danger-full-access',
            {'overrides': []}, 'test-model', 'high', self.root, self.work, self.root / 'output',
            'Initial goal', responder, invocation='$agent-led-swe\n\n',
            capture=self.capture, **changes)

    def test_feedback_resumes_same_session_without_reinvoking_skill(self):
        def user(messages, work, timeout):
            self.assertEqual((work / 'existing.md').read_text(), 'Existing decision')
            return UserReply('Please fix one detail') if len(messages) == 2 else UserReply('Accepted', True)
        result = self.run_conversation(user)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['task_status'], 'unknown')
        self.assertEqual(self.prompts, ['$agent-led-swe\n\nInitial goal', 'Please fix one detail'])
        self.assertIn(SESSION, self.commands[1])
        self.assertIn('resume', self.commands[1])
        self.assertNotIn('--last', self.commands[1])

    def test_no_approval_by_silence_or_invalid_response(self):
        result = self.run_conversation(lambda *args: None)
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['accepted'])

    def test_user_failure_is_not_synthetic_feedback(self):
        def user(*args):
            raise RuntimeError('User service unavailable')
        result = self.run_conversation(user)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(len(self.prompts), 1)
        self.assertFalse((self.root / 'output/turn-001/user-reply.json').exists())

    def test_budget_ends_unaccepted_conversation(self):
        result = self.run_conversation(lambda *args: UserReply('Continue'), max_turns=2)
        self.assertEqual(result['status'], 'turn_limit')
        self.assertFalse(result['accepted'])
        self.assertEqual(len(self.prompts), 2)

    def test_native_error_does_not_reach_user_as_completed_work(self):
        self.status = 'timeout'
        def forbidden(*args):
            self.fail('Timed-out execution must not be presented as a completed turn')
        self.assertEqual(self.run_conversation(forbidden)['status'], 'timeout')

    def test_resume_must_not_create_new_session(self):
        def user(*args):
            self.session = OTHER
            return UserReply('Continue')
        result = self.run_conversation(user)
        self.assertEqual(result['status'], 'error')
        self.assertIn('changed during resume', result['error'])

    def test_user_cannot_silently_rewrite_evidence(self):
        def user(messages, work, timeout):
            (work / 'existing.md').write_text('rewritten')
            return UserReply('Accepted', True)
        self.assertEqual(self.run_conversation(user)['status'], 'error')
        self.assertEqual((self.work / 'existing.md').read_text(), 'Existing decision')

    def test_late_user_answer_does_not_authorize_another_turn(self):
        now = [0]
        def user(*args):
            now[0] += 11
            return UserReply('Accepted', True)
        result = self.run_conversation(user, user_timeout=10, clock=lambda: now[0])
        self.assertEqual(result['status'], 'timeout')
        self.assertFalse(result['accepted'])

    def test_resume_flags_keep_model_and_runtime_provider(self):
        adapter = get_adapter('codex')
        command = adapter.conversation_command(['docker', 'exec', 'worker', 'codex', '-c',
            'model_provider="fixture"'], Path('/testbed'), 'fixed', 'high', 'danger-full-access',
            {'overrides': ['features.plugins=false']}, SESSION)
        self.assertNotIn('-C', command)
        self.assertNotIn('--sandbox', command)
        self.assertIn('model_provider="fixture"', command)
        self.assertIn('sandbox_mode="danger-full-access"', command)
        self.assertIn('features.plugins=false', command)
        cc = get_adapter('claude-code').conversation_command(['claude'], Path('/testbed'),
            'fixed', 'high', 'danger-full-access', {}, SESSION)
        self.assertIn('--resume', cc)
        self.assertNotIn('--no-session-persistence', cc)


class CattrsVerifierTest(unittest.TestCase):
    def test_collection_errors_or_empty_tests_are_not_passes(self):
        good = {'timed_out': False, 'exit_code': 0, 'counts':
                {'tests': 1, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'failures': 0}}
        self.assertEqual(check_status(good), 'pass')
        for update in ({'errors': 1}, {'skipped': 1}, {'tests': 0}, {'xfailed': 1}):
            self.assertEqual(check_status({**good, 'counts': {**good['counts'], **update}}), 'unknown')
        self.assertEqual(check_status({**good, 'exit_code': 1,
            'counts': {**good['counts'], 'failures': 1}}), 'fail')

    def test_frozen_inputs_reject_changed_added_or_removed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'fixture').write_text('original')
            manifest = {'id': TASK_ID, 'base_commit': BASE_COMMIT, 'benchmark_commit': BENCH_COMMIT,
                        'files': file_hashes(root)}
            write_json(root / 'inputs.json', manifest)
            verify_inputs(root)
            (root / 'extra').write_text('leak')
            with self.assertRaises(ValueError):
                verify_inputs(root)
            (root / 'extra').unlink()
            (root / 'fixture').write_text('changed')
            with self.assertRaises(ValueError):
                verify_inputs(root)


if __name__ == '__main__':
    unittest.main()
