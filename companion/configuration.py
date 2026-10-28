"""Profile-local, non-secret companion configuration; never inferred from chat text."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys


def default_bridge_root():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA')
        if not base:
            raise ValueError('APPDATA is required to locate the DFSC profile')
        return Path(base) / 'DFSC Hermes' / 'agent-bridge'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/DFSC Hermes/agent-bridge'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'DFSC Hermes' / 'agent-bridge'


def absolute_path(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-16-le')) // 2 > 4096 or not Path(value).is_absolute():
        raise ValueError(label + ' must be an absolute local path')
    return Path(value).resolve()


@dataclass(frozen=True)
class CompanionConfig:
    agent_id: str
    display_name: str
    bridge_root: Path
    workspace_roots: tuple[Path, ...] = ()
    role_instructions: str = ''
    title_prefix: bool = True

    @property
    def credentials(self):
        return self.bridge_root / 'agents' / self.agent_id

    def within(self, raw):
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            return False
        path = Path(raw).resolve()
        return not self.workspace_roots or any(path == root or root in path.parents for root in self.workspace_roots)

    def owns(self, task):
        if not isinstance(task, dict) or not self.within(task.get('cwd')):
            return False
        origin = task.get('origin') or {}
        owner = origin.get('agentProfile')
        if not owner and self.agent_id == 'h-keke' and isinstance(origin.get('sessionKey'), str) and origin['sessionKey'].startswith('agent:h-keke:'):
            owner = 'h-keke'
        return owner == self.agent_id

    def to_dict(self):
        return {'schemaVersion': 1, 'agentId': self.agent_id, 'displayName': self.display_name,
                'bridgeRoot': str(self.bridge_root), 'workspaceRoots': [str(p) for p in self.workspace_roots],
                'roleInstructions': self.role_instructions, 'titlePrefix': self.title_prefix}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or value.get('schemaVersion') != 1:
            raise ValueError('Unsupported companion configuration schema')
        ident = value.get('agentId')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', ident) or re.fullmatch(r'con|prn|aux|nul|com[1-9]|lpt[1-9]', ident):
            raise ValueError('Invalid agentId')
        display = value.get('displayName')
        if not isinstance(display, str) or not display.strip() or len(display.encode('utf-16-le')) // 2 > 100 or any(ord(c) < 32 or ord(c) == 127 for c in display):
            raise ValueError('Invalid displayName')
        roots = value.get('workspaceRoots', [])
        if not isinstance(roots, list) or len(roots) > 32:
            raise ValueError('Invalid workspaceRoots')
        role = value.get('roleInstructions', '')
        if not isinstance(role, str) or len(role) > 4000:
            raise ValueError('Invalid roleInstructions')
        prefix = value.get('titlePrefix', True)
        if type(prefix) is not bool:
            raise ValueError('Invalid titlePrefix')
        return cls(ident, display.strip(), absolute_path(value['bridgeRoot'] if 'bridgeRoot' in value else str(default_bridge_root()), 'bridgeRoot'),
                   tuple(dict.fromkeys(absolute_path(root, 'workspaceRoots') for root in roots)), role, prefix)

    @classmethod
    def load(cls, profile_home):
        path = Path(profile_home) / 'dfsc-bridge/config.json'
        if path.stat().st_size > 65536:
            raise ValueError('Companion configuration is too large')
        return cls.from_dict(json.loads(path.read_text(encoding='utf-8')))
