"""Cross-agent contracts using synthetic native events and explicit configuration."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_adapters import get_adapter
from model_config import credential, load_profile, validate_compatibility, CONFIGS, claude_environment, claude_model


class AgentAdapterTest(unittest.TestCase):
    def test_codex_runtime_overrides_reach_exec_parser(self):
        from agent_adapters.codex import codex_command
        command = codex_command(['docker', 'exec', '-i', 'worker', 'codex',
            '-c', 'model_provider="evaluation-gateway"', '-c', 'example=true'],
            Path('/testbed'), 'gpt-6.1-sol', 'high', 'danger-full-access')
        exec_index = command.index('exec', command.index('codex'))
        self.assertGreater(command.index('model_provider="evaluation-gateway"'), exec_index)
        self.assertGreater(command.index('example=true'), exec_index)

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
        self.assertEqual(self.adapter.inspect_trace(self.trace().replace('"plugins": []',
                         '"plugins": ["unexpected"]'))['isolation_status'], 'unknown')

    def test_project_capabilities_and_native_tools_are_not_rejected(self):
        trace = self.trace().replace('"skills": []', '"skills": ["project-guide"]')
        trace = trace.replace('"agents": []', '"agents": ["project-reviewer"]')
        trace = trace.replace('"tools": ["Read", "Bash"]', '"tools": ["Read", "Bash", "Skill", "Agent", "TodoWrite"]')
        self.assertEqual(self.adapter.inspect_trace(trace)['isolation_status'], 'verified-discovery')

    def test_context_suffix_is_not_a_different_provider_model(self):
        trace = self.adapter.inspect_trace(self.trace(modelUsage={'deepseek-flash[1m]': {}}))
        self.assertEqual(trace['models_observed'], ['deepseek-flash'])
        self.assertEqual(trace['native_model_labels'], ['deepseek-flash[1m]'])

    def test_background_completion_can_produce_another_main_result(self):
        rows = [json.loads(line) for line in self.trace().splitlines()]
        rows[-1].update(uuid='result-1', session_id='same-session')
        rows += [dict(rows[0]), {**rows[-1], 'uuid': 'result-2'}]
        parsed = self.adapter.inspect_trace('\n'.join(map(json.dumps, rows)))
        self.assertTrue(parsed['telemetry_usable'])
        self.assertEqual(parsed['isolation_status'], 'verified-discovery')
        self.assertEqual(parsed['usage']['input_tokens'], 10)
        self.assertEqual(len(parsed['init_context']), 1)

    def test_command_preserves_native_tools_project_settings_and_model(self):
        command = self.adapter.command(['docker', 'exec', 'container', 'claude'],
                                       Path('/testbed'), 'deepseek-flash', 'high', 'danger-full-access', {})
        self.assertNotIn('--bare', command)
        self.assertNotIn('--disable-slash-commands', command)
        self.assertIn('--replay-user-messages', command)
        self.assertEqual(command[command.index('--tools') + 1], 'default')
        self.assertEqual(command[command.index('--model') + 1], 'deepseek-flash[1m]')
        self.assertIn('--forward-subagent-text', command)
        self.assertNotIn('--setting-sources', command)
        self.assertNotIn('--settings', command)
        self.assertNotIn('--fallback-model', command)

    def test_context_capability_reaches_all_model_slots(self):
        env = claude_environment(self.profile, 'placeholder')
        for key in ('ANTHROPIC_MODEL', 'CLAUDE_CODE_SUBAGENT_MODEL',
                    'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL',
                    'ANTHROPIC_DEFAULT_HAIKU_MODEL', 'ANTHROPIC_DEFAULT_FABLE_MODEL'):
            self.assertEqual(env[key], 'deepseek-flash[1m]')
        self.assertEqual(claude_model('unknown-model'), 'unknown-model')

    def test_delegation_is_an_explicit_experiment_condition(self):
        command = self.adapter.conversation_command(['claude'], Path('/testbed'),
            'deepseek-flash', 'high', 'danger-full-access', {'allow_subagents': False},
            '00112233-4455-6677-8899-aabbccddeeff')
        self.assertEqual(command[command.index('--disallowedTools') + 1], 'Agent,Task,Workflow')
        enabled = self.adapter.command(['claude'], Path('/testbed'), 'deepseek-flash',
            'high', 'danger-full-access', {'allow_subagents': True})
        self.assertNotIn('--disallowedTools', enabled)
        from agent_adapters.codex import codex_command
        codex = codex_command('codex', Path('/testbed'), 'fixed', 'high', 'danger-full-access')
        self.assertIn('features.multi_agent=false', codex)

    def test_bash_heartbeat_is_not_a_subagent_message(self):
        heartbeat = {'type': 'tool_progress', 'tool_name': 'Bash', 'parent_tool_use_id': 'shell',
                     'heartbeat': True, 'elapsed_time_seconds': 30}
        text = self.trace() + '\n' + json.dumps(heartbeat)
        self.assertEqual(self.adapter.inspect_trace(text)['subagent_event_lines'], [])
        child = {'type': 'assistant', 'parent_tool_use_id': 'agent-call',
                 'message': {'content': [{'type': 'text', 'text': 'Child result'}]}}
        self.assertTrue(self.adapter.inspect_trace(text + '\n' + json.dumps(child))['subagent_event_lines'])

    def test_model_and_agent_compatibility(self):
        validate_compatibility('claude-code', self.profile, 'high')
        validate_compatibility('claude-code', {**self.profile, 'model': 'deepseek-v4-pro'}, 'high')
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
