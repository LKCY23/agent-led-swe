"""Provider connection contract checks; no real credentials or network calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_model_connection import DEFAULT_PROFILE, load_profile, probe, NoRedirect


class ModelConnectionTest(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile(DEFAULT_PROFILE)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'receipt'

    def test_two_requests_and_no_secret_in_evidence(self):
        requests = []

        def send(profile, key, payload):
            requests.append(payload)
            if len(requests) == 1:
                return {'model': 'deepseek-flash', 'stop_reason': 'tool_use', 'content': [
                    {'type': 'tool_use', 'id': 'call_1', 'name': 'connection_probe', 'input': {}}]}
            self.assertEqual(payload['messages'][-1]['content'][0]['tool_use_id'], 'call_1')
            return {'model': 'deepseek-flash', 'stop_reason': 'end_turn', 'content': [
                {'type': 'text', 'text': 'CONNECTION_OK'}]}

        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'synthetic-secret'}):
            self.assertEqual(probe(self.profile, self.output, send)['status'], 'passed')
        self.assertEqual(len(requests), 2)
        self.assertNotIn('synthetic-secret', ''.join(p.read_text() for p in self.output.iterdir()))

    def test_wrong_model_fails_without_retry(self):
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'synthetic-secret'}):
            result = probe(self.profile, self.output, lambda *args: {'model': 'another-model'})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['responses']), 1)

    def test_missing_key_stops_before_request(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(ValueError, 'Missing DEEPSEEK_API_KEY'):
            probe(self.profile, self.output, lambda *args: self.fail('Must not call network'),
                  credentials=Path(self.temp.name) / 'absent.json')
        self.assertFalse(self.output.exists())

    def test_invalid_endpoints_and_redirects_rejected(self):
        for endpoint in ('http://remote.example', 'https://key@example.com', 'https://example.com?key=x'):
            path = Path(self.temp.name) / 'bad.json'
            path.write_text(json.dumps({**self.profile, 'base_url': endpoint}))
            with self.assertRaises(ValueError):
                load_profile(path)
        with self.assertRaisesRegex(ValueError, 'redirected'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://another.example')


if __name__ == '__main__':
    unittest.main()
