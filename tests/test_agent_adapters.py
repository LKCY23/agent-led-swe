"""Cross-agent contracts using synthetic native events and explicit configuration."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_adapters import get_adapter
from model_config import credential, load_profile, validate_compatibility, CONFIGS


class AgentAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = get_adapter('claude-code')
        self.profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')

    def trace(self, **changes):
        final = {'type': 'result', 'subtype': 'success', 'is_error': False,
                 'usage': {'input_tokens': 5, 'cache_read_input_tokens': 3,
                           'cache_creation_input_tokens': 2, 'output_tokens': 4},
                 'modelUsage': {'deepseek-flash': {}}, 'total_cost_usd': 0.1}
        final.update(changes)
        init = {'type': 'system', 'subtype': 'init', 'tools': ['Read', 'Bash'],
                'skills': [], 'plugins': [], 'agents': [], 'mcp_servers': []}
        return '\n'.join(json.dumps(e) for e in [init, final])

    def test_completion_usage_and_isolation_are_distinct_from_task_success(self):
        trace = self.adapter.inspect_trace(self.trace())
        self.assertTrue(trace['telemetry_usable'])
        self.assertEqual(trace['usage']['input_tokens'], 10)
        self.assertEqual(trace['isolation_status'], 'verified-discovery')
        self.assertEqual(trace['models_observed'], ['deepseek-flash'])
        self.assertEqual(trace['task_status'], 'unknown')

    def test_errors_missing_result_and_malformed_lines_never_complete(self):
        for trace in ('', self.trace(is_error=True), self.trace(subtype='error_max_turns'),
                      self.trace() + '\nnot json', self.trace() + '\n' + self.trace()):
            self.assertFalse(self.adapter.inspect_trace(trace)['telemetry_usable'])
        self.assertEqual(self.adapter.inspect_trace(self.trace().replace('"skills": []',
                         '"skills": ["unexpected"]'))['isolation_status'], 'unknown')
        self.assertEqual(self.adapter.inspect_trace(self.trace().replace('"agents": []',
                         '"agents": ["custom-agent"]'))['isolation_status'], 'unknown')

    def test_context_suffix_is_not_a_different_provider_model(self):
        trace = self.adapter.inspect_trace(self.trace(modelUsage={'deepseek-flash[1m]': {}}))
        self.assertEqual(trace['models_observed'], ['deepseek-flash'])
        self.assertEqual(trace['native_model_labels'], ['deepseek-flash[1m]'])

    def test_command_disables_extra_tools_and_implicit_configuration(self):
        command = self.adapter.command(['docker', 'exec', 'container', 'claude'],
                                       Path('/testbed'), 'deepseek-flash', 'high', 'danger-full-access', {})
        self.assertNotIn('--bare', command)
        self.assertNotIn('--disable-slash-commands', command)
        self.assertIn('--replay-user-messages', command)
        self.assertEqual(command[command.index('--setting-sources') + 1], 'user')
        self.assertNotIn('--fallback-model', command)

    def test_model_and_agent_compatibility(self):
        validate_compatibility('claude-code', self.profile, 'high')
        for agent, effort in [('codex', 'high'), ('claude-code', 'xhigh')]:
            with self.assertRaises(ValueError):
                validate_compatibility(agent, self.profile, effort)

    def test_local_credential_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'credentials.json'
            path.write_text('{"DEEPSEEK_API_KEY":"file-value"}')
            with patch.dict('os.environ', {}, clear=True):
                self.assertEqual(credential(self.profile, path), 'file-value')
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'environment-value'}):
                self.assertEqual(credential(self.profile, path), 'environment-value')


if __name__ == '__main__':
    unittest.main()
