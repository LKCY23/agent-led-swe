"""Prepare and audit a minimal packaging executor image; verifier image stays intact."""
import argparse
import json
from pathlib import Path
import subprocess

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build_executor(args.base_image, args.output)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['local_source_audit_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
