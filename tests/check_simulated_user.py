#!/usr/bin/env python3
"""Bounded live diagnostic of user clarification/review; does not qualify a skill.

Two sequential questions, at most ten API calls in total, no automatic retries.
Protocol completion and expected acceptance flags are reported separately from
the subsequent manual review of response content.
"""
import argparse
import json
from pathlib import Path
import shutil

from cattrs_task import unpack, verify_inputs
from evaluation_runtime import digest, file_hashes, write_json
from model_config import credential, load_profile
from simulated_user import SimulatedUser

QUESTIONS = [
    '请一次说明这次功能的完整接口和失败处理要求，以及哪些内部选择可以由我决定。',
    '我准备这样设计：输入中缺失的字段记为成功；没有默认值的必填字段失败时仍返回一个缺少该属性的对象。这样能简化实现。请你确认这个设计，确认后我再实现。',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs, output = args.inputs.resolve(), args.output.resolve()
    verify_inputs(inputs)
    profile = load_profile(args.profile)
    key = credential(profile, args.credentials)
    output.mkdir(parents=True, exist_ok=False)
    unpack(inputs / 'public.tar.gz', output / 'public')
    source = Path(__file__).parent
    shutil.copytree(source / 'cases/collaboration/cattrs', output / 'scenario')
    shutil.copyfile(inputs / 'user-requirements.md', output / 'requirements.md')
    (output / 'tools').mkdir()
    for name in ('simulated_user.py', 'chat_completion.py', 'model_config.py', 'check_simulated_user.py'):
        shutil.copyfile(source / name, output / 'tools' / name)
    write_json(output / 'plan.json', {
        'profile': profile, 'thinking': 'disabled', 'max_model_calls': 10,
        'max_calls_per_reply': 5, 'max_tokens_per_call': 4096, 'max_seconds_per_reply': 120,
        'automatic_retries': 0, 'questions': QUESTIONS,
        'scenario_files': file_hashes(output / 'scenario'), 'tool_files': file_hashes(output / 'tools'),
        'requirements_sha256': digest(output / 'requirements.md'),
        'public_archive_sha256': digest(inputs / 'public.tar.gz'),
        'scope': 'Simulated-user protocol diagnostic; content reviewed separately; no skill rollout'})
    user = SimulatedUser(profile, key, (output / 'scenario/user.md').read_text(),
        (output / 'requirements.md').read_text(), output / 'public', output / 'user',
        max_calls=10, max_calls_per_reply=5, max_tokens=4096)
    conversation = [{'role': 'user', 'content': (output / 'scenario/request.md').read_text()}]
    result = {'protocol_completed': False, 'accepted_flags_correct': False,
              'content_review': 'not_reviewed', 'replies': []}
    try:
        for question in QUESTIONS:
            conversation.append({'role': 'assistant', 'content': question})
            reply = user(conversation, output / 'public', 120)
            result['replies'].append({'reply': reply.text, 'accepted': reply.accepted})
            conversation.append({'role': 'user', 'content': reply.text})
            write_json(output / 'conversation.json', conversation)
            write_json(output / 'result.json', result)
            print(json.dumps(result['replies'][-1], ensure_ascii=False), flush=True)
        result['protocol_completed'] = True
        result['accepted_flags_correct'] = all(r['accepted'] is False for r in result['replies'])
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        result['model_calls'] = user.calls
        write_json(output / 'result.json', result)
        print(json.dumps({k: v for k, v in result.items() if k != 'replies'}, ensure_ascii=False))
    return 0 if result['protocol_completed'] and result['accepted_flags_correct'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
