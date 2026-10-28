"""Defence-in-depth task scope. The DFSC host also enforces credential-bound scope."""
from pathlib import Path
try:
    from .client import call as transport_call
except ImportError:
    from client import call as transport_call


class ForeignTaskError(ValueError):
    pass


class ScopedBridge:
    def __init__(self, configuration):
        self.configuration = configuration

    def call(self, root, method, params=None, *, human=False, cancel=None):
        c = self.configuration
        if Path(root) != c.credentials:
            raise ValueError('Credential directory does not match this profile')
        p = dict(params or {})
        if method == 'human.grant':
            if not human:
                raise ValueError('Human capability required')
            p['origin'] = {**p.get('origin', {}), 'agentProfile': c.agent_id, 'agentDisplayName': c.display_name}
        elif method == 'task.create':
            if not c.within(p.get('cwd')):
                raise ValueError('Engineering work must stay within this agent workspace scope')
            p['cwd'] = str(Path(p['cwd']).resolve())
            prefix = c.display_name + ' · '
            if c.title_prefix and not p.get('title', '').startswith(prefix):
                p['title'] = prefix + p.get('title', '')
        elif method == 'task.list':
            offset = p.get('offset', 0)
            if type(offset) is not int or offset < 0:
                raise ValueError('Invalid offset')
            found, raw_offset = [], 0
            while True:
                page = transport_call(root, method, {'offset': raw_offset}, cancel=cancel, agent_id=c.agent_id)
                found.extend(t for t in page if c.owns(t))
                if len(page) < 50 or len(found) >= offset + 50:
                    break
                raw_offset += 50
            return found[offset:offset + 50]
        elif p.get('taskId'):
            task = transport_call(root, 'task.get', {'taskId': p['taskId']}, cancel=cancel, agent_id=c.agent_id)
            if not c.owns(task):
                raise ForeignTaskError('Task does not belong to this agent within its workspace scope')
        elif method not in ('system.capabilities', 'events.wait'):
            raise ValueError('Task identity is required')
        result = transport_call(root, method, p, human=human, cancel=cancel, agent_id=c.agent_id)
        if method == 'system.capabilities':
            result = dict(result)
            if result.get('agentId') not in (None, c.agent_id):
                raise ValueError('Bridge credential identity mismatch')
            roots = []
            for raw in result.get('roots', []):
                authorized = Path(raw).resolve()
                if not c.workspace_roots:
                    roots.append(str(authorized))
                for scoped in c.workspace_roots:
                    if authorized == scoped or authorized in scoped.parents:
                        roots.append(str(scoped))
                    elif scoped in authorized.parents:
                        roots.append(str(authorized))
            result.update(roots=sorted(set(roots)), agentProfile=c.agent_id, agentDisplayName=c.display_name)
        if method == 'task.create' and not c.owns(result):
            raise ValueError('Created task origin mismatch; query existing receipt before retrying')
        return result
