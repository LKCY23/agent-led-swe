"""Fixed model API reverse proxy. No CONNECT, arbitrary hosts, or redirects.

Runs outside the worker network boundary; request bodies and credentials are
never logged. A route is selected by the trusted runner, not by the worker.
"""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import select
import socket
from threading import Event, Thread
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


ROUTES = {
    'claude-code': {('POST', '/v1/messages'), ('POST', '/v1/messages/count_tokens')},
    'codex': {('POST', '/responses'), ('POST', '/responses/compact'), ('GET', '/models')},
}
HOP_HEADERS = {'host', 'connection', 'transfer-encoding', 'content-length',
               'proxy-authorization', 'proxy-connection', 'upgrade', 'te', 'trailer'}


def permitted(agent, method, target):
    url = urlsplit(target)
    return (not url.scheme and not url.netloc and not url.fragment
            and (method, url.path) in ROUTES[agent]
            and set(parse_qs(url.query, keep_blank_values=True)) <= {'beta', 'client_version'})


def handler(agent, upstream, auth_headers=None):
    endpoint = urlsplit(upstream)
    if endpoint.scheme not in ('http', 'https') or not endpoint.hostname or endpoint.query or endpoint.fragment:
        raise ValueError('Invalid fixed upstream')

    class Gateway(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def relay(self):
            if self.command == 'GET' and self.path == '/health':
                self.send_response(204)
                self.end_headers()
                return
            if not permitted(agent, self.command, self.path):
                print(json.dumps({'event': 'route_denied', 'method': self.command, 'path': urlsplit(self.path).path[:160]}), flush=True)
                self.send_error(403, 'Model route only')
                return
            connection = None
            done, watcher = Event(), None
            try:
                # Both pinned clients send length-delimited requests. Fail closed
                # on other framing rather than ambiguously parsing a proxy request.
                if self.headers.get('Transfer-Encoding'):
                    self.send_error(400, 'Length required')
                    return
                length = int(self.headers.get('Content-Length', '0'))
                if length < 0:
                    self.send_error(400, 'Invalid content length')
                    return
                headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
                if auth_headers:
                    headers = {k: v for k, v in headers.items()
                               if k.lower() not in {'authorization', 'x-api-key', 'chatgpt-account-id'}}
                    headers.update(auth_headers)
                cls = http.client.HTTPSConnection if endpoint.scheme == 'https' else http.client.HTTPConnection
                # Bound connection establishment, not inference/stream duration.
                connection = cls(endpoint.hostname, endpoint.port, timeout=30)
                connection.connect()
                upstream_socket = connection.sock
                upstream_socket.settimeout(None)

                def watch_disconnect():
                    # A closed downstream must not leave a request waiting for
                    # upstream tokens. The group deadline also kills this gateway.
                    while not done.wait(.1):
                        try:
                            ready, _, _ = select.select([self.connection], [], [], 0)
                            if ready and not self.connection.recv(1, socket.MSG_PEEK):
                                upstream_socket.shutdown(socket.SHUT_RDWR)
                                return
                        except OSError:
                            return

                connection.putrequest(self.command, endpoint.path.rstrip('/') + self.path)
                for key, value in headers.items():
                    connection.putheader(key, value)
                connection.putheader('Content-Length', str(length))
                connection.endheaders()
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        raise ConnectionError('Incomplete request body')
                    connection.send(chunk)
                    remaining -= len(chunk)
                watcher = Thread(target=watch_disconnect, daemon=True)
                watcher.start()
                response = connection.getresponse()
                # Never send a redirect target to the worker or follow one here.
                if 300 <= response.status < 400:
                    self.send_error(502, 'Upstream redirect refused')
                    return
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in HOP_HEADERS:
                        self.send_header(key, value)
                self.send_header('Connection', 'close')
                self.end_headers()
                while chunk := response.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
                print(json.dumps({'method': self.command, 'route': urlsplit(self.path).path,
                                  'status': response.status}), flush=True)
            except (OSError, ValueError, http.client.HTTPException):
                # Do not include exception text: it can contain auth or payload data.
                print(json.dumps({'event': 'upstream_or_client_error'}), flush=True)
                self.close_connection = True
            finally:
                done.set()
                if connection:
                    connection.close()
                if watcher:
                    watcher.join()

        do_GET = relay
        do_POST = relay
        do_CONNECT = relay
        do_PUT = relay

    return Gateway


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=ROUTES, required=True)
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--auth-file', type=Path)
    args = parser.parse_args()
    auth = json.loads(args.auth_file.read_text()) if args.auth_file else None
    ThreadingHTTPServer(('0.0.0.0', 8080), handler(args.agent, args.upstream, auth)).serve_forever()
