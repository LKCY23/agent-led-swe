"""Per-trial internal Docker network with one fixed model gateway."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import time
import tempfile
import uuid


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE).strip()


@contextmanager
def model_network(image, agent, upstream, evidence, auth_headers=None):
    name = 'swe-model-' + uuid.uuid4().hex[:12]
    created = False
    gateway = False
    secret_dir = tempfile.TemporaryDirectory(prefix='swe-gateway-auth-')
    try:
        docker('network', 'create', '--internal', name)
        created = True
        (evidence / 'network-policy.json').write_text(json.dumps({
            'mode': 'internal-model-gateway-v1', 'agent': agent, 'upstream': upstream,
            'routes': 'model_gateway.ROUTES', 'image': image,
            'redirects': False, 'connect_proxy': False}, indent=2) + '\n')
        mounts, auth_args = [], []
        if auth_headers:
            secret = Path(secret_dir.name) / 'auth.json'
            secret.write_text(json.dumps(auth_headers))
            secret.chmod(0o600)
            mounts = ['-v', f'{secret}:/run/model-auth.json:ro']
            auth_args = ['--auth-file', '/run/model-auth.json']
        docker('create', '--name', name, '--network', 'bridge', '--cap-drop=ALL',
               '--user', f'{os.getuid()}:{os.getgid()}',
               '--security-opt=no-new-privileges', '--read-only', '--memory', '256m',
               '--pids-limit', '64', '-v', f'{Path(__file__).with_name("model_gateway.py")}:/gateway.py:ro',
               *mounts, '--entrypoint', 'python3', image, '-u', '/gateway.py',
               '--agent', agent, '--upstream', upstream, *auth_args)
        gateway = True
        docker('network', 'connect', '--alias', 'model-gateway', name, name)
        docker('start', name)
        for _ in range(40):
            ready = subprocess.run(['docker', 'exec', name, 'python3', '-c',
                'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8080/health",timeout=1)'],
                capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('Model gateway failed to start')
        yield name, 'http://model-gateway:8080'
    finally:
        if gateway:
            logs = subprocess.run(['docker', 'logs', name], capture_output=True, text=True)
            (evidence / 'model-gateway.log').write_text(logs.stdout + logs.stderr)
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
        if created:
            subprocess.run(['docker', 'network', 'rm', name], capture_output=True)
        secret_dir.cleanup()


def audit_network(container, evidence):
    """Probe direct IP, public DNS names, host access and the restricted gateway."""
    script = '''
import json, socket, urllib.request, urllib.error
checks = {}
for host, port in [("1.1.1.1",443),("github.com",443),("pypi.org",443),
                   ("host.docker.internal",80),("host.docker.internal",443)]:
    try:
        with socket.create_connection((host,port), timeout=2): pass
        checks[f"{host}:{port}"] = False
    except OSError:
        checks[f"{host}:{port}"] = True
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
checks["gateway_ready"] = opener.open("http://model-gateway:8080/health",timeout=3).status == 204
try:
    opener.open("http://model-gateway:8080/https://github.com",timeout=3)
    checks["arbitrary_route_blocked"] = False
except urllib.error.HTTPError as exc:
    checks["arbitrary_route_blocked"] = exc.code == 403
print(json.dumps(checks))
'''
    checks = json.loads(docker('exec', container, 'python3', '-c', script))
    networks = json.loads(docker('inspect', '--format', '{{json .NetworkSettings.Networks}}', container))
    checks['single_internal_network'] = len(networks) == 1 and all(
        docker('network', 'inspect', '--format', '{{.Internal}}', name) == 'true' for name in networks)
    caps = json.loads(docker('inspect', '--format', '{{json .HostConfig.CapAdd}}', container)) or []
    dropped = json.loads(docker('inspect', '--format', '{{json .HostConfig.CapDrop}}', container)) or []
    checks['no_network_capabilities'] = dropped == ['ALL'] and {cap.removeprefix('CAP_') for cap in caps} <= {'CHOWN'}
    (evidence / 'network-audit.json').write_text(json.dumps(checks, indent=2) + '\n')
    if not all(checks.values()):
        raise RuntimeError('Worker network isolation audit failed; see network-audit.json')
