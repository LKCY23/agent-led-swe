import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluation_runtime import digest
from suite_tasks import github_patch, selectors, verify_inputs, prepare_suite_task
from swe_pro_verifier import official_status
from task_adapters import load_task, SWE_NAMES
from functional_checks import functional_status
from preflight_suite import qualify


class SuiteTest(unittest.TestCase):
    def test_selected_names_are_registered_without_enabling_unqualified_runs(self):
        for name in ('smolagents', 'xarray', 'nodebb', 'navidrome'):
            self.assertIn(name, SWE_NAMES)
            self.assertEqual(load_task(name, '/tmp/frozen')['id'], name)

    def test_author_patch_records_apply_with_correct_add_delete_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'old.py').write_text('value = 0\n')
            records = [{'filename': 'old.py', 'status': 'removed', 'patch': '@@ -1 +0,0 @@\n-value = 0'},
                       {'filename': 'new.py', 'status': 'added', 'patch': '@@ -0,0 +1 @@\n+value = 1'}]
            result = subprocess.run(['git', '-C', str(root), 'apply', '-'],
                                    input=github_patch(records), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'old.py').exists())
            self.assertEqual((root / 'new.py').read_text(), 'value = 1\n')
        with self.assertRaises(ValueError):
            github_patch([{'filename': '../escape', 'status': 'added', 'patch': '@@'}])
        with self.assertRaises(ValueError):
            github_patch([{'filename': 'code.py', 'status': 'modified', 'patch': None}])

    def test_both_selector_formats_and_empty_official_regression(self):
        self.assertEqual(selectors('a::test, b::test'), ['a::test', 'b::test'])
        self.assertEqual(selectors('["TestDB"]'), ['TestDB'])
        self.assertEqual(selectors("['TestDB']"), ['TestDB'])
        self.assertEqual(selectors([]), [])
        for value in (None, '', [None]):
            with self.assertRaises(ValueError):
                selectors(value)

    def test_frozen_material_and_qualification_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / 'inputs/smolagents'
            directory.mkdir(parents=True)
            (directory / 'request.txt').write_text('Frozen request')
            spec = {'name': 'smolagents', 'instance_id': 'test', 'base_commit': 'base'}
            manifest = {'instance_id': 'test', 'base_commit': 'base',
                        'files': {'request.txt': digest(directory / 'request.txt')}}
            (directory / 'inputs.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_inputs(directory, spec), manifest)
            with patch('suite_tasks.ROOT', root), patch('suite_tasks.load_spec', return_value=(spec, 'spec-sha')):
                with self.assertRaisesRegex(ValueError, 'no passed environment qualification'):
                    prepare_suite_task({'id': 'smolagents', 'swe_inputs': str(root / 'inputs')}, root / 'output')
                receipt = root / 'tests/reports/qualifications/smolagents.json'
                receipt.parent.mkdir(parents=True)
                receipt.write_text('{"qualified": false}')
                with self.assertRaisesRegex(ValueError, 'failed or stale'):
                    prepare_suite_task({'id': 'smolagents', 'swe_inputs': str(root / 'inputs')}, root / 'output')
            (directory / 'request.txt').write_text('Changed')
            with self.assertRaisesRegex(ValueError, 'input changed'):
                verify_inputs(directory, spec)

    def test_native_reward_requires_consistent_actual_test_results(self):
        record = {'exit_code': 0, 'timed_out': False}
        passed = {'tests': [{'name': 'TestDB', 'status': 'PASSED'}]}
        self.assertEqual(official_status(record, '1', passed, {'TestDB'}), 'pass')
        self.assertEqual(official_status(record, '1', {'tests': []}, {'TestDB'}), 'unknown')
        self.assertEqual(official_status(record, '1', passed, set()), 'unknown')
        self.assertEqual(official_status({'exit_code': 1, 'timed_out': False}, '0',
                                        {'tests': []}, {'TestDB'}), 'fail')
        self.assertEqual(official_status({'exit_code': 0, 'timed_out': True}, '1', passed, {'TestDB'}), 'unknown')

    def test_only_frozen_source_defined_skips_are_accepted(self):
        skip = {'classname': 'tests.example', 'name': 'test_example[unsupported]', 'message': 'unsupported combination'}
        result = {'group': 'PASS_TO_PASS', 'exit_code': 0, 'timed_out': False,
                  'counts': {'tests': 3, 'failures': 0, 'errors': 0, 'skipped': 1, 'xfailed': 0},
                  'skipped_cases': [skip]}
        self.assertEqual(functional_status(result), 'unknown')
        self.assertEqual(functional_status(result, [skip]), 'pass')
        self.assertEqual(result['counts']['skipped'], 1)  # Never count skipped cases as passed.
        result['skipped_cases'] = [{**skip, 'message': 'missing dependency'}]
        self.assertEqual(functional_status(result, [skip]), 'unknown')
        result['skipped_cases'] = [skip]
        result['counts']['tests'] = 1
        self.assertEqual(functional_status(result, [skip]), 'unknown')

    def test_qualification_rejects_a_missing_required_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'inputs/smolagents'
            source.mkdir(parents=True)
            (source / 'inputs.json').write_text('{}')
            (source / 'environment.json').write_text('{}')
            (source / 'validation.json').write_text(json.dumps({'kind': 'pytest',
                'groups': {'FAIL_TO_PASS': ['test_a'], 'PASS_TO_PASS': ['test_b']}}))
            with (patch('preflight_suite.load_spec', return_value=({}, 'hash')),
                  patch('preflight_suite.verify_inputs'),
                  patch('preflight_suite.unpack', side_effect=lambda archive, target: target.mkdir()),
                  patch('preflight_suite.validate_task', return_value=[{'id': 'FAIL_TO_PASS', 'status': 'fail'}])):
                report = qualify('smolagents', root / 'inputs', root / 'evidence')
            self.assertFalse(report['qualified'])


if __name__ == '__main__':
    unittest.main()
