"""Claude Code headless execution inside a disposable Docker worker."""
from collections import Counter
import json
import re
from model_config import claude_model, allow_subagents

DELEGATION_TOOLS = {'Task', 'Agent', 'Workflow'}


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
        command = list(binary) + ['--print', '--no-session-persistence',
            '--input-format', 'stream-json', '--replay-user-messages',
            '--output-format', 'stream-json', '--verbose', '--forward-subagent-text',
            '--model', claude_model(model), '--effort', effort,
            '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--no-chrome',
            '--tools', 'default', '--permission-mode', 'bypassPermissions']
        if not allow_subagents(context):
            command += ['--disallowedTools', ','.join(sorted(DELEGATION_TOOLS))]
        return command

    def inspect_trace(self, text, helpers=None):
        counts, malformed, results, models, init = Counter(), [], [], set(), []
        commands = []
        invocations = []
        failures = 0
        child_events = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                    raise ValueError('Not an event')
                kind = event['type']
                if (kind in {'assistant', 'user'} and event.get('parent_tool_use_id')) or (kind == 'system' and event.get('subtype') == 'task_started'
                                                       and event.get('subagent_type')):
                    child_events.append(number)
                counts[kind] += 1
                if kind == 'system' and event.get('subtype') == 'init' and not event.get('parent_tool_use_id'):
                    init.append(event)
                if kind == 'result' and not event.get('parent_tool_use_id'):
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
        # Background-task notifications can trigger another native result in the
        # same print process. Keep the final cumulative receipt, not their sum.
        result_ids = {r.get('uuid') for r in results}
        single_session = len({r.get('session_id') for r in results}) <= 1
        distinct = len(results) == 1 or (None not in result_ids and len(result_ids) == len(results))
        usable = (bool(results) and single_session and distinct
                  and all(r.get('subtype') == 'success' and r.get('is_error') is False for r in results)
                  and not malformed and not failures)
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
        scope = 'native_final_result'
        model_usage = final.get('modelUsage') or {}
        fields = ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')
        if model_usage and all(all(type(v.get(k)) is int and v[k] >= 0 for k in fields)
                               for v in model_usage.values()):
            # Includes child calls and native follow-up turns. On resume this
            # receipt includes earlier calls; the conversation driver takes deltas.
            normalized = {
                'input_tokens': sum(v['inputTokens'] + v['cacheReadInputTokens'] + v['cacheCreationInputTokens']
                                    for v in model_usage.values()),
                'cached_input_tokens': sum(v['cacheReadInputTokens'] for v in model_usage.values()),
                'output_tokens': sum(v['outputTokens'] for v in model_usage.values())}
            scope = 'session_cumulative'
        context_keys = ('session_id', 'model', 'skills', 'tools', 'agents', 'plugins', 'mcp_servers')
        contexts = {json.dumps({key: e.get(key) for key in context_keys}, sort_keys=True) for e in init}
        verified = len(contexts) == 1 and all(init[0].get(key) == [] for key in ('plugins', 'mcp_servers'))
        # Fresh HOME and the frozen public workspace define discovery scopes.
        # Project skills/agents and native tools are task capabilities, not leaks.
        verified = verified and all(isinstance(init[0].get(key), list)
                                    for key in ('skills', 'tools', 'agents'))
        return {'schema_version': 1, 'event_types': dict(counts), 'malformed_lines': malformed,
                'completion_observed': bool(results), 'telemetry_usable': usable,
                'usage': normalized if usable else {k: None for k in normalized},
                'usage_scope': scope,
                'native_usage': usage, 'native_model_labels': sorted(models),
                'native_model_usage': final.get('modelUsage', {}),
                'models_observed': sorted({m.removesuffix('[1m]') for m in models}), 'tool_calls': commands,
                'init_context': init[:1] if len(contexts) == 1 else init,
                'native_init_events': init,
                'subagent_event_lines': child_events,
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
