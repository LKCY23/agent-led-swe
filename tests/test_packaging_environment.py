"""Qualification and local-source audit failures prevent a packaging rollout."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from packaging_environment import clean
import task_adapters


class PackagingEnvironmentTest(unittest.TestCase):
    def test_implementation_or_archive_is_not_clean(self):
        self.assertTrue(clean({'implementation_directories': [], 'package_archives': []}))
        for audit in ({'implementation_directories': ['/opt/vendor/packaging'], 'package_archives': []},
                      {'implementation_directories': [], 'package_archives': ['/tmp/packaging.whl']}):
            self.assertFalse(clean(audit))

    def test_missing_or_stale_executor_qualification_stops_before_source_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tests/cases/swe').mkdir(parents=True)
            (root / 'tests/reports').mkdir()
            spec = {'name': 'packaging'}
            (root / 'tests/cases/swe/packaging.json').write_text(json.dumps(spec))
            (root / 'tests/reports/swe-preflight-2026-10-05.json').write_text(json.dumps({'cases': [
                {'name': 'packaging', 'spec': spec, 'image_id': 'verifier-image', 'summary': {'test_contract': 'pass'}}]}))
            with patch.object(task_adapters, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'paused'):
                    task_adapters.prepare_task({'id': 'packaging', 'swe_inputs': 'unused'}, root / 'missing')
                (root / 'tests/reports/packaging-execution-environment-2026-10-06.json').write_text(json.dumps({
                    'qualified': True, 'spec': spec, 'base_verifier_image': 'different-image'}))
                with self.assertRaisesRegex(ValueError, 'stale'):
                    task_adapters.prepare_task({'id': 'packaging', 'swe_inputs': 'unused'}, root / 'stale')
