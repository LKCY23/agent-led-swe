"""Check case migration and runner evidence boundaries without model calls."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_smoke


class SmokeCasesTest(unittest.TestCase):
    def test_migrated_requests_and_fixtures_are_unchanged(self):
        migration = json.loads((run_smoke.ROOT / 'tests/case-migration-2026-10-05.json').read_text())
        self.assertLessEqual(set(migration['input_hashes']), set(run_smoke.case_ids()))
        for case_id, expected in migration['input_hashes'].items():
            with self.subTest(case=case_id):
                case = run_smoke.load_case(case_id)
                self.assertEqual(run_smoke.case_input_hash(case), expected)

    def test_undefined_case_cannot_run(self):
        with self.assertRaisesRegex(ValueError, 'Unknown runnable case'):
            run_smoke.load_case('not-defined')

    def test_unsafe_fixture_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_smoke, 'CASE_DIR', Path(tmp)):
            for name in ('../outside.txt', '/tmp/outside.txt', '.', ''):
                with self.subTest(path=name):
                    case = {'id': 'T1', 'request': 'Task', 'files': {name: 'text'},
                            'acceptance': ['Expected behavior']}
                    (Path(tmp) / 'T1.json').write_text(json.dumps(case))
                    with self.assertRaisesRegex(ValueError, 'Invalid fixture'):
                        run_smoke.load_case('T1')

    def test_acceptance_missing_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_smoke, 'CASE_DIR', Path(tmp)):
            (Path(tmp) / 'T1.json').write_text(json.dumps(
                {'id': 'T1', 'request': 'Task', 'files': {}, 'acceptance': []}))
            with self.assertRaisesRegex(ValueError, 'Missing acceptance'):
                run_smoke.load_case('T1')

    def test_runner_freezes_case_and_keeps_grading_out_of_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            case_dir = root / 'cases'
            case_dir.mkdir()
            case = {'id': 'T1', 'request': 'Perform the requested task.',
                    'files': {'input.txt': 'User input'},
                    'acceptance': ['GRADER_ONLY_SENTINEL']}
            case_path = case_dir / 'T1.json'
            case_path.write_text(json.dumps(case))
            original_hash = hashlib.sha256(case_path.read_bytes()).hexdigest()
            (root / 'SKILL.md').write_text('Test skill')
            capture = root / 'capture.py'
            capture.touch()
            binary = root / 'codex-test'
            binary.touch(mode=0o700)

            def capture_stub(argv, **kwargs):
                self.assertEqual(argv[0], sys.executable)
                fixture = Path(argv[argv.index('--cwd') + 1])
                prompt = Path(argv[argv.index('--stdin-file') + 1]).read_text()
                self.assertIn(case['request'], prompt)
                self.assertNotIn('GRADER_ONLY_SENTINEL', prompt)
                self.assertEqual([p.name for p in fixture.iterdir()], ['input.txt'])
                self.assertEqual((fixture / 'input.txt').read_text(), 'User input')
                case_path.write_text('{}')  # Evidence must retain the executed definition.
                return subprocess.CompletedProcess(argv, 23, '', '')

            argv = ['run_smoke.py', 'T1', '--capture', str(capture), '--codex-bin', str(binary)]
            with (patch.object(run_smoke, 'ROOT', root),
                  patch.object(run_smoke, 'CASE_DIR', case_dir),
                  patch.dict('os.environ', {'CODEX_HOME': str(root / 'config')}),
                  patch.object(sys, 'argv', argv),
                  patch.object(run_smoke.subprocess, 'run', side_effect=capture_stub),
                  patch.object(run_smoke.subprocess, 'check_output', return_value='test-cli\n'),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(run_smoke.main(), 23)

            evidence = next((root / 'tests/runs').iterdir())
            manifest = json.loads((evidence / 'manifest.json').read_text())
            self.assertEqual(manifest['case_definition']['sha256'], original_hash)
            self.assertEqual(json.loads((evidence / 'case.json').read_text()), case)
            self.assertEqual(manifest['fixture_before'], manifest['fixture_after'])


if __name__ == '__main__':
    unittest.main()
