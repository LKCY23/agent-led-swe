"""Task-grounded simulated user with read-only snapshot tools; never a grader."""
import difflib
import json
from pathlib import Path
import time

from chat_completion import complete
from collaboration_runtime import UserReply
from evaluation_runtime import digest, write_json


def tool(name, description, properties=None, required=()):
    return {'type': 'function', 'function': {'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties or {}, 'required': list(required), 'additionalProperties': False}}}


TOOLS = [
    tool('list_files', '列出当前公开工作区文件；offset 用于分页。',
         {'prefix': {'type': 'string'}, 'offset': {'type': 'integer'}}),
    tool('list_changes', '列出相对初始工作区新增、删除和修改的文件。'),
    tool('read_file', '按行读取当前文件。仅可读工作区相对路径。',
         {'path': {'type': 'string'}, 'start': {'type': 'integer'}, 'lines': {'type': 'integer'}}, ('path',)),
    tool('read_diff', '读取一个文件相对初始工作区的 unified diff，offset 按字符分页。',
         {'path': {'type': 'string'}, 'offset': {'type': 'integer'}}, ('path',)),
    tool('respond_to_agent', '发送本轮最终回复。accepted 仅表示接受最终交付并结束整个协作；同意方案或允许继续必须为 false。',
         {'reply': {'type': 'string'}, 'accepted': {'type': 'boolean'}}, ('reply', 'accepted')),
]
EXCLUDED = {'.git', '.venv', '__pycache__', '.pytest_cache', '.hypothesis', '.benchmarks'}


def normalize_calls(calls):
    """Handle the observed DeepSeek call(function=..., ...) wrapper explicitly.

    Only declared tool names are normalized; argument validation remains unchanged.
    Raw API responses and this normalized representation are both retained.
    """
    names = {entry['function']['name'] for entry in TOOLS}
    result = []
    for entry in calls:
        function = entry['function']
        if function['name'] == 'call':
            arguments = json.loads(function['arguments'])
            if isinstance(arguments, dict) and arguments.get('function') in names:
                arguments = dict(arguments)
                name = arguments.pop('function')
                entry = {**entry, 'function': {'name': name, 'arguments': json.dumps(arguments)}}
        result.append(entry)
    return result


class SnapshotReader:
    def __init__(self, initial, current):
        self.initial, self.current = Path(initial).resolve(), Path(current).resolve()
        self.read_count = 0

    def path(self, root, name):
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            raise ValueError('Only nonempty relative paths are allowed')
        rel = Path(name)
        if '..' in rel.parts or EXCLUDED.intersection(rel.parts):
            raise ValueError('Path is outside the public file view')
        path = root / rel
        if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in [path, *path.parents] if p != root):
            raise ValueError('Symlink access is not supported')
        return path

    def files(self, root):
        files = {}
        for p in root.rglob('*'):
            relative = p.relative_to(root)
            if EXCLUDED.intersection(relative.parts) or p.is_symlink() or not p.is_file():
                continue
            self.path(root, str(relative))
            files[str(relative)] = digest(p)
        return files

    def text(self, root, name, missing=False):
        path = self.path(root, name)
        if missing and not path.exists():
            return ''
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('File unavailable or exceeds the 2 MiB read limit')
        return path.read_text(encoding='utf-8')

    def call(self, name, args):
        if not isinstance(args, dict):
            raise ValueError('Tool arguments must be an object')
        allowed = {'list_files': {'prefix', 'offset'}, 'list_changes': set(),
                   'read_file': {'path', 'start', 'lines'}, 'read_diff': {'path', 'offset'}}
        if name not in allowed or args.keys() - allowed[name]:
            raise ValueError('Unknown tool or arguments')
        for key in ('offset', 'start', 'lines'):
            if key in args and (type(args[key]) is not int or args[key] < (1 if key in ('start', 'lines') else 0)):
                raise ValueError('Invalid range')
        if name == 'list_files':
            prefix = args.get('prefix', '')
            if not isinstance(prefix, str):
                raise ValueError('prefix must be a string')
            values = [p for p in sorted(self.files(self.current)) if p.startswith(prefix)]
            offset = args.get('offset', 0)
            return {'files': values[offset:offset+200], 'total': len(values), 'next_offset': offset+200 if offset+200 < len(values) else None}
        if name == 'list_changes':
            before, after = self.files(self.initial), self.files(self.current)
            return {'added': sorted(after.keys()-before.keys()), 'removed': sorted(before.keys()-after.keys()),
                    'modified': sorted(k for k in before.keys() & after.keys() if before[k] != after[k])}
        path = args.get('path')
        if name == 'read_file':
            lines = self.text(self.current, path).splitlines()
            start, count = args.get('start', 1), min(args.get('lines', 160), 300)
            selected, size = [], 0
            for index in range(start-1, min(len(lines), start-1+count)):
                line = f'{index+1}: {lines[index]}'
                if size + len(line) > 16000:
                    break
                selected.append(line)
                size += len(line)
            self.read_count += 1
            next_line = start + len(selected)
            return {'path': path, 'content': '\n'.join(selected), 'total_lines': len(lines),
                    'next_line': next_line if next_line <= len(lines) else None}
        before, after = self.text(self.initial, path, True), self.text(self.current, path, True)
        diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='before/'+path, tofile='current/'+path))
        offset = args.get('offset', 0)
        self.read_count += 1
        return {'path': path, 'diff': diff[offset:offset+16000],
                'next_offset': offset+16000 if offset+16000 < len(diff) else None}


class SimulatedUser:
    def __init__(self, profile, key, persona, requirements, initial, evidence, *,
                 max_calls=40, max_calls_per_reply=5, max_tokens=4096, effort='none', transport=complete):
        if profile['protocol'] != 'chat-completions':
            raise ValueError('Simulated user requires a Chat Completions profile')
        if profile['provider'] != 'deepseek' or effort != 'none':
            raise ValueError('Typed user replies require DeepSeek non-thinking mode with required tool choice')
        for value in (max_calls, max_calls_per_reply, max_tokens):
            if type(value) is not int or value < 1:
                raise ValueError('User budgets must be positive integers')
        self.profile, self.key, self.transport = profile, key, transport
        self.system = persona + '\n\n# 固定任务要求\n\n' + requirements
        self.initial, self.evidence = initial, evidence
        self.max_calls, self.max_calls_per_reply, self.max_tokens = max_calls, max_calls_per_reply, max_tokens
        self.calls, self.replies, self.effort = 0, 0, effort
        self.usage = []
        evidence.mkdir(parents=True, exist_ok=False)

    def __call__(self, conversation, current, timeout):
        self.replies += 1
        turn = self.evidence / f'reply-{self.replies:03d}'
        turn.mkdir()
        deadline = time.monotonic() + timeout
        reader = SnapshotReader(self.initial, current)
        messages = [{'role': 'system', 'content': self.system}, {'role': 'user', 'content':
            '以下是你与开发 Agent 的完整公开对话，请回应最后一条消息。\n' + json.dumps(conversation, ensure_ascii=False)}]
        try:
            for index in range(self.max_calls_per_reply):
                if self.calls >= self.max_calls or time.monotonic() >= deadline:
                    raise TimeoutError('Simulated-user budget exhausted')
                last_call = index == self.max_calls_per_reply - 1 or self.calls == self.max_calls - 1
                choice = ({'type': 'function', 'function': {'name': 'respond_to_agent'}}
                          if last_call else 'required')
                payload = {'model': self.profile['model'], 'messages': messages,
                           'tools': [TOOLS[-1]] if last_call else TOOLS,
                           'stream': False, 'max_tokens': self.max_tokens,
                           'tool_choice': choice, 'thinking': {'type': 'disabled'}}
                call = turn / f'call-{index+1:02d}'
                call.mkdir()
                write_json(call / 'request.json', payload)
                self.calls += 1
                response = self.transport(self.profile, self.key, payload, deadline-time.monotonic())
                write_json(call / 'response.json', response)
                if response.get('model') != self.profile['model']:
                    raise ValueError('Simulated-user response model differs from the frozen profile')
                self.usage.append(response.get('usage'))
                choices = response.get('choices')
                if not isinstance(choices, list) or len(choices) != 1:
                    raise ValueError('Missing or ambiguous simulated-user choice')
                choice = choices[0]
                message = choice['message']
                if choice['finish_reason'] == 'tool_calls':
                    calls = message.get('tool_calls', [])
                    if not calls or len(calls) > 8:
                        raise ValueError('Invalid simulated-user tool batch')
                    calls = normalize_calls(calls)
                    write_json(call / 'normalized-tools.json', calls)
                    offered = {t['function']['name'] for t in payload['tools']}
                    if any(c['function']['name'] not in offered for c in calls):
                        raise ValueError('Simulated user called a tool not offered in this request')
                    if any(c['function']['name'] == 'respond_to_agent' for c in calls):
                        if len(calls) != 1:
                            raise ValueError('Send the final reply after completing file inspection')
                        reply = json.loads(calls[0]['function']['arguments'])
                        return self.reply(reply, reader)
                    messages.append({**{k: v for k, v in message.items() if k in ('role', 'content', 'reasoning_content')}, 'tool_calls': calls})
                    records = []
                    for entry in calls:
                        function = entry['function']
                        try:
                            result = reader.call(function['name'], json.loads(function['arguments']))
                        except (OSError, UnicodeError, ValueError) as exc:
                            result = {'error': str(exc)}
                        records.append({'tool': function, 'result': result})
                        messages.append({'role': 'tool', 'tool_call_id': entry['id'], 'content': json.dumps(result, ensure_ascii=False)})
                    write_json(call / 'tools.json', records)
                    continue
                if choice['finish_reason'] != 'stop':
                    raise ValueError('Simulated-user response was truncated or interrupted')
                reply = json.loads(message['content'])
                return self.reply(reply, reader)
            raise TimeoutError('Simulated-user tool round limit reached')
        except Exception as exc:
            write_json(turn / 'error.json', {'type': type(exc).__name__, 'message': str(exc)})
            if isinstance(exc, (OSError, ValueError, RuntimeError, TimeoutError)):
                raise
            raise ValueError('Malformed simulated-user response; see retained evidence') from exc
        finally:
            write_json(self.evidence / 'usage.json', {'calls': self.calls, 'replies': self.replies,
                                                    'per_call_usage': self.usage})

    @staticmethod
    def reply(reply, reader):
        if not isinstance(reply, dict) or set(reply) != {'reply', 'accepted'}:
            raise ValueError('Expected reply/accepted JSON from simulated user')
        answer = UserReply(reply['reply'], reply['accepted'])
        if answer.accepted and reader.read_count == 0:
            raise ValueError('Final acceptance requires inspecting current artifacts')
        return answer
