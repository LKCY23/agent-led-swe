"""Verify retained artifacts independently of dialogue completion or activation."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from evaluation_runtime import write_json
from run_collaboration import run_pair


class ArtifactEvaluationTest(unittest.TestCase):
    def test_version_pair_installs_each_frozen_skill_and_discloses_shared_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for name in ('task-inputs', 'scenario', 'current', 'candidate', 'reference-skill', 'frozen-skill'):
                (output / name).mkdir()
            (output / 'task-inputs/user-requirements.md').write_text('Requirements')
            (output / 'scenario/request.md').write_text('Request')
            (output / 'scenario/user.md').write_text('User role')
            write_json(output / 'qualification.json', {'runs': [{}, {'checks': {'groups': []}}]})
            plan = {'agent': {'agent': 'codex'}, 'variants': ['current', 'candidate'],
                    'variant_skills': {'current': 'reference-skill', 'candidate': 'frozen-skill'},
                    'user_profile': {}, 'user_environment': {}, 'user_agent': {}, 'user_effort': 'high',
                    'environment': {}, 'solver_profile': {'model': 'fixture'}, 'effort': 'high',
                    'limits': {'total_seconds': 1800}}
            def unpack(source, work):
                work.mkdir()
                (work / 'source.py').write_text('original = True\n')
            treatments = []
            @contextmanager
            def environment(case, work, evidence, cli, treatment, **kwargs):
                treatments.append(treatment)
                yield ['codex'], work, 'danger-full-access', '/native/SKILL.md'
            user = MagicMock()
            user.calls = 1
            with patch('cattrs_task.verify_inputs'), patch('run_collaboration.unpack', side_effect=unpack), \
                    patch('run_collaboration.SimulatedUser', return_value=user) as users, \
                    patch('run_collaboration.execution_environment', side_effect=environment), \
                    patch('run_collaboration.get_adapter') as adapters, \
                    patch('run_collaboration.converse', side_effect=lambda *a, **kw: {
                        'status': 'completed', 'accepted': True}) as conversations, \
                    patch('run_collaboration.verify_activation', return_value={'status': 'verified'}) as activation, \
                    patch('cattrs_task.run_checks', return_value={'status': 'pass', 'groups': []}):
                adapters.return_value.name = 'codex'
                adapters.return_value.prepare_context.return_value = {}
                adapters.return_value.invocation.return_value = '$agent-led-swe\n\n'
                results = run_pair(output, plan, Path('/unused'))
            self.assertEqual(treatments, [output / 'reference-skill', output / 'frozen-skill'])
            self.assertEqual([call.args[2] for call in activation.call_args_list], treatments)
            self.assertEqual(len(results), 2)
            for call in conversations.call_args_list:
                self.assertEqual(call.kwargs['invocation'], '$agent-led-swe\n\n')
                self.assertEqual(call.kwargs['timeout'], 1800)
                self.assertIn('share 1800 seconds total', call.args[10])
            for call in users.call_args_list:
                self.assertIn('share 1800 seconds total', call.args[1])

    def test_user_runtime_error_does_not_skip_artifact_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for name in ('task-inputs', 'scenario', 'baseline'):
                (output / name).mkdir()
            (output / 'task-inputs/user-requirements.md').write_text('Requirements')
            (output / 'scenario/request.md').write_text('Request')
            (output / 'scenario/user.md').write_text('User role')
            write_json(output / 'qualification.json', {'runs': [{}, {'checks': {
                'groups': [{'outcome_sha256': 'verified-tests'}]}}]})
            plan = {'agent': {'agent': 'claude-code'}, 'variants': ['baseline'],
                    'user_profile': {}, 'user_environment': {}, 'user_agent': {},
                    'user_effort': 'high', 'environment': {}, 'solver_profile': {},
                    'limits': {'total_seconds': 1200}}

            def unpack(source, work):
                work.mkdir()
                (work / 'source.py').write_text('original = True\n')

            @contextmanager
            def user(*args, **kwargs):
                raise RuntimeError('User failed to start')
                yield  # Context-manager shape; the failure happens on entry.

            user_instance = user()
            user_instance.calls = 0
            checks = {'status': 'pass', 'groups': [{'outcome_sha256': 'verified-tests'}]}
            with patch('cattrs_task.verify_inputs'), patch('run_collaboration.unpack', side_effect=unpack), \
                    patch('run_collaboration.SimulatedUser', return_value=user_instance), \
                    patch('cattrs_task.run_checks', return_value=checks) as verify:
                rows = run_pair(output, plan, Path('/unused'))
            verify.assert_called_once()
            self.assertEqual(rows[0]['status'], 'error')
            self.assertFalse(rows[0]['accepted'])
            self.assertEqual(rows[0]['comparison_validity'], 'invalid')
            self.assertEqual(rows[0]['task_status'], 'pass')
            self.assertEqual(json.loads((output / 'baseline/verifier-result.json').read_text()), checks)


if __name__ == '__main__':
    unittest.main()
