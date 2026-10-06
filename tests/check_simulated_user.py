#!/usr/bin/env python3
"""Live native CC user smoke: clarify requirements, then read/review a draft.

No solver rollout. Two replies, each limited to 180 seconds.
"""
import argparse
import json
from pathlib import Path
import shutil

from cattrs_task import unpack, verify_inputs
from evaluation_runtime import build_worker_image, digest, file_hashes, write_json
from model_config import CONFIGS, load_profile
from simulated_user import SimulatedUser

QUESTIONS = [
    '请一次说明这次功能的完整接口和失败处理要求，以及哪些内部选择可以由我决定。',
    '我还没有开始实现。接口草案写在 docs/native-user-review-probe.md，请读取该文件，指出需要修改的地方。这一轮只是设计审阅，不是最终交付。',
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
    output.mkdir(parents=True, exist_ok=False)
    unpack(inputs / 'public.tar.gz', output / 'public')
    shutil.copytree(output / 'public', output / 'review')
    (output / 'review/docs/native-user-review-probe.md').write_text(
        '# 待审阅接口草案\n\n输入缺失的字段记为成功。必填且没有默认值的字段失败时，返回一个缺少该属性的对象。\n')
    source = Path(__file__).parent
    shutil.copytree(source / 'cases/collaboration/cattrs', output / 'scenario')
    shutil.copyfile(inputs / 'user-requirements.md', output / 'requirements.md')
    environment = json.loads((inputs / 'environment.json').read_text())
    cli = {'agent': 'claude-code', 'version': json.loads((CONFIGS / 'agents.json').read_text())['claude-code']['version']}
    environment['worker_image'] = build_worker_image(environment, cli['version'], output / 'build', 'claude-code')
    (output / 'tools').mkdir()
    for name in ('simulated_user.py', 'model_config.py', 'evaluation_runtime.py', 'check_simulated_user.py'):
        shutil.copyfile(source / name, output / 'tools' / name)
    write_json(output / 'plan.json', {'profile': profile, 'cli': cli, 'environment': environment,
        'max_seconds_per_reply': 180, 'max_replies': 2,
        'structured_output_retries': 1, 'questions': QUESTIONS,
        'scenario_files': file_hashes(output / 'scenario'), 'tool_files': file_hashes(output / 'tools'),
        'requirements_sha256': digest(output / 'requirements.md'),
        'public_archive_sha256': digest(inputs / 'public.tar.gz'),
        'scope': 'Native CC user smoke; no solver rollout'})
    conversation = [{'role': 'user', 'content': (output / 'scenario/request.md').read_text()}]
    result = {'protocol_completed': False, 'accepted_flags_correct': False, 'content_review': 'not_reviewed', 'replies': []}
    try:
        with SimulatedUser(profile, (output / 'scenario/user.md').read_text(), (output / 'requirements.md').read_text(),
                output / 'public', output / 'user', environment, cli, args.credentials,
                max_replies=2) as user:
            for index, question in enumerate(QUESTIONS):
                conversation.append({'role': 'assistant', 'content': question})
                reply = user(conversation, output / ('public' if index == 0 else 'review'), 180)
                result['replies'].append({'reply': reply.text, 'accepted': reply.accepted})
                conversation.append({'role': 'user', 'content': reply.text})
                write_json(output / 'conversation.json', conversation)
                write_json(output / 'result.json', result)
                print(json.dumps(result['replies'][-1], ensure_ascii=False), flush=True)
            result.update(protocol_completed=True, accepted_flags_correct=all(not r['accepted'] for r in result['replies']),
                          native_session_id=user.session)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    write_json(output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'replies'}, ensure_ascii=False))
    return 0 if result['protocol_completed'] and result['accepted_flags_correct'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
