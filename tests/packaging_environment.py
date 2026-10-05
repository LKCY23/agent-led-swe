"""Prepare and audit a minimal packaging executor image; verifier image stays intact."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import tarfile
import tempfile

from evaluation_runtime import DEFAULT_EVALUATOR, digest, load_helper, write_json


SCAN = '''from pathlib import Path
import json
roots = [Path(p) for p in ("/usr", "/opt", "/root/.cache", "/tmp", "/var/cache")]
copies = sorted({str(p) for root in roots if root.exists() for p in root.rglob("packaging") if p.is_dir()})
archives = sorted({str(p) for root in roots if root.exists() for p in root.rglob("*packaging*.whl")})
print(json.dumps({"implementation_directories": copies, "package_archives": archives,
                  "scope": "Local runtime roots; /testbed is the allowed task source"}))
'''

SCRUB = '''from pathlib import Path
import json, shutil
removed = []
roots = [Path(p) for p in ("/usr/local/lib", "/opt", "/root/.cache")]
paths = {p for root in roots if root.exists() for p in root.rglob("packaging") if p.is_dir()}
paths |= {p for root in roots if root.exists() for p in root.rglob("packaging-*.dist-info")}
paths |= {Path("/root/.cache/uv"), Path("/root/.cache/pip")}
# Global pip/setuptools would be broken after removing their vendored copies.
# The isolated task venv uses uv and flit_core; no global package manager is needed.
site = Path("/usr/local/lib/python3.10/site-packages")
for pattern in ("pip", "pip-*.dist-info", "setuptools", "setuptools-*.dist-info", "_distutils_hack", "distutils-precedence.pth"):
    paths.update(site.glob(pattern))
paths.update(Path("/usr/local/bin").glob("pip*"))
for p in sorted(paths, key=lambda p: len(p.parts), reverse=True):
    if p.is_symlink() or p.is_file():
        p.unlink(); removed.append(str(p))
    elif p.is_dir():
        shutil.rmtree(p); removed.append(str(p))
Path("/opt/packaging-scrub.json").write_text(json.dumps(removed, indent=2))
'''


def audit_image(image):
    data = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--read-only',
        '--entrypoint', '/usr/local/bin/python', image, '-c', SCAN], text=True, timeout=45)
    return json.loads(data)


def audit_container(container, import_task=True):
    data = subprocess.check_output(['docker', 'exec', container, '/usr/local/bin/python', '-c', SCAN],
                                   text=True, timeout=45)
    audit = json.loads(data)
    if import_task:
        audit['task_import'] = subprocess.check_output(['docker', 'exec', container, 'python', '-c',
            'import packaging; print(packaging.__file__)'], text=True, timeout=15).strip()
    return audit


def clean(audit):
    return not audit['implementation_directories'] and not audit['package_archives']


def build_executor(base, output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = output / 'build'
    build.mkdir()
    (build / 'scrub.py').write_text(SCRUB)
    tag_base = 'agent-led-swe-clean-base:' + base.removeprefix('sha256:')
    subprocess.run(['docker', 'tag', base, tag_base], check=True)
    (build / 'Dockerfile').write_text(f'FROM {tag_base}\n'
        'COPY scrub.py /tmp/scrub.py\nRUN /usr/local/bin/python /tmp/scrub.py && rm /tmp/scrub.py\n'
        'ENV UV_NO_CACHE=1\n')
    tag = 'agent-led-swe-packaging-executor:' + digest(build / 'Dockerfile')[:12] + '-' + digest(build / 'scrub.py')[:12]
    capture = load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture
    result = capture(build, output / 'build-log', ['docker', 'build', '-t', tag, str(build)], 300)
    if result['exit_code'] != 0 or result['timed_out']:
        raise RuntimeError('Clean executor build failed; retained build log has details')
    image = subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()
    audit = audit_image(image)
    report = {'base_verifier_image': base, 'executor_image': image,
              'local_source_audit': audit, 'local_source_audit_passed': clean(audit),
              'qualified': False, 'reason': 'Control/reference revalidation still required'}
    write_json(output / 'report.json', report)
    return report


def qualify_executor(report, inputs, output):
    """Reproduce qualification from frozen data, with no Agent/model calls."""
    from task_adapters import ROOT, prepare_variants, test_items
    from functional_checks import run_test_groups, functional_status
    from evaluation_runtime import build_worker_image, execution_environment
    from model_config import CONFIGS, load_profile
    output = output.resolve()
    spec = json.loads((ROOT / 'tests/cases/swe/packaging.json').read_text())
    old = next(c for c in json.loads((ROOT / 'tests/reports/swe-preflight-2026-10-05.json').read_text())['cases']
               if c['name'] == 'packaging')
    if old['spec'] != spec or old['image_id'] != report['base_verifier_image']:
        raise ValueError('Base image or task differs from the qualified verifier')
    row = inputs / (spec['instance_id'] + '.json')
    archive = inputs / spec['instance_id'] / 'source.tar.gz'
    if digest(row) != spec['metadata_sha256'] or digest(archive) != spec['source_sha256']:
        raise ValueError('Frozen source data changed')
    metadata = json.loads(row.read_text())
    with tarfile.open(archive) as tar:
        tar.extractall(output / 'source', filter='data')
    variants = output / 'variants'
    variants.mkdir()
    control, reference = prepare_variants(next((output / 'source').iterdir()), metadata, variants, True)
    groups = {g: test_items(metadata[g]) for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')}
    report.update(spec=spec, runs=[], worker_checks=[], evidence=str(output), qualified=False)
    for label, template in [('control', control), ('reference', reference)]:
        for repetition in (1, 2):
            workspace = output / f'{label}-{repetition}'
            shutil.copytree(template, workspace)
            rows = run_test_groups(workspace, output / f'{label}-{repetition}-results',
                                   {'image': report['executor_image'], 'network': 'none'}, groups)
            report['runs'] += [{'variant': label, 'repetition': repetition, **r} for r in rows]
            write_json(output / 'report.json', report)
            expected = ['fail', 'pass'] if label == 'control' else ['pass', 'pass']
            if [functional_status(r) for r in rows] != expected:
                raise RuntimeError('Control/reference qualification failed; inspect retained test logs')
            for r in rows:
                original = [x for x in old['runs'] if x['variant'] == label and x['group'] == r['group']]
                if not original or any(x['outcome_sha256'] != r['outcome_sha256'] for x in original):
                    raise RuntimeError('Verifier outcomes differ from original qualification')
            print(label, repetition, expected, flush=True)
    versions = json.loads((CONFIGS / 'agents.json').read_text())
    for agent in ('codex', 'claude-code'):
        evidence = output / agent
        evidence.mkdir()
        environment = {'kind': 'docker', 'image': report['base_verifier_image'],
                       'execution_image': report['executor_image'], 'audit_packaging_sources': True}
        environment['worker_image'] = build_worker_image(environment, versions[agent]['version'], evidence / 'worker-build', agent)
        profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json') if agent == 'claude-code' else None
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp).resolve()
            shutil.copytree(variants / 'learner', workspace, dirs_exist_ok=True)
            with execution_environment({'environment': environment}, workspace, evidence,
                    {'agent': agent, 'version': versions[agent]['version']}, authenticate=False, model_profile=profile) as runtime:
                binary, _, _, _ = runtime
                version = subprocess.check_output(binary[:-1] + ['python', '-m', 'pytest', '--version'], text=True, timeout=30)
        report['worker_checks'].append({'agent': agent, 'version': versions[agent]['version'],
            'worker_image': environment['worker_image'], 'status': 'passed', 'pytest_version': version.strip()})
        write_json(output / 'report.json', report)
    report.update(qualified=True, reason='Repeated control/reference checks and both worker audits passed',
                  scope='Local installed/vendored/archive/cache source audit; not network egress isolation')
    write_json(output / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, help='Frozen source data; also run complete control/reference and worker qualification')
    args = parser.parse_args()
    report = build_executor(args.base_image, args.output)
    if args.inputs and report['local_source_audit_passed']:
        report = qualify_executor(report, args.inputs.resolve(), args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if (report['qualified'] if args.inputs else report['local_source_audit_passed']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
