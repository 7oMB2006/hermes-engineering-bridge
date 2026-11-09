import json
import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/hermes-engineering-bridge'


class ResourceTests(unittest.TestCase):
    def test_desktop_entry_uses_local_document_pages(self):
        manifest = json.loads((PLUGIN / 'step.plugin.json').read_text(encoding='utf-8'))
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '0.3.0')
        self.assertEqual(presentation['schemaVersion'], 1)
        desktop = presentation['desktop']
        self.assertEqual(desktop['surface'], 'main-view')
        self.assertEqual(desktop['connection'], {'protocol': 'agent-bridge-v1'})
        self.assertEqual(desktop['defaultPage'], 'start')
        self.assertEqual([page['id'] for page in desktop['pages']],
                         ['start', 'setup', 'first-task', 'troubleshooting'])
        for page in desktop['pages']:
            self.assertTrue((PLUGIN / page['document']).is_file(), page['document'])
            self.assertTrue(page['document'].endswith('.md'))
            self.assertNotIn('..', Path(page['document']).parts)
        self.assertEqual(manifest['icon'], 'icon.png')
        icon = (PLUGIN / manifest['icon']).read_bytes()
        self.assertLessEqual(len(icon), 128 * 1024)
        self.assertEqual(icon[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(icon[12:16], b'IHDR')
        self.assertEqual(int.from_bytes(icon[16:20], 'big'), 256)
        self.assertEqual(int.from_bytes(icon[20:24], 'big'), 256)
        self.assertEqual(hashlib.sha256(icon).hexdigest(),
                         '94d7d38c86a760ac89095dc3bed7eb26da2d6eb60903345797e43e374cd9204c')

    def test_toolbar_icons_are_separate_native_17px_theme_variants(self):
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        icons = presentation['desktop']['icon']
        self.assertEqual(icons, {
            'light': 'icons/toolbar-light.png',
            'dark': 'icons/toolbar-dark.png',
        })
        variants = []
        for path in icons.values():
            icon = (PLUGIN / path).read_bytes()
            self.assertLessEqual(len(icon), 128 * 1024)
            self.assertEqual(icon[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(icon[12:16], b'IHDR')
            self.assertEqual(int.from_bytes(icon[16:20], 'big'), 17)
            self.assertEqual(int.from_bytes(icon[20:24], 'big'), 17)
            variants.append(icon)
        self.assertNotEqual(*variants)
        self.assertEqual([hashlib.sha256(icon).hexdigest() for icon in variants], [
            '945359dc44c52b65b9ccd7088b0ae2d6be93a706bfd0e7fe5f2c7399d1cc0593',
            '5fb10ee50d4bb49c37b9c24c068d646c613ca9fa74f076275a031e2c87ee51c0',
        ])

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
        self.assertIn('首次打开不会自动寻找 profile 或连接凭据', start)
        self.assertIn('页面只接收身份、可见目录和任务摘要，不接收令牌', start)
        self.assertIn('不证明 companion 已加载', start)
        self.assertIn('不内置 Agent Bridge 服务', setup)
        self.assertIn('首批 50 条', setup)
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
