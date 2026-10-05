"""Codex launch and context checks; native trace parsing uses the frozen helper."""
import json
from pathlib import Path
import re
import subprocess
from evaluation_runtime import digest, write_json, load_helper

CONTEXT_OVERRIDES = [
    'features.plugins=false', 'features.apps=false', 'features.memories=false',
    'features.hooks=false', 'features.multi_agent=false', 'features.skill_search=false',
    'project_doc_max_bytes=0', 'developer_instructions=""',
]


def skill_paths(items):
    text = '\n'.join(c.get('text', '') for i in items for c in i.get('content', []))
    roots = dict(re.findall(r'- `(r\d+)` = `([^`]+)`', text))
    return text, [str(Path(roots[root]) / tail)
                  for root, tail in re.findall(r'\(file: (r\d+)/([^\n]+)\)', text)]


def isolated_context(binary, workspace, evidence, model, effort, sandbox):
    """Inventory and disable skill discovery using invocation-only overrides.

    Debug rendering does not support --ignore-user-config. Explicit overrides
    remove user instructions/catalogs for this check; exec additionally ignores
    user config. This verifies discovery, not a filesystem read-access boundary.
    """
    disabled = set()
    for attempt in range(5):
        overrides = CONTEXT_OVERRIDES + ['skills.config=[' + ','.join(
            '{path=' + json.dumps(p) + ',enabled=false}' for p in sorted(disabled)) + ']']
        command = ([binary] if isinstance(binary, str) else list(binary)) + ['-C', str(workspace), '-s', sandbox,
                   '-c', 'approval_policy="never"', '-c', 'model=' + json.dumps(model),
                   '-c', 'model_reasoning_effort=' + json.dumps(effort)]
        command += [part for value in overrides for part in ('-c', value)]
        command += ['debug', 'prompt-input', 'LOCAL_CONTEXT_CHECK']
        try:
            rendered = subprocess.run(command, capture_output=True, text=True, timeout=40)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Context preflight timed out; executor was not started') from exc
        (evidence / f'context-{attempt}.json').write_text(rendered.stdout)
        (evidence / f'context-{attempt}.stderr').write_text(rendered.stderr)
        if rendered.returncode:
            raise ValueError('Context preflight failed; see saved stderr')
        text, paths = skill_paths(json.loads(rendered.stdout))
        if not paths:
            if ('<skills_instructions>' in text or 'agent-led-swe' in text.lower()
                    or '# AGENTS.md instructions' in text):
                raise ValueError('Unexpected inherited instructions remain in rendered context')
            receipt = {'status': 'verified-discovery', 'disabled_paths': sorted(disabled),
                       'overrides': overrides, 'context_sha256': digest(evidence / f'context-{attempt}.json'),
                       'scope': 'No automatic skills or inherited project/developer guidance in '
                                'preflight; fresh ephemeral execution. Not filesystem read isolation.'}
            write_json(evidence / 'isolation.json', receipt)
            return receipt
        if set(paths) <= disabled:
            raise ValueError('Skill disabling did not take effect')
        disabled.update(paths)
    raise ValueError('Skill catalog did not clear within bounded preflight')


def codex_command(binary, workspace, model, effort, sandbox, overrides=()):
    command = ([binary] if isinstance(binary, str) else list(binary)) + ['exec', '--ignore-user-config', '--ephemeral', '--json',
            '--sandbox', sandbox, '--skip-git-repo-check', '-C', str(workspace),
            '-c', 'agents.enabled=false', '-c', 'approval_policy="never"',
            '-c', 'web_search="disabled"', '-c', 'model=' + json.dumps(model),
            '-c', 'model_reasoning_effort=' + json.dumps(effort)]
    return command + [part for value in overrides for part in ('-c', value)]



class CodexAdapter:
    name = 'codex'
    executable = 'codex'
    npm_package = '@openai/codex'
    cli_entrypoint = '@openai/codex/bin/codex.js'

    def prepare_context(self, binary, workspace, evidence, model, effort, sandbox):
        return isolated_context(binary, workspace, evidence, model, effort, sandbox)

    def command(self, binary, workspace, model, effort, sandbox, context):
        return codex_command(binary, workspace, model, effort, sandbox, context['overrides']) + ['-']

    def inspect_trace(self, text, helpers):
        return load_helper(helpers / 'inspect_codex_trace.py').inspect_trace(text)
