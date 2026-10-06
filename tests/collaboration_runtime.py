"""Conversation transport and evidence capture; no prescribed development stages.

The caller owns one isolated runtime for the entire conversation. User responders
receive public messages and snapshots, never the skill condition or verifier.
There is deliberately no model-backed default responder or automatic LLM judge.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import time
from uuid import UUID

from evaluation_runtime import execute, file_hashes, positive_seconds, snapshot, write_json


@dataclass(frozen=True)
class UserReply:
    text: str
    accepted: bool = False

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip() or type(self.accepted) is not bool:
            raise ValueError('A user reply needs nonempty text and an explicit acceptance flag')


def completed_turn(agent, raw):
    """Extract the native conversation ID and final reply, not commentary/tools."""
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    ids, replies = set(), []
    if agent == 'claude-code':
        for event in events:
            if event.get('session_id'):
                ids.add(event['session_id'])
            if event.get('type') == 'result' and event.get('subtype') == 'success' and not event.get('is_error'):
                replies.append(event.get('result', ''))
    elif agent == 'codex':
        for event in events:
            if event.get('type') == 'thread.started':
                ids.add(event['thread_id'])
            if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                replies.append(event['item'].get('text', ''))
    else:
        raise ValueError('Unsupported conversation agent')
    if len(ids) != 1 or not replies or not isinstance(replies[-1], str) or not replies[-1].strip():
        raise ValueError('Native conversation ID or final reply is missing/ambiguous')
    return str(UUID(next(iter(ids)))), replies[-1]


def converse(adapter, binary, runtime_cwd, sandbox, context, model, effort,
             helpers, workspace, output, request, responder, *, invocation='',
             max_turns=12, timeout=3600, turn_timeout=600, user_timeout=120,
             capture=execute, clock=time.monotonic):
    """A user question/review and a final answer both use normal native turns.

    responder(messages, snapshot_path, timeout_seconds) must enforce its own
    I/O timeout. Responses returned after that deadline are never delivered.
    No tool or model call is made by this function except through these drivers.
    """
    if type(max_turns) is not int or max_turns < 1:
        raise ValueError('max_turns must be a positive integer')
    for limit in (timeout, turn_timeout, user_timeout):
        positive_seconds(limit)
    output.mkdir(parents=True, exist_ok=False)
    deadline = clock() + timeout
    messages = [{'role': 'user', 'content': request}]
    session_id, rows = None, []
    result = {'status': 'error', 'accepted': False, 'task_status': 'unknown', 'turns': rows}
    try:
        for number in range(1, max_turns + 1):
            remaining = deadline - clock()
            if remaining <= 0:
                result['status'] = 'timeout'
                break
            turn = output / f'turn-{number:03d}'
            turn.mkdir()
            prompt = turn / 'prompt.txt'
            prompt.write_text((invocation if number == 1 else '') + messages[-1]['content'])
            command = adapter.conversation_command(binary, runtime_cwd, model, effort, sandbox, context, session_id)
            execution = capture(helpers, workspace, turn / 'capture', command,
                                min(turn_timeout, remaining), prompt, adapter)
            row = {'turn': number, 'execution': execution}
            rows.append(row)
            write_json(turn / 'execution.json', execution)
            for path in workspace.rglob('*'):
                if path.is_symlink() and not path.resolve().is_relative_to(workspace.resolve()):
                    raise ValueError('Workspace symlink escapes the public snapshot')
            snapshot_hashes = snapshot(workspace, turn / 'workspace')
            if execution['run_status'] != 'completed':
                result['status'] = execution['run_status']
                break
            if adapter.name == 'claude-code' and (execution.get('isolation_status') != 'verified-discovery'
                                                  or execution.get('models_observed') != [model]):
                raise ValueError('Native model or isolation check failed')
            current_id, reply = completed_turn(adapter.name, (turn / 'capture/stdout.log').read_text())
            if session_id is not None and current_id != session_id:
                raise ValueError('Native conversation changed during resume')
            session_id = current_id
            row['session_id'] = session_id
            messages.append({'role': 'assistant', 'content': reply})
            write_json(output / 'conversation.json', messages)
            remaining = deadline - clock()
            if remaining <= 0:
                result['status'] = 'timeout'
                break
            allowance = min(user_timeout, remaining)
            started = clock()
            # Pass a copy so the responder cannot rewrite earlier conversation.
            answer = responder([dict(m) for m in messages], turn / 'workspace', allowance)
            if file_hashes(turn / 'workspace') != snapshot_hashes:
                raise ValueError('User responder modified its evidence snapshot')
            if clock() - started > allowance or clock() >= deadline:
                result['status'] = 'timeout'
                break
            if not isinstance(answer, UserReply):
                raise ValueError('User service returned an invalid response')
            write_json(turn / 'user-reply.json', {'text': answer.text, 'accepted': answer.accepted})
            messages.append({'role': 'user', 'content': answer.text})
            write_json(output / 'conversation.json', messages)
            if answer.accepted:
                result.update(status='completed', accepted=True)
                break
        else:
            result['status'] = 'turn_limit'
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        result.update(status='error', error=str(exc))
    finally:
        write_json(output / 'result.json', result)
    return result
