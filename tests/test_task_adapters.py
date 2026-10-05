"""Contract and grading gates that must hold across benchmark sources."""
from pathlib import Path
import tempfile
import unittest

from evaluate_results import check_bundle, task_status
from evaluation_runtime import digest, file_hashes
from functional_checks import functional_status
from task_adapters import load_task, prepare_task


class TaskAdapterTest(unittest.TestCase):
    def test_behavior_uses_same_workspace_contract_without_exposing_grader(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'task'
            task = prepare_task({'id': 'T', 'request': 'Task', 'files': {'a.txt': 'input'},
                                 'acceptance': ['Hidden criterion']}, output)
            self.assertEqual(task['environment']['kind'], 'local')
            self.assertEqual(task['workspace'], 'task/workspace')
            self.assertEqual(list(file_hashes(output / 'workspace')), ['a.txt'])
            self.assertNotIn('Hidden criterion', (output / 'workspace/a.txt').read_text())

    def test_unqualified_cases_are_not_silently_enabled(self):
        for name in ('dspy', 'agents-sdk'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                load_task(name, Path('/unused'))

    def test_validator_tampering_is_detected_before_grading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'task/validation').mkdir(parents=True)
            (root / 'task/validation/test_a.py').write_text('assert False\n')
            (root / 'case.json').write_text('{}')
            (root / 'rubrics.md').write_text('rubric')
            plan = {'case_sha256': digest(root / 'case.json'), 'rubric_sha256': digest(root / 'rubrics.md'),
                    'task_files': file_hashes(root / 'task')}
            check_bundle(root, plan)
            (root / 'task/validation/test_a.py').write_text('assert True\n')
            with self.assertRaisesRegex(ValueError, 'validation materials changed'):
                check_bundle(root, plan)

    def test_functional_failure_cannot_be_overruled_by_review(self):
        row = {'group': 'FAIL_TO_PASS', 'exit_code': 1, 'timed_out': False,
               'counts': {'tests': 1, 'failures': 1, 'errors': 0, 'skipped': 0, 'xfailed': 0}}
        self.assertEqual(functional_status(row), 'fail')
        self.assertEqual(task_status('completed', [{'status': 'pass'}, {'status': functional_status(row)}]), 'fail')
        row['counts']['failures'] = 0
        row['counts']['errors'] = 1
        self.assertEqual(functional_status(row), 'unknown')
        self.assertEqual(task_status('completed', [{'status': 'pass'}, {'status': 'unknown'}]), 'unknown')


if __name__ == '__main__':
    unittest.main()
