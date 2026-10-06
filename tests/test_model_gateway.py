"""Exercise actual proxy I/O, streaming and denied routes without model calls."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
from threading import Thread
import unittest

from model_gateway import handler, permitted


class GatewayTest(unittest.TestCase):
    def test_only_fixed_protocol_routes_are_allowed(self):
        self.assertTrue(permitted('claude-code', 'POST', '/v1/messages?beta=true'))
        self.assertTrue(permitted('codex', 'POST', '/responses'))
        for target in ('https://github.com/responses', '//github.com/responses',
                       '/responses/../anything', '/%72esponses', '/responses?url=https://github.com',
                       '/responses#fragment'):
            self.assertFalse(permitted('codex', 'POST', target))
        self.assertFalse(permitted('codex', 'CONNECT', '/responses'))
        self.assertFalse(permitted('codex', 'GET', '/responses'))

    def test_stream_auth_forwarding_and_redirect_refusal(self):
        received = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                received.append((self.path, body, self.headers.get('Authorization')))
                if body == b'redirect':
                    self.send_response(302)
                    self.send_header('Location', 'https://github.com/answer')
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                self.wfile.write(b'data: first\n\ndata: second\n\n')

        upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        proxy = ThreadingHTTPServer(('127.0.0.1', 0), handler('codex',
            f'http://127.0.0.1:{upstream.server_port}/v1', {'Authorization': 'Bearer gateway-synthetic'}))
        threads = [Thread(target=s.serve_forever, daemon=True) for s in (upstream, proxy)]
        for thread in threads:
            thread.start()
        try:
            for body, status in [(b'payload', 200), (b'redirect', 502)]:
                connection = http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=3)
                connection.request('POST', '/responses', body, {'Authorization': 'Bearer synthetic'})
                response = connection.getresponse()
                self.assertEqual(response.status, status)
                data = response.read()
                if status == 200:
                    self.assertEqual(data, b'data: first\n\ndata: second\n\n')
                self.assertIsNone(response.getheader('Location'))
                connection.close()
            connection = http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=3)
            connection.request('CONNECT', 'example.com:443')
            self.assertEqual(connection.getresponse().status, 403)
            connection.close()
            self.assertEqual(received, [('/v1/responses', b'payload', 'Bearer gateway-synthetic'),
                                        ('/v1/responses', b'redirect', 'Bearer gateway-synthetic')])
        finally:
            for server in (proxy, upstream):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join()


if __name__ == '__main__':
    unittest.main()
