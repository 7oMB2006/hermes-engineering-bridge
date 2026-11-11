"""Explicit profile installer and optional trusted-human pairing; never a model tool."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile

try:
    from .configuration import CompanionConfig
    from .client import call
    from .external import load_connector
except ImportError:
    from configuration import CompanionConfig
    from client import call
    from external import load_connector


def pair(configuration):
    # This management-only command is deliberately separate from dfsc-bridge.
    if configuration.protocol is not None:
        raise ValueError('External connectors must be paired in DFSC, not with human credentials')
    current = call(configuration.bridge_root, 'human.agents', human=True)
    agents = current['agents']
    roots = [str(root) for root in configuration.workspace_roots]
    if not roots:
        roots = call(configuration.bridge_root, 'system.capabilities', human=True).get('roots', [])
    if not roots:
        raise ValueError('Authorize an engineering root in DFSC before pairing')
    updated = [a for a in agents if a['id'] != configuration.agent_id]
    updated.append({'id': configuration.agent_id, 'displayName': configuration.display_name, 'roots': roots})
    payload = {'agents': updated}
    if 'revision' in current:
        payload['expectedRevision'] = current['revision']
    return call(configuration.bridge_root, 'human.agents', payload, human=True)


def install(home, configuration, *, source=None, pair_with_host=False, replace_connection=False):
    import hermes_yaml as yaml
    if configuration.protocol is not None and pair_with_host:
        raise ValueError('--pair is unavailable for an external connector')
    home = Path(home).resolve()
    if not (home / 'config.yaml').is_file():
        raise ValueError('An existing Hermes profile with config.yaml is required')
    profile_config = home / 'dfsc-bridge/config.json'
    if profile_config.exists():
        try:
            previous = CompanionConfig.load(home)
            previous_connection = (previous.protocol, previous.agent_id, previous.bridge_root, previous.workspace_roots)
        except (ValueError, KeyError, TypeError):
            previous_connection = None
        next_connection = (configuration.protocol, configuration.agent_id, configuration.bridge_root, configuration.workspace_roots)
        if previous_connection != next_connection and not replace_connection:
            raise ValueError('Existing connection differs; back up and explicitly use --replace-connection to switch')
    source = Path(source or __file__).resolve()
    if source.is_file():
        source = source.parent
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = home / 'backups' / ('dfsc-companion-' + stamp)
    backup.mkdir(parents=True, mode=0o700)
    settings_path = home / 'config.yaml'
    shutil.copy2(settings_path, backup / 'config.yaml')
    data = home / 'dfsc-bridge'
    data.mkdir(mode=0o700, exist_ok=True)
    if profile_config.exists():
        shutil.copy2(profile_config, backup / 'companion-config.json')
    target = home / 'plugins/hermes-dfsc'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copytree(target, backup / 'plugin', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    settings = yaml.safe_load(settings_path.read_text(encoding='utf-8')) or {}
    for toolset in ['dfsc', 'skills']:
        if toolset not in settings.setdefault('toolsets', []):
            settings['toolsets'].append(toolset)
        for platform in (['cli', 'feishu'] if configuration.protocol is None else ['cli']):
            if toolset not in settings.setdefault('platform_toolsets', {}).setdefault(platform, []):
                settings['platform_toolsets'][platform].append(toolset)
    plugins = settings.setdefault('plugins', {})
    if 'hermes-dfsc' not in plugins.setdefault('enabled', []):
        plugins['enabled'].append('hermes-dfsc')
    plugins.setdefault('entries', {}).setdefault('hermes-dfsc', {})['allow_gateway_injection'] = configuration.protocol is None
    # Check local configuration before modifying the host's active registrations.
    settings_text = yaml.safe_dump(settings, allow_unicode=True, sort_keys=False)
    config_text = json.dumps(configuration.to_dict(), ensure_ascii=False, indent=2) + '\n'
    with tempfile.TemporaryDirectory(prefix='.dfsc-install-', dir=target.parent) as temporary:
        staged = Path(temporary) / 'plugin'
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'test_*.py', 'install_profile.py', 'README.md'))
        for required in ['__init__.py', 'configuration.py', 'scope.py', 'client.py', 'external.py',
                         'plugin.yaml', 'dfsc-bridge', 'skills/SKILL.md', 'skills/external/SKILL.md']:
            if not (staged / required).is_file():
                raise ValueError('Incomplete companion source: ' + required)
        # Stage everything before changing either registration or installed code.
        if pair_with_host:
            pair(configuration)
        previous = Path(temporary) / 'previous'
        swapped = False
        try:
            if target.exists():
                target.rename(previous)
            staged.rename(target)
            swapped = True
            for path, text in [(profile_config, config_text), (settings_path, settings_text)]:
                pending = path.with_suffix(path.suffix + '.tmp')
                pending.write_text(text, encoding='utf-8')
                pending.chmod(0o600)
                pending.replace(path)
            (target / 'dfsc-bridge').chmod(0o700)
        except Exception:
            if swapped:
                shutil.rmtree(target)
            if previous.exists():
                previous.rename(target)
            shutil.copy2(backup / 'config.yaml', settings_path)
            if (backup / 'companion-config.json').exists():
                shutil.copy2(backup / 'companion-config.json', profile_config)
            elif profile_config.exists():
                profile_config.unlink()
            raise RuntimeError('Companion files restored after installation failure; host pairing may already be registered. Backup: ' + str(backup)) from None
    return {'profile': str(home), 'agentId': configuration.agent_id, 'backup': str(backup),
            'paired': pair_with_host, 'reloadRequired': True,
            'protocol': configuration.protocol or 'legacy-hermes-bridge'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-home', required=True, type=Path)
    configurations = parser.add_mutually_exclusive_group()
    configurations.add_argument('--config', type=Path, help='Non-secret companion JSON; required for first installation')
    configurations.add_argument('--desktop-connector', type=Path, help='Non-secret dfsc-external-v1 config exported by DFSC')
    parser.add_argument('--hermes-source', type=Path, help='Hermes source root when hermes_yaml is not installed in this Python environment')
    parser.add_argument('--pair', action='store_true', help='Use the DFSC trusted-human credential to register this agent and current roots')
    parser.add_argument('--replace-connection', action='store_true', help='Explicitly switch an existing profile connection after creating a backup')
    args = parser.parse_args()
    if args.desktop_connector and args.pair:
        parser.error('--desktop-connector cannot be combined with --pair')
    if args.hermes_source:
        source = args.hermes_source.resolve()
        sys.path.insert(0, str(source))
        from pm.environments import activate_dependencies
        activate_dependencies(source)
    if args.desktop_connector:
        configuration = load_connector(args.desktop_connector)
    else:
        configuration = CompanionConfig.from_dict(json.loads(args.config.read_text(encoding='utf-8'))) if args.config else CompanionConfig.load(args.profile_home)
    print(json.dumps(install(args.profile_home, configuration, pair_with_host=args.pair,
                             replace_connection=args.replace_connection), ensure_ascii=False))


if __name__ == '__main__':
    main()
