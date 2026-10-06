"""Bounded non-streaming Chat Completions transport, isolated from tool dispatch.

Credentials travel over stdin to a short-lived HTTP child, never command arguments
or evidence. The parent timeout kills a stalled child; HTTP errors are sanitized.
"""
import json
from pathlib import Path
import subprocess
import sys
from urllib import error, request


def complete(profile, key, payload, timeout):
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve())],
            input=json.dumps({'url': profile['base_url'].rstrip('/') + '/chat/completions',
                              'key': key, 'payload': payload, 'timeout': timeout}),
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError('Simulated-user model request timed out') from None
    if result.returncode:
        # Never include untrusted HTTP error bodies or local exception messages.
        raise RuntimeError('Simulated-user HTTP request failed')
    value = json.loads(result.stdout)
    if 'transport_error' in value:
        raise RuntimeError(value['transport_error'])
    return value


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    args = json.load(sys.stdin)
    data = json.dumps(args['payload']).encode()
    req = request.Request(args['url'], data=data, headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + args['key']})
    try:
        opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
        with opener.open(req, timeout=args['timeout']) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError('Oversized response')
            value = json.loads(raw)
    except error.HTTPError as exc:
        value = {'transport_error': f'Simulated-user HTTP status {exc.code}'}
    except (OSError, ValueError, error.URLError):
        value = {'transport_error': 'Simulated-user transport or response error'}
    print(json.dumps(value))


if __name__ == '__main__':
    main()
