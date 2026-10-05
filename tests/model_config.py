"""Non-secret model profiles and explicitly selected local credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


CONFIGS = Path(__file__).parent / 'configs'
DEFAULT_CREDENTIALS = CONFIGS / 'credentials.local.json'


def load_profile(path):
    profile = json.loads(Path(path).read_text())
    required = {'provider', 'model', 'version_label', 'protocol'}
    if not isinstance(profile, dict) or not required <= profile.keys():
        raise ValueError('Model profile requires provider, model, version_label and protocol')
    if profile.keys() - required - {'base_url', 'api_key_env'}:
        raise ValueError('Unexpected model profile fields; credentials belong in the local credential file')
    if any(not isinstance(v, str) or not v for v in profile.values()):
        raise ValueError('Model profile fields must be nonempty strings')
    if profile['protocol'] == 'anthropic-messages':
        if not {'base_url', 'api_key_env'} <= profile.keys():
            raise ValueError('Anthropic Messages requires base_url and api_key_env')
        endpoint = urlsplit(profile['base_url'])
        if (not endpoint.hostname or endpoint.username or endpoint.password
                or endpoint.query or endpoint.fragment
                or (endpoint.scheme != 'https' and not (
                    endpoint.scheme == 'http' and endpoint.hostname in ('localhost', '127.0.0.1', '::1')))):
            raise ValueError('Use HTTPS or loopback HTTP without credentials/query in the endpoint')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', profile['api_key_env']):
            raise ValueError('api_key_env must name an environment variable')
    elif profile['protocol'] != 'codex-native':
        raise ValueError('Unsupported model protocol')
    elif set(profile) != required:
        raise ValueError('Native Codex profile does not support endpoint or API-key overrides')
    return profile


def credential(profile, path=DEFAULT_CREDENTIALS):
    """Environment takes precedence; never read the user's global agent settings."""
    name = profile['api_key_env']
    value = os.environ.get(name, '').strip()
    if not value and Path(path).is_file():
        try:
            values = json.loads(Path(path).read_text())
        except ValueError:
            raise ValueError('Credential file is not valid JSON') from None
        if not isinstance(values, dict) or not isinstance(values.get(name, ''), str):
            raise ValueError('Credential file must map environment variable names to strings')
        value = values.get(name, '').strip()
    if not value:
        raise ValueError(f'Missing {name}; fill {path} or set that environment variable')
    if '\n' in value or '\r' in value:
        raise ValueError('Credential must be a single line')
    return value


def validate_compatibility(agent, profile, effort):
    if agent == 'codex':
        if profile['provider'] != 'openai' or profile['protocol'] != 'codex-native':
            raise ValueError('This Codex adapter currently supports native OpenAI configuration only')
        if effort not in ('low', 'medium', 'high', 'xhigh'):
            raise ValueError('Unsupported Codex effort')
    elif agent == 'claude-code':
        if (profile['provider'] != 'deepseek' or profile['protocol'] != 'anthropic-messages'
                or profile['model'] != 'deepseek-flash'):
            raise ValueError('Initial Claude Code integration supports DeepSeek Flash over Anthropic Messages')
        if effort not in ('low', 'high', 'max'):
            raise ValueError('Use DeepSeek effort low/high/max to avoid implicit effort alias mapping')
    else:
        raise ValueError('Unsupported agent')


def claude_environment(profile, key):
    """Explicitly pin all Claude model slots to the same provider model."""
    return {'ANTHROPIC_API_KEY': key, 'ANTHROPIC_BASE_URL': profile['base_url'],
            'ANTHROPIC_MODEL': profile['model'],
            **{f'ANTHROPIC_DEFAULT_{slot}_MODEL': profile['model']
               for slot in ('OPUS', 'SONNET', 'HAIKU', 'FABLE')},
            'CLAUDE_CODE_SUBAGENT_MODEL': profile['model'],
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
            'DISABLE_AUTOUPDATER': '1'}
