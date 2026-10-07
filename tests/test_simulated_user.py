"""Native CC user boundary and reply checks, with no model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_adapters.claude_code import BUNDLED_SKILLS
from evaluation_runtime import digest, write_json
from model_config import CONFIGS, load_profile
from simulated_user import parse_reply, user_command

SESSION = '00112233-4455-6677-8899-aabbccddeeff'


def events(accepted=False, read=False):
    init = {'type': 'system', 'subtype': 'init', 'session_id': SESSION,
            'skills': sorted(BUNDLED_SKILLS), 'plugins': [], 'mcp_servers': [],
            'tools': ['Read', 'Glob', 'Grep', 'StructuredOutput']}
    rows = [init]
    if read:
        rows += [
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 'read',
             'name': 'Read', 'input': {'file_path': '/testbed/current/api.md'}}]}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'read',
             'content': 'actual contents', 'is_error': False}]}}]
    rows.append({'type': 'result', 'session_id': SESSION, 'subtype': 'success', 'is_error': False,
                 'modelUsage': {'deepseek-flash[1m]': {}},
                 'structured_output': {'reply': 'Reviewed', 'accepted': accepted}})
    return rows


def parse(rows, previous=None):
    return parse_reply('\n'.join(json.dumps(r) for r in rows), 'deepseek-flash', previous)


class NativeUserTest(unittest.TestCase):
    def test_design_approval_does_not_end_collaboration(self):
        reply, session, _ = parse(events())
        self.assertFalse(reply.accepted)
        self.assertEqual(session, SESSION)

    def test_acceptance_is_not_gated_by_this_turns_tool_history(self):
        self.assertTrue(parse(events(accepted=True))[0].accepted)
        self.assertTrue(parse(events(accepted=True, read=True))[0].accepted)
        rows = events(accepted=True, read=True)
        rows[2]['message']['content'][0]['is_error'] = True
        self.assertTrue(parse(rows)[0].accepted)

    def test_current_content_search_counts_as_inspection(self):
        rows = events(accepted=True, read=True)
        rows[1]['message']['content'][0].update(name='Grep', input={
            'path': 'current/api.md', 'pattern': 'PartialResult', 'output_mode': 'content'})
        self.assertTrue(parse(rows)[0].accepted)
        rows[1]['message']['content'][0]['input']['output_mode'] = 'files_with_matches'
        self.assertTrue(parse(rows)[0].accepted)

    def test_skill_or_write_tool_exposure_is_rejected(self):
        for key, value in [('tools', ['Read', 'Bash']), ('skills', ['agent-led-swe']),
                           ('mcp_servers', ['external']), ('plugins', ['extra'])]:
            rows = events()
            rows[0][key] = value
            with self.assertRaises(ValueError):
                parse(rows)

    def test_unexpected_native_tool_execution_is_rejected(self):
        rows = events(read=True)
        rows[1]['message']['content'][0]['name'] = 'Write'
        with self.assertRaises(ValueError):
            parse(rows)

    def test_raw_text_is_not_used_as_structured_output(self):
        rows = events()
        rows[-1].pop('structured_output')
        rows[-1]['result'] = '{"reply":"looks good","accepted":true}'
        with self.assertRaises(ValueError):
            parse(rows)

    def test_wrong_model_session_or_incomplete_result_is_rejected(self):
        for update in ({'modelUsage': {'deepseek-v4-pro': {}}}, {'session_id': 'bad'},
                       {'subtype': 'error_max_turns'}, {'is_error': True},
                       {'structured_output': {'reply': 'done', 'accepted': 'true'}}):
            rows = events()
            rows[-1].update(update)
            with self.assertRaises(ValueError):
                parse(rows)
        with self.assertRaises(ValueError):
            parse(events(), previous='11112233-4455-6677-8899-aabbccddeeff')

    def test_native_command_owns_tools_schema_and_resume(self):
        command = user_command(['docker', 'exec', 'user', 'claude'], Path('/testbed'),
            'deepseek-flash', 'high', 'USER_ROLE', SESSION)
        self.assertNotIn('--bare', command)
        self.assertNotIn('--max-turns', command)
        self.assertIn('--json-schema', command)
        self.assertEqual(command[command.index('--permission-mode') + 1], 'dontAsk')
        self.assertEqual(command[command.index('--tools') + 1], 'Read,Glob,Grep')
        self.assertEqual(command[command.index('--resume') + 1], SESSION)
        self.assertNotIn('--no-session-persistence', command)
        self.assertNotIn('respond_to_agent', ' '.join(command))
        self.assertNotIn('tool_choice', ' '.join(command))

    def test_missing_native_search_tools_is_rejected(self):
        rows = events()
        rows[0]['tools'] = ['Read', 'StructuredOutput']
        with self.assertRaises(ValueError):
            parse(rows)

    def test_historical_user_receipt_does_not_gate_current_run(self):
        from run_collaboration import prepare_pair
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / 'inputs'
            inputs.mkdir()
            (inputs / 'inputs.json').write_text('{}')
            write_json(inputs / 'environment.json', {'image': 'fixture'})
            (inputs / 'user-requirements.md').write_text('requirements')
            (root / 'SKILL.md').write_text('Test skill')
            qualification = root / 'task.json'
            write_json(qualification, {'qualified': True,
                'inputs_sha256': digest(inputs / 'inputs.json'),
                'verifier_sha256': digest(Path(__file__).with_name('cattrs_task.py'))})
            user_qualification = root / 'user.json'
            write_json(user_qualification, {'qualified': False})
            profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')
            with patch('run_collaboration.verify_inputs'), patch('run_collaboration.build_worker_image', return_value='fixture'):
                plan = prepare_pair(inputs, qualification, root / 'pair', 'claude-code', profile, profile,
                                    'high', root, {'total_seconds': 1200}, user_qualification)
            self.assertEqual(plan['limits'], {'total_seconds': 1200})
            self.assertEqual(plan['user_qualification_sha256'], digest(user_qualification))
            self.assertEqual(plan['variant_skills'], {'baseline': None, 'skill': 'frozen-skill'})
            reference = root / 'reference'
            reference.mkdir()
            (reference / 'SKILL.md').write_text('Current skill')
            with patch('run_collaboration.verify_inputs'), patch('run_collaboration.build_worker_image', return_value='fixture'):
                version_plan = prepare_pair(inputs, qualification, root / 'versions', 'claude-code', profile, profile,
                    'high', root, {'total_seconds': 1800}, reference_skill=reference)
            self.assertEqual(version_plan['variants'], ['current', 'candidate'])
            self.assertEqual(version_plan['variant_skills'], {
                'current': 'reference-skill', 'candidate': 'frozen-skill'})
            self.assertEqual((root / 'versions/reference-skill/SKILL.md').read_text(), 'Current skill')
            self.assertEqual((root / 'versions/frozen-skill/SKILL.md').read_text(), 'Test skill')
            self.assertNotEqual(version_plan['reference_skill_files']['SKILL.md'], version_plan['skill_files']['SKILL.md'])


if __name__ == '__main__':
    unittest.main()
