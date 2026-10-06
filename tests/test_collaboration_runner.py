"""Verify retained artifacts independently of dialogue completion or activation."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation_runtime import write_json
from run_collaboration import run_pair


class ArtifactEvaluationTest(unittest.TestCase):
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
            with patch('run_collaboration.verify_inputs'), patch('run_collaboration.unpack', side_effect=unpack), \
                    patch('run_collaboration.SimulatedUser', return_value=user_instance), \
                    patch('run_collaboration.run_checks', return_value=checks) as verify:
                rows = run_pair(output, plan, Path('/unused'))
            verify.assert_called_once()
            self.assertEqual(rows[0]['status'], 'error')
            self.assertFalse(rows[0]['accepted'])
            self.assertEqual(rows[0]['comparison_validity'], 'invalid')
            self.assertEqual(rows[0]['task_status'], 'pass')
            self.assertEqual(json.loads((output / 'baseline/verifier-result.json').read_text()), checks)


if __name__ == '__main__':
    unittest.main()
