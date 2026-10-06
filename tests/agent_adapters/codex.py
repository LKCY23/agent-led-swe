"""Codex launch and context checks; native trace parsing uses the frozen helper."""
import json
from pathlib import Path
import re
import subprocess
from evaluation_runtime import digest, write_json, load_helper
from model_config import allow_subagents

CONTEXT_OVERRIDES = [
    'features.plugins=false', 'features.apps=false', 'developer_instructions=""',
]


def delegation_overrides():
    return [] if allow_subagents() else ['features.multi_agent=false', 'agents.enabled=false']


def skill_paths(items):
    text = '\n'.join(c.get('text', '') for i in items for c in i.get('content', []))
    roots = dict(re.findall(r'- `(r\d+)` = `([^`]+)`', text))
    return text, [str(Path(roots[root]) / tail)
                  for root, tail in re.findall(r'\(file: (r\d+)/([^\n]+)\)', text)]


def isolated_context(binary, workspace, evidence, model, effort, sandbox, skill_path=None):
    """Inventory and disable skill discovery using invocation-only overrides.

    Debug rendering does not support --ignore-user-config. Explicit overrides
    remove user instructions/catalogs for this check; exec additionally ignores
    user config. This verifies discovery, not a filesystem read-access boundary.
    """
    disabled = set()
    for attempt in range(5):
        overrides = CONTEXT_OVERRIDES + delegation_overrides() + ['skills.config=[' + ','.join(
            '{path=' + json.dumps(p) + ',enabled=false}' for p in sorted(disabled)) + ']']
        command = ([binary] if isinstance(binary, str) else list(binary)) + ['-C', str(workspace), '-s', sandbox,
                   '-c', 'approval_policy="never"', '-c', 'model=' + json.dumps(model),
                   '-c', 'model_reasoning_effort=' + json.dumps(effort)]
        command += [part for value in overrides for part in ('-c', value)]
        command += ['debug', 'prompt-input', '$agent-led-swe\nLOCAL_CONTEXT_CHECK' if skill_path else 'LOCAL_CONTEXT_CHECK']
        try:
            rendered = subprocess.run(command, capture_output=True, text=True, timeout=40)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Context preflight timed out; executor was not started') from exc
        (evidence / f'context-{attempt}.json').write_text(rendered.stdout)
        (evidence / f'context-{attempt}.stderr').write_text(rendered.stderr)
        if rendered.returncode:
            raise ValueError('Context preflight failed; see saved stderr')
        text, paths = skill_paths(json.loads(rendered.stdout))
        project_paths = {p for p in paths if Path(p).is_relative_to(Path(workspace))}
        unexpected = set(paths) - project_paths - ({str(skill_path)} if skill_path else set())
        if not unexpected:
            if not skill_path and ('agent-led-swe' in text.lower() or
                                   ('<skills_instructions>' in text and not paths)):
                raise ValueError('Unexpected target skill or unrecognized skill catalog in rendered context')
            if skill_path and str(skill_path) not in paths:
                raise ValueError('Target skill was not discovered by Codex')
            receipt = {'status': 'verified-discovery', 'disabled_paths': sorted(disabled),
                       'expected_skill': 'agent-led-swe' if skill_path else None,
                       'entrypoint': str(skill_path) if skill_path else None,
                       'overrides': overrides, 'context_sha256': digest(evidence / f'context-{attempt}.json'),
                       'scope': 'Frozen project guidance and skills remain available alongside the target skill, if installed; '
                                'unrelated external skill catalogs are disabled. Fresh isolated execution; '
                                'native input injection is checked in the saved session.'}
            write_json(evidence / 'isolation.json', receipt)
            return receipt
        if unexpected <= disabled:
            raise ValueError('Skill disabling did not take effect')
        disabled.update(unexpected)
    raise ValueError('Skill catalog did not clear within bounded preflight')


def codex_command(binary, workspace, model, effort, sandbox, overrides=()):
    prefix = [binary] if isinstance(binary, str) else list(binary)
    runtime_overrides = []
    # exec has its own config override parser. Overrides before the subcommand
    # do not configure that parser in the pinned CLI; preserve them after exec.
    while len(prefix) >= 2 and prefix[-2] == '-c':
        runtime_overrides.insert(0, prefix.pop())
        prefix.pop()
    command = prefix + ['exec', '--ignore-user-config', '--ephemeral', '--json',
            '--sandbox', sandbox, '--skip-git-repo-check', '-C', str(workspace),
            '-c', 'approval_policy="never"',
            '-c', 'web_search="disabled"', '-c', 'model=' + json.dumps(model),
            '-c', 'model_reasoning_effort=' + json.dumps(effort)]
    return command + [part for value in [*runtime_overrides, *overrides, *delegation_overrides()] for part in ('-c', value)]



class CodexAdapter:
    name = 'codex'
    executable = 'codex'
    npm_package = '@openai/codex'
    cli_entrypoint = '@openai/codex/bin/codex.js'

    def invocation(self):
        return '$agent-led-swe\n\n'

    def prepare_context(self, binary, workspace, evidence, model, effort, sandbox, skill_path=None):
        return isolated_context(binary, workspace, evidence, model, effort, sandbox, skill_path)

    def command(self, binary, workspace, model, effort, sandbox, context):
        command = codex_command(binary, workspace, model, effort, sandbox, context['overrides'])
        # Fresh isolated HOME/container; retain native input injection evidence
        # before the runtime removes it. Judges still use --ephemeral.
        command.remove('--ephemeral')
        return command + ['-']

    def inspect_trace(self, text, helpers):
        return load_helper(helpers / 'inspect_codex_trace.py').inspect_trace(text)

    def conversation_command(self, binary, workspace, model, effort, sandbox, context, session_id=None):
        command = self.command(binary, workspace, model, effort, sandbox, context)
        if session_id:
            from uuid import UUID
            # exec resume has its own option set. Keep provider/context config
            # after the subcommand; never resume the ambient "last" session.
            index = len(command) - 1 - command[::-1].index('exec')
            command.insert(index + 1, 'resume')
            for flag in ('-C', '--sandbox'):
                index = command.index(flag)
                del command[index:index + 2]
            command[-1:] = ['-c', 'sandbox_mode=' + json.dumps(sandbox), str(UUID(session_id)), '-']
        return command
