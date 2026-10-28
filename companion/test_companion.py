import importlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

# Reuse the loaded package fixture, never the user's installed plugin.
import test_plugin
from test_plugin import plugin
configuration = importlib.import_module(plugin.__name__ + '.configuration')
scope = importlib.import_module(plugin.__name__ + '.scope')
client = importlib.import_module(plugin.__name__ + '.client')
installer = importlib.import_module(plugin.__name__ + '.install_profile')


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.config = configuration.CompanionConfig('h-xiexie', 'H蟹蟹', self.root, (self.project,), '金融研究与 XDJ 工程')
        self.bridge = scope.ScopedBridge(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def task(self, agent='h-xiexie', cwd=None):
        return {'id': 'task', 'origin': {'agentProfile': agent}, 'cwd': str(cwd or self.project)}

    def test_configuration_roundtrip_and_no_unconfigured_profile(self):
        self.assertEqual(configuration.CompanionConfig.from_dict(self.config.to_dict()), self.config)
        with self.assertRaises(FileNotFoundError):
            configuration.CompanionConfig.load(self.root)
        for bad in [{'agentId': '../other'}, {'workspaceRoots': ['relative']}, {'bridgeRoot': 'relative'}, {'displayName': 'bad\nname'}, {'schemaVersion': 99}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                configuration.CompanionConfig.from_dict({**self.config.to_dict(), **bad})

    def test_registration_requires_profile_opt_in_and_preserves_role(self):
        class Context:
            def __init__(self):
                self.tools = []
                self.hooks = []
            def on_unload(self, callback): self.unload = callback
            def register_hook(self, name, callback): self.hooks.append(name)
            def register_tool(self, **kwargs): self.tools.append(kwargs)
            def register_system_prompt_section(self, name, callback): self.instructions = callback
            def register_skill(self, *args): pass
        ctx = Context()
        modules = {'hermes_constants': NS(get_hermes_home=lambda: self.root), 'dotenv': NS(dotenv_values=lambda path: {})}
        with patch.dict(sys.modules, modules), patch.object(plugin.Integration, 'start'):
            plugin.register(ctx)
            self.assertFalse(ctx.tools)
            (self.root / 'dfsc-bridge').mkdir()
            (self.root / 'dfsc-bridge/config.json').write_text(json.dumps(self.config.to_dict()))
            plugin.register(ctx)
        self.assertEqual(ctx.tools[0]['name'], 'dfsc_engineering')
        self.assertIn('H蟹蟹', ctx.tools[0]['schema']['description'])
        self.assertTrue(ctx.instructions().startswith('金融研究与 XDJ 工程'))
        self.assertEqual(len(ctx.hooks), 3)
        ctx.unload()

    def test_host_identity_limits_match_companion_configuration(self):
        base = self.config.to_dict()
        for ident in ['a', '0', '0_agent', 'h_xiexie', 'x' * 64]:
            with self.subTest(ident=ident):
                self.assertEqual(configuration.CompanionConfig.from_dict({**base, 'agentId': ident}).agent_id, ident)
        for ident in ['con', 'prn', 'aux', 'nul', 'com1', 'com9', 'lpt1', 'lpt9', '_a', '-a', 'X', 'x' * 65]:
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                configuration.CompanionConfig.from_dict({**base, 'agentId': ident})
        self.assertEqual(configuration.CompanionConfig.from_dict({**base, 'displayName': 'x' * 100}).display_name, 'x' * 100)
        for display in ['x' * 101, '\U0001f980' * 51, 'bad\x7fname']:
            with self.subTest(display=display), self.assertRaises(ValueError):
                configuration.CompanionConfig.from_dict({**base, 'displayName': display})
        # Raw input count is checked before deduplication, just like human.agents.
        configuration.CompanionConfig.from_dict({**base, 'workspaceRoots': [str(self.project)] * 32})
        with self.assertRaises(ValueError):
            configuration.CompanionConfig.from_dict({**base, 'workspaceRoots': [str(self.project)] * 33})

    def test_windows_default_uses_appdata_not_mac_path(self):
        with patch.object(configuration.sys, 'platform', 'win32'), patch.dict(configuration.os.environ, {'APPDATA': str(self.root)}):
            self.assertEqual(configuration.default_bridge_root(), self.root / 'DFSC Hermes/agent-bridge')

    def test_scope_blocks_traversal_prefix_and_symlink(self):
        escape = self.project / 'escape'
        try:
            escape.symlink_to(self.root, target_is_directory=True)
        except OSError:
            escape = None  # Windows without symlink privilege still exercises canonical traversal.
        paths = [str(self.project / '../outside'), str(self.project) + '-other', 'relative']
        if escape:
            paths.append(str(escape / 'outside'))
        for path in paths:
            with self.subTest(path=path), patch.object(scope, 'transport_call') as rpc:
                with self.assertRaises(ValueError):
                    self.bridge.call(self.config.credentials, 'task.create', {'cwd': path})
                rpc.assert_not_called()

    def test_legacy_owner_requires_exact_profile_session_prefix(self):
        keke = configuration.CompanionConfig('h-keke', 'H刻刻', self.root)
        base = {'cwd': str(self.project), 'origin': {'sessionKey': 'agent:h-keke:feishu:dm:chat'}}
        self.assertTrue(keke.owns(base))
        self.assertFalse(self.config.owns(base))
        self.assertFalse(keke.owns({**base, 'origin': {'sessionKey': 'agent:h-keke-other:chat'}}))
        self.assertFalse(keke.owns({**base, 'origin': {'agentProfile': 'h-xiexie', 'sessionKey': base['origin']['sessionKey']}}))

    def test_cross_agent_and_outside_task_calls_block_before_mutation(self):
        for method in ['run.submit', 'approval.respond', 'session.archive', 'session.restore', 'human.approval']:
            for task in [self.task(agent='h-keke'), self.task(cwd=self.root)]:
                with self.subTest(method=method, task=task), patch.object(scope, 'transport_call', return_value=task) as rpc:
                    with self.assertRaises(scope.ForeignTaskError):
                        self.bridge.call(self.config.credentials, method, {'taskId': 'task'}, human=method.startswith('human.'))
                    self.assertEqual([c.args[1] for c in rpc.call_args_list], ['task.get'])

    def test_owned_task_forwards_only_credential_bound_identity(self):
        with patch.object(scope, 'transport_call', side_effect=[self.task(), {'archived': True}]) as rpc:
            self.assertTrue(self.bridge.call(self.config.credentials, 'session.archive', {'taskId': 'task'})['archived'])
            for call in rpc.call_args_list:
                self.assertEqual(call.args[0], self.config.credentials)
                self.assertEqual(call.kwargs['agent_id'], 'h-xiexie')
        with self.assertRaises(ValueError):
            self.bridge.call(self.root, 'task.list')

    def test_grants_use_real_config_identity_and_model_cannot_issue_them(self):
        with patch.object(scope, 'transport_call', side_effect=lambda *args, **kw: args[2]) as rpc:
            result = self.bridge.call(self.config.credentials, 'human.grant', {'origin': {'chatId': 'c', 'userId': 'u', 'agentProfile': 'spoof'}}, human=True)
            self.assertEqual(result['origin']['agentProfile'], 'h-xiexie')
            self.assertEqual(result['origin']['agentDisplayName'], 'H蟹蟹')
            with self.assertRaises(ValueError):
                self.bridge.call(self.config.credentials, 'human.grant')

    def test_list_pagination_filters_before_slicing(self):
        pages = [[self.task('h-keke') for _ in range(50)], [self.task()]]
        with patch.object(scope, 'transport_call', side_effect=pages):
            self.assertEqual(self.bridge.call(self.config.credentials, 'task.list'), [self.task()])

    def test_capabilities_roots_intersect_and_wrong_identity_fails(self):
        with patch.object(scope, 'transport_call', return_value={'roots': [str(self.root), '/outside'], 'agentId': 'h-xiexie'}):
            self.assertEqual(self.bridge.call(self.config.credentials, 'system.capabilities')['roots'], [str(self.project)])
        with patch.object(scope, 'transport_call', return_value={'roots': [], 'agentId': 'h-keke'}), self.assertRaises(ValueError):
            self.bridge.call(self.config.credentials, 'system.capabilities')

    def test_pair_preserves_other_agents_and_uses_revision(self):
        current = {'agents': [{'id': 'h-keke', 'displayName': 'H刻刻', 'roots': [str(self.root)]}], 'revision': 5}
        with patch.object(installer, 'call', side_effect=[current, {'revision': 6}]) as rpc:
            installer.pair(self.config)
            self.assertEqual(rpc.call_args.args[2]['expectedRevision'], 5)
            self.assertEqual([a['id'] for a in rpc.call_args.args[2]['agents']], ['h-keke', 'h-xiexie'])
            self.assertTrue(rpc.call_args.kwargs['human'])

    def test_install_preserves_delivery_credentials_and_other_settings(self):
        (self.root / 'config.yaml').write_text(json.dumps({'model': 'existing', 'plugins': {'enabled': ['other']}}))
        data = self.root / 'dfsc-bridge'
        data.mkdir()
        (data / 'delivery.json').write_text('{"cursor": 123}')
        (self.root / '.env').write_text('PRIVATE_FIXTURE=unchanged\n')
        fake_yaml = NS(safe_load=json.loads, safe_dump=lambda value, **kw: json.dumps(value))
        with patch.dict(sys.modules, {'hermes_yaml': fake_yaml}):
            result = installer.install(self.root, self.config, source=Path(__file__).parent)
        self.assertTrue(Path(result['backup']).is_dir())
        self.assertEqual((data / 'delivery.json').read_text(), '{"cursor": 123}')
        self.assertEqual((self.root / '.env').read_text(), 'PRIVATE_FIXTURE=unchanged\n')
        settings = json.loads((self.root / 'config.yaml').read_text())
        self.assertEqual(settings['model'], 'existing')
        self.assertEqual(settings['plugins']['enabled'], ['other', 'hermes-dfsc'])
        self.assertEqual(configuration.CompanionConfig.load(self.root), self.config)


class TransportTests(unittest.TestCase):
    def test_loopback_transport_and_role_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(('127.0.0.1', 0));listener.listen(1)
            port = listener.getsockname()[1]
            seen = []
            def server():
                connection, _ = listener.accept()
                with connection:
                    seen.append(json.loads(connection.recv(4096)))
                    connection.sendall(b'{"ok":true,"result":{"agentId":"h-xiexie"}}\n')
            thread = threading.Thread(target=server);thread.start()
            descriptor = {'version': 1, 'transport': 'tcp', 'host': '127.0.0.1', 'port': port, 'token': 'fixture', 'agentId': 'h-xiexie', 'role': 'model', 'displayName': 'H蟹蟹 🦀'}
            path = Path(directory) / 'model.json';path.write_bytes(json.dumps(descriptor, ensure_ascii=False).encode('utf-8'))
            read_text = Path.read_text
            def local_read(target, encoding=None, errors=None):
                return read_text(target, encoding=encoding or 'ascii', errors=errors)
            try:
                with patch.object(Path, 'read_text', local_read):
                    result = client.call(directory, 'system.capabilities', agent_id='h-xiexie')
                self.assertEqual(result['agentId'], 'h-xiexie')
                self.assertEqual(seen[0]['method'], 'system.capabilities')
                for changed in [{'host': '0.0.0.0'}, {'host': 'example.com'}, {'agentId': 'h-keke'}, {'role': 'human'}]:
                    path.write_text(json.dumps({**descriptor, **changed}))
                    with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                        client.call(directory, 'system.capabilities', agent_id='h-xiexie')
            finally:
                thread.join(1);listener.close()


class EventCursorTests(unittest.TestCase):
    setUp = test_plugin.PluginTests.setUp
    tearDown = test_plugin.PluginTests.tearDown

    def test_durable_unicode_state_does_not_depend_on_platform_locale(self):
        # Windows can use a non-UTF-8 text locale. Reconnection must preserve
        # actual Feishu/card content rather than failing or changing its text.
        state = {**self.integration.state, 'unicodeFixture': 'H蟹蟹 · 工程 🦀'}
        self.integration.state_path.write_bytes(json.dumps(state, ensure_ascii=False).encode('utf-8'))
        read_text, write_text = Path.read_text, Path.write_text
        def local_read(path, encoding=None, errors=None):
            return read_text(path, encoding=encoding or 'ascii', errors=errors)
        def local_write(path, data, encoding=None, errors=None, newline=None):
            return write_text(path, data, encoding=encoding or 'ascii', errors=errors, newline=newline)
        with patch.object(Path, 'read_text', local_read), patch.object(Path, 'write_text', local_write):
            restored = plugin.Integration(self.ctx, self.integration.home, {}, self.integration.configuration)
            self.assertEqual(restored.state['unicodeFixture'], state['unicodeFixture'])
            restored.save()
        self.assertEqual(json.loads(self.integration.state_path.read_bytes().decode('utf-8'))['unicodeFixture'], state['unicodeFixture'])

    def test_filtered_empty_batches_advance_host_cursor(self):
        self.ctx._manager.has_gateway_message_injector = True
        waits = []
        def rpc(root, method, params=None, **kwargs):
            if method == 'task.list':
                return []
            waits.append(params['cursor'])
            if len(waits) == 2:
                self.integration.halt.set()
                raise RuntimeError('done')
            return {'events': [], 'nextCursor': 71, 'historyGeneration': 0}
        with patch.object(self.integration, 'rpc', side_effect=rpc):
            self.integration.consume()
        self.assertEqual(waits, [0, 71])
        self.assertEqual(json.loads(self.integration.state_path.read_text())['cursor'], 71)

    def test_upgrade_drops_foreign_pending_wakes_before_injection(self):
        self.ctx._manager.has_gateway_message_injector = True
        self.integration.state['pendingWakes'] = {'foreign': {'taskId': 'foreign', 'sessionKey': 'other', 'content': 'do not inject', 'tries': 0, 'last': 0}}
        injected = []
        self.ctx.inject_message = lambda *args, **kwargs: injected.append(args)
        def rpc(root, method, params=None, **kwargs):
            if method == 'task.list':
                return []
            self.integration.halt.set()
            raise RuntimeError('done')
        with patch.object(self.integration, 'rpc', side_effect=rpc):
            self.integration.consume()
        self.assertFalse(injected)
        self.assertFalse(self.integration.state['pendingWakes'])
