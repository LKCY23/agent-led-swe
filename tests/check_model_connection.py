#!/usr/bin/env python3
"""Check the selected DeepSeek endpoint with two bounded synthetic messages.

This is a provider connection check, not an agent runner or benchmark. No task
source, user settings, or skill content is sent. Credentials stay in memory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from evaluation_runtime import digest, write_json
from model_config import load_profile, credential, DEFAULT_CREDENTIALS


DEFAULT_PROFILE = Path(__file__).parent / 'configs/models/deepseek-v4.1-flash.json'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Endpoint redirected; verify the configured service before sending credentials')


def post_message(profile, key, payload):
    request = Request(profile['base_url'].rstrip('/') + '/v1/messages',
                      data=json.dumps(payload).encode(), method='POST', headers={
                          'Content-Type': 'application/json', 'anthropic-version': '2023-06-01',
                          'x-api-key': key})
    try:
        with build_opener(NoRedirect).open(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as exc:
        # Never record request headers or arbitrary server error bodies.
        raise ValueError(f'Provider returned HTTP {exc.code}') from None
    except (URLError, TimeoutError):
        raise ValueError('Provider connection failed or timed out') from None


def probe(profile, output, send=post_message, credentials=DEFAULT_CREDENTIALS):
    if profile['protocol'] != 'anthropic-messages' or profile['model'] != 'deepseek-flash':
        raise ValueError('This probe requires DeepSeek Flash through Anthropic Messages')
    key = credential(profile, credentials)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    receipt = {'status': 'running', 'profile': profile, 'max_requests': 2,
               'max_output_tokens_per_request': 128, 'thinking': 'disabled',
               'timeout_seconds_per_request': 60, 'responses': [], 'cost': None,
               'scope': 'Provider text/tool-result exchange only; streaming and agent execution untested'}
    write_json(output / 'receipt.json', receipt)
    tool = {'name': 'connection_probe', 'description': 'Return a fixed connectivity marker.',
            'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}
    messages = [{'role': 'user', 'content': 'Call connection_probe with an empty object. '
                 'Then reply with exactly the marker from its result.'}]
    common = {'model': profile['model'], 'max_tokens': 128,
              'thinking': {'type': 'disabled'}, 'tools': [tool]}
    try:
        for index in range(2):
            payload = {**common, 'messages': messages,
                       'tool_choice': {'type': 'tool', 'name': 'connection_probe'}
                       if index == 0 else {'type': 'none'}}
            response = send(profile, key, payload)
            receipt['responses'].append({k: response.get(k) for k in ('model', 'stop_reason', 'usage')})
            write_json(output / f'response-{index + 1}.json', response)
            if response.get('model') != profile['model']:
                raise ValueError('Response model differs from the configured model; inspect receipt')
            content = response.get('content', [])
            if index == 0:
                calls = [c for c in content if c.get('type') == 'tool_use']
                if (response.get('stop_reason') != 'tool_use' or len(calls) != 1
                        or calls[0].get('name') != tool['name'] or calls[0].get('input') != {}
                        or not calls[0].get('id')):
                    raise ValueError('Provider did not return the requested valid tool call')
                messages += [{'role': 'assistant', 'content': content},
                             {'role': 'user', 'content': [{'type': 'tool_result',
                               'tool_use_id': calls[0]['id'], 'content': 'CONNECTION_OK'}]}]
            elif (response.get('stop_reason') != 'end_turn' or ''.join(
                    c.get('text', '') for c in content if c.get('type') == 'text').strip() != 'CONNECTION_OK'):
                raise ValueError('Provider did not complete the tool-result exchange')
        receipt['status'] = 'passed'
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        receipt['status'] = 'failed'
        receipt['error'] = str(exc)
    finally:
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
        write_json(output / 'receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--check-only', action='store_true', help='Validate config and credential presence; no request')
    parser.add_argument('--credentials', type=Path, default=DEFAULT_CREDENTIALS)
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile)
        if args.check_only:
            try:
                credential(profile, args.credentials)
                present = True
            except ValueError:
                present = False
            print(json.dumps({'profile_valid': True, 'credential_present': present,
                              'credential_env': profile['api_key_env'], 'network_called': False}))
            return 0 if present else 1
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        output = Path(__file__).parent / 'runs' / ('model-connection-' + stamp)
        receipt = probe(profile, output, credentials=args.credentials)
        write_json(output / 'profile-source.json', {'path': str(args.profile.resolve()),
                                                   'sha256': digest(args.profile)})
        print(json.dumps({'status': receipt['status'], 'evidence': str(output)}))
        return 0 if receipt['status'] == 'passed' else 1
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
