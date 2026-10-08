"""Frozen task inputs must retain their identity and content before execution."""
import json
from pathlib import Path
import tempfile
import unittest

from evaluation_runtime import file_hashes
from run_collaboration import task_adapter
from tomlkit_task import BASE_COMMIT, BENCH_COMMIT, TASK_ID, verify_inputs


class TomlkitInputsTest(unittest.TestCase):
    def test_modified_private_or_public_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('public.tar.gz', 'user-requirements.md', 'test.patch'):
                (root / name).write_text('frozen')
            (root / 'inputs.json').write_text(json.dumps({
                'id': TASK_ID, 'base_commit': BASE_COMMIT, 'benchmark_commit': BENCH_COMMIT,
                'files': file_hashes(root)}))
            verify_inputs(root)
            for name in ('public.tar.gz', 'user-requirements.md', 'test.patch'):
                with self.subTest(name=name):
                    (root / name).write_text('changed')
                    with self.assertRaisesRegex(ValueError, 'inputs changed'):
                        verify_inputs(root)
                    (root / name).write_text('frozen')

    def test_task_selector_and_identity(self):
        self.assertEqual(task_adapter('tomlkit').TASK_ID, TASK_ID)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'inputs.json').write_text(json.dumps({
                'id': 'another-task', 'base_commit': BASE_COMMIT,
                'benchmark_commit': BENCH_COMMIT, 'files': {}}))
            with self.assertRaisesRegex(ValueError, 'task identity'):
                verify_inputs(root)
