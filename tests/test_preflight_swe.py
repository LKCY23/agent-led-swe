"""Check benchmark patch semantics and environment selection without Docker."""
from pathlib import Path
import tempfile
import unittest

import preflight_swe


SOURCE_FIX = '''diff --git a/feature.py b/feature.py
--- a/feature.py
+++ b/feature.py
@@ -1 +1 @@
-value = 0
+value = 1
'''
TEST_ADD = '''diff --git a/test_feature.py b/test_feature.py
new file mode 100644
--- /dev/null
+++ b/test_feature.py
@@ -0,0 +1 @@
+assert value == 1
'''
MASK = SOURCE_FIX.replace('-value = 0\n+value = 1', '-value = 1\n+value = 0')
TEST_DELETE = '''diff --git a/test_feature.py b/test_feature.py
deleted file mode 100644
--- a/test_feature.py
+++ /dev/null
@@ -1 +0,0 @@
-assert value == 1
'''


class PreflightTest(unittest.TestCase):
    def test_fix_and_mask_produce_separate_learner_control_and_reference(self):
        for mask in (False, True):
            with self.subTest(mask=mask), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source, output = root / 'source', root / 'output'
                source.mkdir()
                output.mkdir()
                (source / 'feature.py').write_text('value = 1\n' if mask else 'value = 0\n')
                if mask:
                    (source / 'test_feature.py').write_text('assert value == 1\n')
                metadata = {'patch': MASK if mask else SOURCE_FIX,
                            'test_patch': TEST_DELETE if mask else TEST_ADD}
                control, reference = preflight_swe.prepare_variants(source, metadata, output, mask)
                self.assertFalse((output / 'learner/test_feature.py').exists())
                self.assertEqual((control / 'feature.py').read_text(), 'value = 0\n')
                self.assertEqual((reference / 'feature.py').read_text(), 'value = 1\n')
                self.assertEqual((control / 'test_feature.py').read_bytes(),
                                 (reference / 'test_feature.py').read_bytes())

    def test_sdk_dependencies_use_project_table_and_existing_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pyproject.toml').write_text('[project]\ndependencies=["openai>=1"]\n'
                                               '[project.optional-dependencies]\nlitellm=["litellm"]\n')
            (root / 'uv.lock').write_text('[[package]]\nname="openai"\nversion="1.81.0"\n'
                                         'source={registry="https://pypi.org/simple"}\n')
            deps, pins = preflight_swe.requirements(root, 'agents-sdk')
            self.assertIn('openai>=1', deps)
            self.assertIn('litellm', deps)
            self.assertIn('openai==1.81.0', pins)

    def test_missing_or_failed_xml_is_not_a_zero_failure_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.xml'
            self.assertIsNone(preflight_swe.xml_counts(path))
            path.write_text('<testsuites><testsuite><testcase><failure/></testcase>'
                            '<testcase><error/></testcase><testcase><skipped/></testcase>'
                            '</testsuite></testsuites>')
            self.assertEqual(preflight_swe.xml_counts(path),
                             {'tests': 3, 'failures': 1, 'errors': 1, 'skipped': 1, 'xfailed': 0})

    def test_expected_xfail_is_distinct_from_missing_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.xml'
            path.write_text('<testsuite><testcase name="a"><skipped type="pytest.xfail"/>'
                            '</testcase><testcase name="b"><skipped/></testcase></testsuite>')
            result = preflight_swe.xml_counts(path)
            self.assertEqual(result['xfailed'], 1)
            self.assertEqual(result['skipped'], 1)

    def test_summary_requires_complete_repeated_evidence(self):
        rows = [{'variant': v, 'repetition': n, 'group': g, 'timed_out': False,
                 'exit_code': 1 if v == 'control' and g == 'FAIL_TO_PASS' else 0,
                 'counts': {'tests': 2, 'errors': 0, 'skipped': 0,
                            'failures': 1 if v == 'control' and g == 'FAIL_TO_PASS' else 0}}
                for v in ('control', 'reference') for n in (1, 2)
                for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')]
        self.assertEqual(preflight_swe.summarize_runs(rows)['test_contract'], 'pass')
        self.assertEqual(preflight_swe.summarize_runs(rows[:-1])['test_contract'], 'unknown')
        rows[-1]['counts']['skipped'] = 1
        self.assertEqual(preflight_swe.summarize_runs(rows)['test_contract'], 'unknown')
        rows[-1]['counts']['skipped'] = 0
        rows[-1]['exit_code'] = 1
        self.assertEqual(preflight_swe.summarize_runs(rows)['test_contract'], 'fail')

    def test_fingerprint_distinguishes_which_test_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.xml', Path(tmp) / 'b.xml'
            a.write_text('<testsuite><testcase name="a"><failure/></testcase>'
                         '<testcase name="b"/></testsuite>')
            b.write_text('<testsuite><testcase name="a"/>'
                         '<testcase name="b"><failure/></testcase></testsuite>')
            self.assertEqual(preflight_swe.xml_counts(a), preflight_swe.xml_counts(b))
            self.assertNotEqual(preflight_swe.xml_fingerprint(a), preflight_swe.xml_fingerprint(b))


if __name__ == '__main__':
    unittest.main()
