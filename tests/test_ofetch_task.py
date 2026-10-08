"""Verifier parsing distinguishes selected skips, missing tests and real failures."""
import json
from pathlib import Path
import tempfile
import unittest

from ofetch_task import test_result
from run_collaboration import task_adapter


class OfetchVerifierTest(unittest.TestCase):
    def check_result(self, states, group='new', code=0):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'result.json'
            p.write_text(json.dumps({'success': code == 0, 'numTotalTests': len(states),
                'numPassedTests': states.count('passed'), 'numFailedTests': states.count('failed'),
                'numPendingTests': states.count('pending'), 'testResults': [{'assertionResults': [
                    {'fullName': str(i), 'status': state} for i, state in enumerate(states)]}]}))
            return test_result(p, {'exit_code': code, 'timed_out': False}, group)

    def test_intentional_base_filter_is_not_new_suite_skip(self):
        self.assertEqual(self.check_result(['passed', 'pending'], 'base-ok')['status'], 'pass')
        self.assertEqual(self.check_result(['passed', 'pending'])['status'], 'unknown')

    def test_no_tests_and_execution_errors_cannot_pass(self):
        self.assertEqual(self.check_result([])['status'], 'unknown')
        self.assertEqual(self.check_result(['passed'], code=1)['status'], 'unknown')
        self.assertEqual(self.check_result(['failed'], code=1)['status'], 'fail')

    def test_fingerprint_tracks_test_identity_and_outcome(self):
        self.assertNotEqual(self.check_result(['passed'])['outcome_sha256'],
                            self.check_result(['failed'], code=1)['outcome_sha256'])

    def test_task_selection_rejects_unknown_backends(self):
        self.assertEqual(task_adapter('ofetch').TASK_ID, 'deepswe_ofetch-per-origin-circuit-breaker')
        self.assertEqual(task_adapter('cattrs').TASK_ID, 'deepswe_cattrs-partial-structuring-recovery')
        with self.assertRaises(ValueError):
            task_adapter('../ofetch')
