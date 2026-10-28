"""Bounded JSONL client. The model-facing entrypoint never reads human credentials."""
import json
import socket
import time
from pathlib import Path


def call(root, method, params=None, *, human=False, cancel=None, agent_id=None):
    if cancel and cancel.is_set():
        raise RuntimeError('Bridge subscription cancelled')
    descriptor = json.loads((Path(root) / ('human.json' if human else 'model.json')).read_text(encoding='utf-8'))
    if descriptor.get('version') != 1:
        raise RuntimeError('Incompatible DFSC Bridge')
    role = 'human' if human else 'model'
    if agent_id is not None and (descriptor.get('agentId') != agent_id or descriptor.get('role') != role):
        raise RuntimeError('DFSC credential identity or role mismatch')
    transport = descriptor.get('transport', 'unix')
    if transport == 'tcp':
        if descriptor.get('host') != '127.0.0.1' or type(descriptor.get('port')) is not int or not 1 <= descriptor['port'] <= 65535:
            raise RuntimeError('Bridge TCP endpoint must be an IPv4 loopback address')
        family, address = socket.AF_INET, ('127.0.0.1', descriptor['port'])
    elif transport == 'unix':
        if not hasattr(socket, 'AF_UNIX') or not isinstance(descriptor.get('socket'), str) or not descriptor['socket']:
            raise RuntimeError('Local Unix socket is unavailable')
        family, address = socket.AF_UNIX, descriptor['socket']
    else:
        raise RuntimeError('Unsupported Bridge transport')
    if not isinstance(descriptor.get('token'), str) or not descriptor['token']:
        raise RuntimeError('Missing Bridge credential')
    with socket.socket(family, socket.SOCK_STREAM) as conn:
        conn.settimeout(32)
        conn.connect(address)
        conn.sendall((json.dumps({'version': 1, 'token': descriptor['token'], 'method': method, 'params': params or {}}, ensure_ascii=False) + '\n').encode())
        deadline = time.monotonic() + 32
        if cancel:
            conn.settimeout(0.25)
        data = bytearray()
        while b'\n' not in data:
            if cancel and cancel.is_set():
                raise RuntimeError('Bridge subscription cancelled')
            if time.monotonic() >= deadline:
                raise TimeoutError('Bridge reply timed out; query before retrying')
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                if cancel:
                    continue
                raise
            if not chunk:
                raise RuntimeError('Bridge disconnected before reply; query before retrying')
            data.extend(chunk)
            if len(data) > 8 * 1024 * 1024:
                raise RuntimeError('Bridge response too large')
        result = json.loads(data.split(b'\n', 1)[0])
        if not result.get('ok'):
            raise RuntimeError(result.get('error', 'Bridge request failed'))
        return result['result']
