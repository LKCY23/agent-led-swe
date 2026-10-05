"""Exercise package link validation in disposable copies, without model calls."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import check_package


class PackageLinksTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'agent-led-swe'
        self.root.mkdir()
        source = check_package.ROOT
        for directory in ('references', 'assets', 'agents', '.claude-plugin'):
            shutil.copytree(source / directory, self.root / directory)
        shutil.copyfile(source / 'SKILL.md', self.root / 'SKILL.md')

    def validate(self):
        with patch.object(check_package, 'ROOT', self.root), redirect_stdout(io.StringIO()):
            check_package.main()

    def test_current_package(self):
        self.validate()

    def test_unicode_duplicate_and_same_file_anchors(self):
        (self.root / 'target.md').write_text(
            '# 本地测试环境\n## **Check** `result`\n## Check result\n'
            '[同文件](#check-result-1)\n')
        (self.root / 'links.md').write_text(
            '[中文](target.md#本地测试环境)\n'
            '[编码](target.md#%E6%9C%AC%E5%9C%B0%E6%B5%8B%E8%AF%95%E7%8E%AF%E5%A2%83)\n'
            '[重复标题](target.md#check-result-1)\n')
        self.validate()

    def test_removed_section_is_rejected(self):
        (self.root / 'target.md').write_text('# New heading\n')
        (self.root / 'links.md').write_text('[旧标题](target.md#old-heading)\n')
        with self.assertRaisesRegex(AssertionError, 'Broken fragment'):
            self.validate()

    def test_missing_same_file_section_is_rejected(self):
        (self.root / 'links.md').write_text('# Existing\n[不存在](#missing)\n')
        with self.assertRaisesRegex(AssertionError, 'Broken fragment'):
            self.validate()

    def test_code_examples_are_not_sections_or_live_links(self):
        target = self.root / 'target.md'
        target.write_text('```markdown\n# Example heading\n[示例](absent.md#x)\n```\n')
        self.validate()
        (self.root / 'links.md').write_text('[不是章节](target.md#example-heading)\n')
        with self.assertRaisesRegex(AssertionError, 'Broken fragment'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
