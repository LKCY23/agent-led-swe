"""Continuation inputs preserve prior work without leaking private verifier files."""
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import cattrs_repair_task as task


class ContinuationInputsTest(unittest.TestCase):
    def test_public_bundle_preserves_documents_and_tests_but_removes_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, upstream, output = (root / n for n in ('source', 'upstream', 'output'))
            source.mkdir()
            upstream.mkdir()
            for name in ('docs/partial.md', 'tests/test_partial.py', 'src/cattrs/partial.py',
                         '.pytest_cache/v/cache/nodeids'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('existing material')
            for name in ('environment.json', 'inputs.json', 'user-requirements.md', 'test.patch'):
                (upstream / name).write_text('{}')
            before = task.source_hash(source)
            with patch.object(task, 'SNAPSHOT_HASH', before), patch.object(task.cattrs_task, 'verify_inputs'):
                task.prepare(upstream, source, output)
                task.verify_inputs(output)
            with tarfile.open(output / 'public.tar.gz') as archive:
                names = archive.getnames()
            self.assertIn('docs/partial.md', names)
            self.assertIn('tests/test_partial.py', names)
            self.assertFalse(any(n.startswith('.pytest_cache') for n in names))
            self.assertNotIn('test.patch', names)
            self.assertNotIn('reference.patch', names)
            self.assertEqual(task.source_hash(source), before)

    def test_changed_source_cannot_silently_replace_selected_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(task.cattrs_task, 'verify_inputs'):
                with self.assertRaisesRegex(ValueError, 'selected real artifact'):
                    task.prepare(root, root, root / 'output')
            self.assertFalse((root / 'output').exists())
