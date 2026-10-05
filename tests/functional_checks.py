"""Run trusted functional checks against a copy of submitted artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

from evaluation_runtime import DEFAULT_EVALUATOR, load_helper, write_json


def run_test_groups(workspace, evidence, environment, groups, timeout=180):
    """Shared by benchmark preflight and evaluation; never edits the submitted snapshot."""
    evidence.mkdir(parents=True, exist_ok=False)
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    container = 'swe-check-' + uuid.uuid4().hex[:12]
    command = ['docker', 'run', '-d', '--name', container, '--network', environment.get('network', 'none'),
               '--cpus', '2', '--memory', '3g', '-v', f'{workspace}:/testbed',
               '-v', f'{evidence}:/results', '-w', '/testbed',
               '-e', 'SETUPTOOLS_SCM_PRETEND_VERSION=7.2.0.dev0', environment['image'], 'sleep', '900']
    subprocess.run(command, check=True, capture_output=True)
    results = []
    try:
        install = capture(workspace, evidence / 'install', ['docker', 'exec', container,
            'uv', 'pip', 'install', '--python', '/opt/testenv/bin/python', '--no-deps',
            '--no-build-isolation', '-e', '/testbed'], 90)
        if install['exit_code'] != 0 or install['timed_out']:
            raise RuntimeError(f'Environment installation failed: {evidence / "install"}')
        packages = subprocess.check_output(['docker', 'exec', container, 'uv', 'pip', 'freeze',
                                            '--python', '/opt/testenv/bin/python'], text=True)
        (evidence / 'packages.txt').write_text(packages)
        for group, selectors in groups.items():
            if group not in ('FAIL_TO_PASS', 'PASS_TO_PASS') or not selectors:
                raise ValueError('A functional check needs a named nonempty selector list')
            argv = ['docker', 'exec', container, 'python', '-m', 'pytest', '-q', '--color=no',
                    f'--junitxml=/results/{group}.xml', *selectors]
            outcome = capture(workspace, evidence / group, argv, timeout)
            result = {'group': group, 'exit_code': outcome['exit_code'],
                      'timed_out': outcome['timed_out'], 'elapsed_seconds': outcome['elapsed_seconds'],
                      'counts': xml_counts(evidence / f'{group}.xml'),
                      'outcome_sha256': xml_fingerprint(evidence / f'{group}.xml')}
            results.append(result)
            write_json(evidence / 'results.json', results)
            if outcome['timed_out'] or outcome['exit_code'] not in (0, 1):
                break
    finally:
        subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
    return results


def functional_status(result):
    counts = result.get('counts')
    if not counts or not counts['tests'] or result['timed_out']:
        return 'unknown'
    # Test exceptions need diagnosis: they may originate in the submission or environment.
    if counts['errors'] or counts['skipped'] or result['exit_code'] not in (0, 1):
        return 'unknown'
    if counts['failures']:
        return 'fail'
    if result['group'] == 'FAIL_TO_PASS' and counts.get('xfailed', 0):
        return 'unknown'
    return 'pass' if result['exit_code'] == 0 else 'unknown'


def validate_task(task, bundle, artifacts, output):
    """Run the task's frozen validator; a second call uses a new output directory."""
    validation = task.get('validation')
    if not validation:
        return []
    if validation['kind'] != 'pytest':
        raise ValueError('Unsupported functional validator')
    output.mkdir(parents=True, exist_ok=False)
    checks = []
    with tempfile.TemporaryDirectory(prefix='swe-validation-') as tmp:
        workspace = Path(tmp).resolve() / 'workspace'
        for p in artifacts.rglob('*'):
            if p.is_symlink() and not p.resolve().is_relative_to(artifacts.resolve()):
                raise ValueError('Submitted symlink escapes the artifact workspace')
        shutil.copytree(artifacts, workspace, symlinks=True)
        trusted = bundle / validation['overlay']
        # Replace trusted test trees, retaining the submitted version in the immutable artifact.
        for name in validation['test_roots']:
            target = workspace / name
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            shutil.copytree(trusted / name, target)
        try:
            results = run_test_groups(workspace, output / 'run', task['environment'], validation['groups'])
            for group in validation['groups']:
                result = next((r for r in results if r['group'] == group), None)
                status = functional_status(result) if result else 'unknown'
                reason = 'Trusted functional check; errors/skips need diagnosis'
                expected = validation.get('expected_outcomes', {}).get(group)
                if status == 'pass' and expected and result['outcome_sha256'] != expected:
                    status, reason = 'unknown', 'Test identities/outcomes differ from qualified reference'
                checks.append({'id': group, 'status': status, 'reason': reason,
                    'evidence': [str(output / 'run' / group)], 'details': result})
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            checks = [{'id': g, 'status': 'unknown', 'reason': str(exc), 'evidence': [str(output)]}
                      for g in validation['groups']]
    write_json(output / 'checks.json', checks)
    return checks

def xml_counts(path):
    if not path.is_file():
        return None
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    xfailed = sum(s.get('type') == 'pytest.xfail' for s in root.iter('skipped'))
    return {'tests': len(cases), 'failures': len(list(root.iter('failure'))),
            'errors': len(list(root.iter('error'))),
            'skipped': len(list(root.iter('skipped'))) - xfailed, 'xfailed': xfailed}



def xml_fingerprint(path):
    if not path.is_file():
        return None
    rows = [(c.get('classname', ''), c.get('name', ''),
             next((tag + ':' + c.find(tag).get('type', '')
                   for tag in ('failure', 'error', 'skipped') if c.find(tag) is not None), 'pass'))
            for c in ET.parse(path).getroot().iter('testcase')]
    return hashlib.sha256(json.dumps(sorted(rows), ensure_ascii=False).encode()).hexdigest()
