import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/hermes-engineering-bridge'


class ResourceTests(unittest.TestCase):
    def test_desktop_entry_uses_local_document_pages(self):
        manifest = json.loads((PLUGIN / 'step.plugin.json').read_text(encoding='utf-8'))
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '0.2.0')
        self.assertEqual(presentation['schemaVersion'], 1)
        desktop = presentation['desktop']
        self.assertEqual(desktop['surface'], 'main-view')
        self.assertEqual(desktop['defaultPage'], 'start')
        self.assertEqual([page['id'] for page in desktop['pages']],
                         ['start', 'setup', 'first-task', 'troubleshooting'])
        for page in desktop['pages']:
            self.assertTrue((PLUGIN / page['document']).is_file(), page['document'])
            self.assertTrue(page['document'].endswith('.md'))
            self.assertNotIn('..', Path(page['document']).parts)
        self.assertTrue((PLUGIN / desktop['icon']['light']).is_file())

    def test_markdown_links_stay_in_the_resource_package(self):
        for path in PLUGIN.rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            for url in re.findall(r'\]\(([^)]+)\)', text):
                if url.startswith('https://'):
                    continue
                target = (path.parent / url.split('#', 1)[0]).resolve()
                self.assertTrue(target.is_relative_to(PLUGIN.resolve()), (path, url))
                self.assertTrue(target.is_file(), (path, url))

    def test_guides_do_not_claim_installation_is_connection(self):
        start = (PLUGIN / 'docs/START.md').read_text(encoding='utf-8')
        setup = (PLUGIN / 'docs/SETUP.md').read_text(encoding='utf-8')
        task = (PLUGIN / 'docs/FIRST_TASK.md').read_text(encoding='utf-8')
        self.assertIn('安装资源包与连接工程桥是不同的步骤', start)
        self.assertIn('不会读取连接凭据', start)
        self.assertIn('当前需要访问权限', setup)
        self.assertIn('可能产生对应服务费用', task)
        self.assertIn('打开本页本身不会开始执行', task)

    def test_entry_does_not_add_an_executable_resource(self):
        manifest = json.loads((PLUGIN / 'step.plugin.json').read_text(encoding='utf-8'))
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        for key in ('entry', 'frontend', 'provision', 'mcpServers'):
            self.assertNotIn(key, manifest)
            self.assertNotIn(key, presentation['desktop'])


if __name__ == '__main__':
    unittest.main()
