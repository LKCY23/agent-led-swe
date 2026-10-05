"""Reject installed-but-uninvoked skills and mismatched native injection evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from native_skills import verify_activation
from agent_adapters import get_adapter


class NativeSkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / 'source'
        self.skill.mkdir()
        (self.skill / 'SKILL.md').write_text('Expected source body')
        (self.root / 'capture').mkdir()

    def test_claude_requires_catalog_and_native_replay_not_read(self):
        init = {'init_context': [{'skills': ['agent-led-swe']}], 'native_skill_invocations': [],
                'isolation_status': 'verified-discovery'}
        path = self.root / 'capture/trace.json'
        path.write_text(json.dumps(init))
        self.assertEqual(verify_activation('claude-code', self.root, self.skill, 'entry')['status'], 'failed')
        init['native_skill_invocations'] = ['agent-led-swe']
        path.write_text(json.dumps(init))
        self.assertEqual(verify_activation('claude-code', self.root, self.skill, 'entry')['status'], 'verified')
        self.assertEqual(verify_activation('claude-code', self.root, None, None)['status'], 'failed')

    def test_codex_requires_matching_native_input_body_and_path(self):
        sessions = self.root / 'native-codex-session'
        sessions.mkdir()
        def save(text, role='user'):
            (sessions / 'session.jsonl').write_text(json.dumps({'type': 'response_item', 'payload': {
                'role': role, 'content': [{'text': text}]}}) + '\n')
        save('I read the skill')
        self.assertEqual(verify_activation('codex', self.root, self.skill, '/installed/SKILL.md')['status'], 'failed')
        text = '<skill>\n<name>agent-led-swe</name>\n<path>/installed/SKILL.md</path>\nExpected source body\n</skill>'
        save(text, role='assistant')
        self.assertEqual(verify_activation('codex', self.root, self.skill, '/installed/SKILL.md')['status'], 'failed')
        save(text)
        self.assertEqual(verify_activation('codex', self.root, self.skill, '/installed/SKILL.md')['status'], 'verified')
        (self.skill / 'SKILL.md').write_text('Different source')
        self.assertEqual(verify_activation('codex', self.root, self.skill, '/installed/SKILL.md')['status'], 'failed')

    def test_each_agent_has_its_native_prefix(self):
        self.assertEqual(get_adapter('codex').invocation(), '$agent-led-swe\n\n')
        self.assertEqual(get_adapter('claude-code').invocation(), '/agent-led-swe\n\n')
