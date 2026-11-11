import importlib
import json
from pathlib import Path
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

import test_plugin

plugin = test_plugin.plugin
external = importlib.import_module(plugin.__name__ + '.external')
configuration = importlib.import_module(plugin.__name__ + '.configuration')
installer = importlib.import_module(plugin.__name__ + '.install_profile')


class ExternalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.agent_id = 'external-fixture'
        self.config_value = {
            'schemaVersion': 1, 'protocol': external.PROTOCOL, 'agentId': self.agent_id,
            'displayName': '工程助手', 'bridgeRoot': str(self.root),
            'workspaceRoots': [str(self.project)],
        }
        self.config = configuration.CompanionConfig.from_dict(self.config_value)
        self.config_file = self.root / 'connector.json'
        self.config_file.write_text(json.dumps(self.config_value), encoding='utf-8')
        self.credentials = self.root / 'agents' / self.agent_id
        self.credentials.mkdir(parents=True)
        self.requests = []
        self.responses = {}
        self.caps = {'protocol': external.PROTOCOL, 'agentId': self.agent_id,
                     'roots': [str(self.project)], 'methods': list(external.METHODS)}
        test = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request = json.loads(self.rfile.readline(65537))
                test.requests.append(request)
                result = test.caps if request['method'] == 'system.capabilities' else test.task()
                if request['method'] == 'task.list':
                    result = [test.task()]
                reply = test.responses.get(request['method'], {'ok': True, 'result': result})
                self.wfile.write(reply if isinstance(reply, bytes) else json.dumps(reply).encode('utf-8') + b'\n')

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True

        self.server = Server(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.descriptor = {
            'version': 1, 'protocol': external.PROTOCOL, 'agentId': self.agent_id, 'role': 'model',
            'transport': 'tcp', 'host': '127.0.0.1', 'port': self.server.server_address[1],
            'token': 'private-credential-fixture',
        }
        self.write_descriptor()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def write_descriptor(self, **changes):
        (self.credentials / 'model.json').write_text(json.dumps({**self.descriptor, **changes}), encoding='utf-8')

    def task(self, **changes):
        return {'id': 'task-fixture', 'title': 'One task', 'cwd': str(self.project),
                'origin': {'agentProfile': self.agent_id}, 'phase': 'completed',
                'sessionId': 'native-session', 'runtimeId': 'native-runtime',
                'summary': 'Native turn ended; tests unverified.', **changes}

    def test_protocol_is_explicit_and_legacy_roundtrip_unchanged(self):
        self.assertEqual(self.config.protocol, external.PROTOCOL)
        self.assertEqual(configuration.CompanionConfig.from_dict(self.config.to_dict()), self.config)
        legacy = configuration.CompanionConfig('legacy', 'Legacy', self.root)
        self.assertNotIn('protocol', legacy.to_dict())
        self.assertIsNone(configuration.CompanionConfig.from_dict(legacy.to_dict()).protocol)
        for change in [{'protocol': 'auto'}, {'bridgeRoot': None}, {'workspaceRoots': []}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                configuration.CompanionConfig.from_dict({**self.config_value, **change})

    def test_public_import_accepts_only_nonsecret_strict_shape(self):
        self.assertEqual(external.load_connector(self.config_file), self.config)
        for changes in [{'token': 'never-import'}, {'protocol': None}, {'bridgeRoot': 'relative'},
                        {'workspaceRoots': [str(self.root / 'missing')]}, {'human': {'token': 'never-read'}}]:
            self.config_file.write_text(json.dumps({**self.config_value, **changes}), encoding='utf-8')
            with self.subTest(changes=changes), self.assertRaises(external.ExternalError):
                external.load_connector(self.config_file)

    def test_duplicate_keys_and_oversized_files_fail(self):
        self.config_file.write_text('{"schemaVersion":1,"schemaVersion":1}', encoding='utf-8')
        with self.assertRaises(external.ExternalError):
            external.load_connector(self.config_file)
        self.config_file.write_bytes(b' ' * (external.MAX_FILE + 1))
        with self.assertRaises(external.ExternalError):
            external.load_connector(self.config_file)

    def test_external_registration_never_reads_env_or_starts_legacy_hooks(self):
        class Context:
            def __init__(self): self.tools, self.hooks, self.skills = [], [], []
            def on_unload(self, callback): self.unload = callback
            def register_hook(self, *args): self.hooks.append(args)
            def register_tool(self, **kwargs): self.tools.append(kwargs)
            def register_system_prompt_section(self, name, callback): self.instructions = callback
            def register_skill(self, *args): self.skills.append(args)
        (self.root / 'dfsc-bridge').mkdir()
        (self.root / 'dfsc-bridge/config.json').write_text(json.dumps(self.config.to_dict()), encoding='utf-8')
        ctx = Context()
        modules = {'hermes_constants': NS(get_hermes_home=lambda: self.root),
                   'dotenv': NS(dotenv_values=lambda path: self.fail('External mode read .env'))}
        with patch.dict(sys.modules, modules), patch.object(plugin, 'Integration') as legacy:
            plugin.register(ctx)
        legacy.assert_not_called()
        self.assertEqual(ctx.hooks, [])
        self.assertEqual(ctx.tools[0]['schema']['parameters']['properties']['method']['enum'], list(external.METHODS))
        self.assertIn('skills/external', ctx.skills[0][1].as_posix())
        self.assertNotIn('human.grant', ctx.instructions())
        ctx.unload()
        self.assertEqual(json.loads(ctx.tools[0]['handler']({'method': 'task.list'})),
                         {'error': {'code': 'adapter-unloaded'}})

    def test_loopback_handshake_and_direct_task_projection(self):
        result = external.call(self.config, 'task.create', {'key': 'create-1', 'cwd': str(self.project), 'title': 'One task'})
        self.assertEqual(result['id'], 'task-fixture')
        self.assertEqual([r['method'] for r in self.requests], ['system.capabilities', 'task.create'])
        for request in self.requests:
            self.assertEqual(request['protocol'], external.PROTOCOL)
            self.assertEqual(request['version'], 1)
            self.assertEqual(request['token'], self.descriptor['token'])
            self.assertNotIn('agentId', request)
        self.assertNotIn(self.descriptor['token'], json.dumps(result))

    def test_tool_metadata_is_searchable_without_expanding_protocol(self):
        metadata = (Path(__file__).parent / 'plugin.yaml').read_text(encoding='utf-8')
        self.assertIn('version: 0.2.0\n', metadata)
        description = next(line.removeprefix('description: ') for line in metadata.splitlines()
                           if line.startswith('description: '))
        for boundary in ['explicitly configured', 'legacy or dfsc-external-v1',
                         'capabilities depend on that protocol', 'External-mode approvals remain local',
                         'human approvals and event wakeups are legacy-only']:
            self.assertIn(boundary, description)
        captured = {}
        sections = {}
        ctx = NS(on_unload=lambda callback: None,
                 register_tool=lambda **tool: captured.update(tool),
                 register_system_prompt_section=lambda name, callback: sections.update({name: callback}),
                 register_skill=lambda *args: None)
        external.register(ctx, self.config)
        schema = captured['schema']
        for term in ['DFSC', 'engineering', 'task', 'create', 'submit', 'capabilities', 'status', 'result', 'stop']:
            with self.subTest(term=term):
                self.assertRegex(schema['description'], r'\b' + term + r'\b')
        properties = schema['parameters']['properties']
        self.assertEqual(properties['method']['enum'], list(external.METHODS))
        self.assertFalse(schema['parameters']['additionalProperties'])
        self.assertFalse(properties['params']['additionalProperties'])
        self.assertIn('task.create.id', properties['params']['properties']['taskId']['description'])
        self.assertIn('DFSC 本机处理', schema['description'])
        instructions = sections['dfsc-external']()
        for boundary in ['当前 DFSC 进程', 'resultAvailable=false', '不能重新派工', '不读取整个原生历史']:
            self.assertIn(boundary, instructions)

    def test_descriptor_validation_happens_before_network_and_never_reads_human(self):
        (self.credentials / 'human.json').write_text('not-json-never-read', encoding='utf-8')
        for change in [{'protocol': None}, {'agentId': 'another'}, {'role': 'human'},
                       {'host': '0.0.0.0'}, {'transport': 'unix'}, {'port': True}, {'token': ''}]:
            self.write_descriptor(**change)
            with self.subTest(change=change), self.assertRaises(external.ExternalError):
                external.call(self.config, 'task.list')
        self.assertEqual(self.requests, [])

    def test_unsupported_methods_and_spoofed_fields_do_not_reach_socket(self):
        for method in ['approval.respond', 'human.grant', 'events.wait', 'task.accept', 'task.pause']:
            with self.subTest(method=method), self.assertRaises(external.ExternalError):
                external.call(self.config, method, {'taskId': 'task-fixture'})
        for params in [{'key': 'k', 'cwd': str(self.project), 'title': 'T', 'origin': {'source': 'human'}},
                       {'taskId': 'task-fixture', 'key': 's', 'message': 'M', 'confirmed': True}]:
            method = 'task.create' if 'cwd' in params else 'run.submit'
            with self.assertRaises(external.ExternalError):
                external.call(self.config, method, params)
        self.assertEqual(self.requests, [])

    def test_capability_protocol_identity_and_missing_method_fail_closed(self):
        for changes in [{'protocol': 'legacy'}, {'agentId': 'other'}, {'roots': []},
                        {'methods': ['system.capabilities']}]:
            self.caps.update(changes)
            with self.subTest(changes=changes), self.assertRaises(external.ExternalError):
                external.call(self.config, 'task.list')
            self.caps = {'protocol': external.PROTOCOL, 'agentId': self.agent_id,
                         'roots': [str(self.project)], 'methods': list(external.METHODS)}
        self.assertTrue(all(r['method'] == 'system.capabilities' for r in self.requests))

    def test_only_exact_authorized_root_can_create(self):
        child = self.project / 'child'
        child.mkdir()
        for path in [str(child), str(self.root), str(self.project / '..'), 'relative']:
            with self.subTest(path=path), self.assertRaises(external.ExternalError):
                external.call(self.config, 'task.create', {'key': 'k', 'title': 'T', 'cwd': path})
        self.assertTrue(all(r['method'] == 'system.capabilities' for r in self.requests))

    def test_foreign_task_and_out_of_scope_result_rejected(self):
        for task in [self.task(origin={'agentProfile': 'other'}), self.task(cwd=str(self.root))]:
            self.responses['task.get'] = {'ok': True, 'result': task}
            with self.assertRaises(external.ExternalError):
                external.call(self.config, 'task.get', {'taskId': 'task-fixture'})

    def test_summary_is_bounded_and_no_tool_or_reasoning_projection(self):
        self.responses['task.get'] = {'ok': True, 'result': self.task(
            summary='x' * 9000, thoughts='not-visible', tools=[{'output': 'not-visible'}], approval={'token': 'not-visible'})}
        result = external.call(self.config, 'task.get', {'taskId': 'task-fixture'})
        self.assertEqual(len(result['summary']), 8000)
        self.assertTrue(result['summaryTruncated'])
        self.assertNotIn('not-visible', json.dumps(result))
        self.assertEqual(result['phase'], 'completed')
        self.assertNotIn('accepted', result)

    def test_completed_without_process_local_summary_preserves_status_without_fabricating_result(self):
        task = self.task(resultAvailable=False, submitted=True, receipt='delivered')
        del task['summary']
        self.responses['task.get'] = {'ok': True, 'result': task}
        result = external.call(self.config, 'task.get', {'taskId': task['id']})
        self.assertEqual(result['id'], task['id'])
        self.assertEqual(result['phase'], 'completed')
        self.assertFalse(result['resultAvailable'])
        self.assertTrue(result['submitted'])
        self.assertEqual(result['receipt'], 'delivered')
        self.assertNotIn('summary', result)
        self.assertNotIn('summaryTruncated', result)
        self.assertNotIn('accepted', result)
        self.assertEqual([request['method'] for request in self.requests], ['system.capabilities', 'task.get'])

    def test_faulty_peer_cannot_echo_bearer_or_change_requested_task(self):
        self.responses['task.get'] = {'ok': True, 'result': self.task(summary=self.descriptor['token'])}
        result = external.call(self.config, 'task.get', {'taskId': 'task-fixture'})
        self.assertEqual(result['summary'], '[redacted]')
        self.responses['task.get'] = {'ok': True, 'result': self.task(id='another-task')}
        with self.assertRaises(external.ExternalError):
            external.call(self.config, 'task.get', {'taskId': 'task-fixture'})

    def test_structured_errors_and_legacy_string_codes(self):
        for error in [{'code': 'connector:revoked'}, {'code': 'unauthorized'}, 'key-conflict',
                      {'code': self.descriptor['token']}, {'code': self.descriptor['token'] + '\n'},
                      self.descriptor['token'] + ' invalid transport']:
            self.responses['task.get'] = {'ok': False, 'error': error}
            with self.subTest(error=error), self.assertRaises(external.ExternalError) as caught:
                external.call(self.config, 'task.get', {'taskId': 'task-fixture'})
            self.assertNotIn(self.descriptor['token'], str(caught.exception))
        self.assertEqual(str(caught.exception), 'request-rejected')

    def test_malformed_utf8_and_oversized_reply_are_bounded(self):
        for reply in [b'\xff\n', b'x' * (external.MAX_REPLY + 1) + b'\n']:
            self.responses['task.list'] = reply
            with self.assertRaises(external.ExternalError):
                external.call(self.config, 'task.list')

    def test_cli_uses_real_client_without_hermes_dependencies(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).parent / 'external.py'),
                                 '--config', str(self.config_file), 'system.capabilities'],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['protocol'], external.PROTOCOL)
        self.assertNotIn(self.descriptor['token'], result.stdout + result.stderr)

    def test_cli_rejects_legacy_methods_before_connecting(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).parent / 'external.py'),
                                 '--config', str(self.config_file), 'approval.respond'],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.requests, [])

    def test_installer_switch_requires_explicit_confirmation_and_preserves_state(self):
        home = self.root / 'hermes'
        home.mkdir()
        settings = {'model': 'existing', 'plugins': {'enabled': ['other']}}
        (home / 'config.yaml').write_text(json.dumps(settings), encoding='utf-8')
        data = home / 'dfsc-bridge'
        data.mkdir()
        previous = configuration.CompanionConfig('legacy', 'Legacy', self.root, (self.project,))
        original_config = json.dumps(previous.to_dict())
        (data / 'config.json').write_text(original_config, encoding='utf-8')
        (data / 'delivery.json').write_text('{"cursor":123}', encoding='utf-8')
        (home / '.env').write_text('PRIVATE=unchanged\n', encoding='utf-8')
        (self.root / 'human.json').write_text('legacy-human-unchanged', encoding='utf-8')
        fake_yaml = NS(safe_load=json.loads, safe_dump=lambda value, **kw: json.dumps(value))
        with patch.dict(sys.modules, {'hermes_yaml': fake_yaml}), patch.object(installer, 'pair') as pair:
            with self.assertRaises(ValueError):
                installer.install(home, self.config)
            self.assertEqual((data / 'config.json').read_text(encoding='utf-8'), original_config)
            result = installer.install(home, self.config, replace_connection=True)
        pair.assert_not_called()
        self.assertFalse(result['paired'])
        self.assertTrue(result['reloadRequired'])
        self.assertEqual(result['protocol'], external.PROTOCOL)
        self.assertEqual((Path(result['backup']) / 'companion-config.json').read_text(encoding='utf-8'), original_config)
        self.assertEqual((data / 'delivery.json').read_text(encoding='utf-8'), '{"cursor":123}')
        self.assertEqual((home / '.env').read_text(encoding='utf-8'), 'PRIVATE=unchanged\n')
        self.assertEqual((self.root / 'human.json').read_text(encoding='utf-8'), 'legacy-human-unchanged')
        installed = json.loads((home / 'config.yaml').read_text(encoding='utf-8'))
        self.assertEqual(installed['model'], 'existing')
        self.assertNotIn('feishu', installed['platform_toolsets'])
        self.assertFalse(installed['plugins']['entries']['hermes-dfsc']['allow_gateway_injection'])
        self.assertEqual(configuration.CompanionConfig.load(home), self.config)

    def test_pair_and_external_mode_are_mutually_exclusive(self):
        fake_yaml = NS()
        with patch.dict(sys.modules, {'hermes_yaml': fake_yaml}), patch.object(installer, 'call') as rpc:
            with self.assertRaises(ValueError):
                installer.pair(self.config)
            with self.assertRaises(ValueError):
                installer.install(self.root, self.config, pair_with_host=True)
        rpc.assert_not_called()
        self.assertFalse((self.root / 'backups').exists())


if __name__ == '__main__':
    unittest.main()
