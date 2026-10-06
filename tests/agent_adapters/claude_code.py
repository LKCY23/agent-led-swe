"""Claude Code headless execution inside a disposable Docker worker."""
from collections import Counter
import json
import re


# Bundled commands in the pinned 2.1.278 CLI, present in both comparison arms.
BUNDLED_SKILLS = {'deep-research', 'dataviz', 'update-config', 'verify', 'debug',
                  'code-review', 'simplify', 'batch', 'fewer-permission-prompts', 'doctor',
                  'loop', 'claude-api', 'workflow-authoring', 'run', 'run-skill-generator'}


class ClaudeCodeAdapter:
    name = 'claude-code'
    executable = 'claude'
    npm_package = '@anthropic-ai/claude-code'
    cli_entrypoint = '@anthropic-ai/claude-code/bin/claude.exe'

    def invocation(self):
        return '/agent-led-swe\n\n'

    def prepare_context(self, binary, workspace, evidence, model, effort, sandbox, skill_path=None):
        from evaluation_runtime import write_json
        if sandbox != 'danger-full-access' or not isinstance(binary, list) or binary[0] != 'docker':
            raise ValueError('Claude Code execution requires the disposable Docker runtime')
        # No equivalent of Codex prompt-input exists here. Verify actual init events
        # after launch; do not report configuration alone as proven isolation.
        receipt = {'status': 'pending-trace-check', 'expected_skill': 'agent-led-swe' if skill_path else None,
                   'scope': 'Fresh container/home; native skill installation and slash invocation; '
                   'strict empty MCP configuration. Verify native events after execution.'}
        write_json(evidence / 'isolation.json', receipt)
        return receipt

    def command(self, binary, workspace, model, effort, sandbox, context):
        return list(binary) + ['--print', '--no-session-persistence',
            '--input-format', 'stream-json', '--replay-user-messages',
            '--output-format', 'stream-json', '--verbose', '--model', model + '[1m]', '--effort', effort,
            '--setting-sources', 'user', '--settings', '{"disableAllHooks":true,"autoMemoryEnabled":false}', '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--no-chrome',
            '--tools', 'Bash,Read,Write,Edit,Glob,Grep', '--permission-mode', 'bypassPermissions']

    def inspect_trace(self, text, helpers=None):
        counts, malformed, results, models, init = Counter(), [], [], set(), []
        commands = []
        invocations = []
        failures = 0
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                    raise ValueError('Not an event')
                kind = event['type']
                counts[kind] += 1
                if kind == 'system' and event.get('subtype') == 'init':
                    init.append(event)
                if kind == 'result':
                    results.append(event)
                    models.update((event.get('modelUsage') or {}).keys())
                if kind == 'user' and event.get('isReplay') is True:
                    content = event.get('message', {}).get('content', '')
                    if isinstance(content, str):
                        invocations.extend(re.findall(r'<command-name>/([^<]+)</command-name>', content))
                if kind == 'assistant':
                    message = event.get('message') or {}
                    if message.get('model'):
                        models.add(message['model'])
                    for block in message.get('content', []):
                        if block.get('type') == 'tool_use':
                            commands.append({'line': number, 'id': block.get('id'),
                                             'name': block.get('name'), 'input': block.get('input')})
                if kind == 'error':
                    failures += 1
            except (ValueError, TypeError, AttributeError):
                malformed.append(number)
        final = results[-1] if results else {}
        usable = (len(results) == 1 and final.get('subtype') == 'success'
                  and final.get('is_error') is False and not malformed and not failures)
        usage = final.get('usage') or {}
        # Native input excludes cache reads/writes; normalized input includes both.
        keys = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
        values = [usage.get(k) for k in keys]
        total = sum(values) if all(type(v) is int and v >= 0 for v in values) else None
        output = usage.get('output_tokens')
        cached = usage.get('cache_read_input_tokens')
        normalized = {'input_tokens': total,
                      'cached_input_tokens': cached if type(cached) is int and cached >= 0 else None,
                      'output_tokens': output if type(output) is int and output >= 0 else None}
        allowed_tools = {'Bash', 'Read', 'Write', 'Edit', 'Glob', 'Grep'}
        verified = len(init) == 1 and all(init[0].get(key) == [] for key in ('plugins', 'mcp_servers'))
        verified = verified and isinstance(init[0].get('skills'), list) and set(init[0]['skills']) <= BUNDLED_SKILLS | {'agent-led-swe'}
        verified = verified and set(invocations) <= {'agent-led-swe'}
        verified = verified and isinstance(init[0].get('tools'), list) and set(init[0]['tools']) <= allowed_tools
        # 2.1.278 reports built-in agent names even with no Agent/Task tool.
        # Reject custom agents; catalog presence does not enable delegation.
        builtins = {'claude', 'Explore', 'general-purpose', 'Plan', 'statusline-setup'}
        verified = verified and isinstance(init[0].get('agents'), list) and set(init[0]['agents']) <= builtins
        return {'schema_version': 1, 'event_types': dict(counts), 'malformed_lines': malformed,
                'completion_observed': bool(results), 'telemetry_usable': usable,
                'usage': normalized if usable else {k: None for k in normalized},
                'native_usage': usage, 'native_model_labels': sorted(models),
                'models_observed': sorted({m.removesuffix('[1m]') for m in models}), 'tool_calls': commands,
                'init_context': init,
                'native_skill_invocations': invocations,
                'isolation_status': 'verified-discovery' if verified else 'unknown',
                'client_cost_estimate_usd': final.get('total_cost_usd'),
                'task_status': 'unknown'}

    def conversation_command(self, binary, workspace, model, effort, sandbox, context, session_id=None):
        command = self.command(binary, workspace, model, effort, sandbox, context)
        command.remove('--no-session-persistence')
        if session_id:
            from uuid import UUID
            command += ['--resume', str(UUID(session_id))]
        return command
