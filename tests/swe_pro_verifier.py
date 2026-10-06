"""Run unmodified SWE-bench Pro V2 verification on a pristine task image."""
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from container_workspace import install_workspace
from evaluation_runtime import DEFAULT_EVALUATOR, load_helper, write_json
from suite_tasks import selectors


def official_status(record, reward, data, required):
    if (record['timed_out'] or record['exit_code'] not in (0, 1) or not required
            or not isinstance(data, dict) or not isinstance(data.get('tests'), list)):
        return 'unknown'
    passed = {t.get('name') for t in data['tests'] if t.get('status') == 'PASSED'}
    expected = required <= passed
    if expected and (reward, record['exit_code']) == ('1', 0):
        return 'pass'
    if not expected and (reward, record['exit_code']) == ('0', 1):
        return 'fail'
    return 'unknown'


def run_pro_checks(artifacts, trusted, environment, output, supplemental=(), timeout=600):
    output.mkdir(parents=True, exist_ok=False)
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    container = 'swe-pro-check-' + uuid.uuid4().hex[:12]
    workdir = environment['workdir']
    argv = ['docker', 'run', '-d', '--name', container, '--platform', environment['platform'],
            '--network', 'none', '--cpus', '2', '--memory', '4g',
            '-v', f'{trusted.resolve()}/tests:/tests:ro',
            '-v', f'{output.resolve()}:/logs/verifier', '-w', workdir,
            environment['image'], 'sleep', '86400']
    subprocess.run(argv, check=True, capture_output=True)
    checks = []
    try:
        config = json.loads((trusted / 'tests/config.json').read_text())
        required = set(selectors(config['fail_to_pass']) + selectors(config['pass_to_pass']))
        base_files = json.loads((trusted / 'public-files.json').read_text())
        install_workspace(container, artifacts, workdir, base_files)
        result = capture(artifacts, output / 'official-capture',
                         ['docker', 'exec', container, 'bash', '/tests/test.sh'], timeout)
        reward = output / 'reward.txt'
        parsed = output / 'output.json'
        state = 'unknown'
        data = None
        if parsed.is_file():
            data = json.loads(parsed.read_text())
        if reward.is_file():
            state = official_status(result, reward.read_text().strip(), data, required)
        outcomes = sorted((t.get('name'), t.get('status')) for t in (data or {}).get('tests', []))
        checks.append({'id': 'OFFICIAL', 'status': state, 'reason': 'Unmodified SWE-bench Pro V2 verifier',
            'evidence': [str(output)], 'details': {'exit_code': result['exit_code'],
                'timed_out': result['timed_out'], 'parsed_tests': len(outcomes),
                'outcome_sha256': hashlib.sha256(json.dumps(outcomes).encode()).hexdigest()}})
        for check in supplemental:
            record = capture(artifacts, output / check['id'],
                             ['docker', 'exec', container, *check['argv']], timeout)
            status = ('unknown' if record['timed_out'] or record['exit_code'] not in (0, 1)
                      else 'pass' if record['exit_code'] == 0 else 'fail')
            checks.append({'id': check['id'], 'status': status,
                'reason': 'Supplemental original-project regression; separate from official reward',
                'evidence': [str(output / check['id'])],
                'details': {'exit_code': record['exit_code'], 'timed_out': record['timed_out']}})
    finally:
        subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
    write_json(output / 'checks.json', checks)
    return checks
