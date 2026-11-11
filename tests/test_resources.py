import json
import hashlib
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/hermes-engineering-bridge'


class ResourceTests(unittest.TestCase):
    def test_desktop_entry_uses_local_document_pages(self):
        manifest = json.loads((PLUGIN / 'step.plugin.json').read_text(encoding='utf-8'))
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '0.3.0')
        self.assertEqual(presentation['schemaVersion'], 1)
        self.assertEqual(manifest['name'], 'Hermes x DFSC')
        desktop = presentation['desktop']
        self.assertEqual(desktop['title'], 'Hermes x DFSC')
        self.assertEqual(desktop['surface'], 'main-view')
        self.assertEqual(desktop['connection'], {
            'protocol': 'agent-bridge-v1',
            'guides': {'setup': 'setup', 'firstTask': 'first-task',
                       'troubleshooting': 'troubleshooting'},
        })
        self.assertEqual(desktop['defaultPage'], 'start')
        self.assertEqual([page['id'] for page in desktop['pages']],
                         ['start', 'setup', 'first-task', 'troubleshooting'])
        for page in desktop['pages']:
            self.assertTrue((PLUGIN / page['document']).is_file(), page['document'])
            self.assertTrue(page['document'].endswith('.md'))
            self.assertNotIn('..', Path(page['document']).parts)
        self.assertTrue(set(desktop['connection']['guides'].values())
                        <= {page['id'] for page in desktop['pages']})
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
        self.assertIn('本仓库不提供宿主应用安装器', setup)
        self.assertIn('本项目维护', setup)
        self.assertIn('不是 Hermes 官方组件', setup)
        self.assertIn('此项只验证目录和标记文件', setup)
        self.assertIn('配置有效不证明 companion 已启用或加载', setup)
        self.assertIn('页面不接收令牌', setup)
        self.assertIn('可能产生对应服务费用', task)
        self.assertIn('打开本页本身不会开始执行', task)
        for name in ('START', 'SETUP', 'FIRST_TASK', 'TROUBLESHOOTING'):
            text = (PLUGIN / f'docs/{name}.md').read_text(encoding='utf-8')
            self.assertNotIn('当前需要访问权限', text, name)
            self.assertNotIn('配套项目当前需要访问权限', text, name)

    def test_requirements_are_declared_without_installing_or_making_feishu_required(self):
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        requirements = presentation['requirements']
        self.assertEqual(set(requirements), {'dfsc', 'external'})
        self.assertEqual(requirements['dfsc'], '>=0.6.0')
        external = requirements['external']
        self.assertEqual([item['name'] for item in external], [
            'Hermes Agent', 'Hermes x DFSC companion', 'DFSC Agent Bridge 配套宿主',
            '飞书工程授权通道',
        ])
        for index, item in enumerate(external):
            self.assertTrue(set(item) <= {'name', 'description', 'url', 'optional'})
            self.assertEqual(item.get('optional', False), index == 3)
            parsed = urlparse(item['url'])
            self.assertEqual(parsed.scheme, 'https')
            self.assertIn(parsed.netloc, ('github.com', 'open.feishu.cn'))
            self.assertIsNone(parsed.username)
            self.assertIsNone(parsed.password)
            self.assertFalse(parsed.query)
            self.assertFalse(parsed.fragment)
        self.assertIn('版本号达标不证明', external[2]['description'])
        self.assertIn('安装资源与只读检查无需飞书', external[0]['description'])
        self.assertIn('新工程授权仍需已配置的飞书通道', external[0]['description'])
        self.assertIn('发起新工程委托的授权入口', external[3]['description'])
        self.assertIn('安装与只读查看不需要', external[3]['description'])
        task = (PLUGIN / 'docs/FIRST_TASK.md').read_text(encoding='utf-8')
        self.assertIn('安装资源与只读检查无需飞书', task)
        self.assertIn('只从已核验的飞书主人消息', task)
        self.assertIn('不是所有渠道的通用能力', task)

    def test_onboarding_matches_the_four_evidence_cards(self):
        for relative in ('README.md', 'docs/START.md', 'docs/SETUP.md',
                         'commands/hermes-bridge-help.md'):
            text = (PLUGIN / relative).read_text(encoding='utf-8')
            for label in ('身份目录', 'companion 配置', 'Bridge 配对', '授权目录'):
                self.assertIn(label, text, (relative, label))
        start = (PLUGIN / 'docs/START.md').read_text(encoding='utf-8')
        self.assertIn('不证明 Hermes 正在运行', start)
        self.assertIn('不证明 companion 已加载', start)
        self.assertIn('只证明本次身份、目录和摘要查询成功', start)
        self.assertIn('不证明可以派工', start)

    def test_entry_does_not_add_an_executable_resource(self):
        manifest = json.loads((PLUGIN / 'step.plugin.json').read_text(encoding='utf-8'))
        presentation = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))
        for key in ('entry', 'frontend', 'provision', 'mcpServers'):
            self.assertNotIn(key, manifest)
            self.assertNotIn(key, presentation['desktop'])

    def test_guides_distinguish_quick_status_from_full_workspace(self):
        for relative in ('README.md', 'docs/START.md', 'commands/hermes-bridge-help.md'):
            text = (PLUGIN / relative).read_text(encoding='utf-8')
            self.assertIn('打开完整工作台', text, relative)
            self.assertIn('不切换当前聊天' if relative != 'docs/START.md' else '不离开当前聊天',
                          text, relative)
        start = (PLUGIN / 'docs/START.md').read_text(encoding='utf-8')
        self.assertIn('最多 5 项任务', start)
        self.assertIn('不是实时在线状态', start)

    def test_guides_explicitly_separate_unreleased_generic_and_legacy_modes(self):
        for relative in ('README.md', 'docs/START.md', 'docs/SETUP.md', 'docs/FIRST_TASK.md',
                         'docs/TROUBLESHOOTING.md', 'commands/hermes-bridge-help.md'):
            text = (PLUGIN / relative).read_text(encoding='utf-8')
            with self.subTest(relative=relative):
                self.assertIn('dfsc-external-v1', text)
                self.assertIn('尚未发布', text)
                self.assertIn('外部 Agent', text)
                self.assertIn('--desktop-connector', text)
                self.assertIn('独立 profile', text)
                self.assertIn('旧', text)
                self.assertIn('本机', text)
                self.assertIn('completed', text)
                self.assertNotIn('普通 DFSC 主线目前不内置配套 Bridge 服务', text)
        setup = (PLUGIN / 'docs/SETUP.md').read_text(encoding='utf-8')
        self.assertIn('不加 `--pair`', setup)
        self.assertIn('不手写 token', setup)
        self.assertIn('不会自动重启网关', setup)
        self.assertIn('--replace-connection', setup)
        self.assertIn('通用宿主当前每页最多 20 项', setup)
        self.assertIn('没有开放翻页参数', setup)
        requirements = json.loads((PLUGIN / 'dfsc.plugin.json').read_text(encoding='utf-8'))['requirements']['external']
        self.assertIn('仅旧专版模式', requirements[0]['description'])
        self.assertIn('新增通用模式不依赖飞书', requirements[0]['description'])
        self.assertIn('dfsc-external-v1', requirements[2]['description'])
        self.assertIn('尚未发布', requirements[2]['description'])
        self.assertIn('仅旧专版模式', requirements[3]['description'])
        self.assertTrue(requirements[3]['optional'])


if __name__ == '__main__':
    unittest.main()
