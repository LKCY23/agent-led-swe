"""Frozen input/qualification contracts for the four selected benchmark tasks."""
from pathlib import Path
import ast
import json
import tarfile

from evaluation_runtime import digest, file_hashes


NAMES = ('smolagents', 'xarray', 'nodebb', 'navidrome')
ROOT = Path(__file__).resolve().parents[1]


def github_patch(files):
    """Reconstruct complete diffs from FeatBench's GitHub per-file records."""
    chunks = []
    for item in files:
        name, status = item['filename'], item['status']
        if Path(name).is_absolute() or '..' in Path(name).parts or '\n' in name:
            raise ValueError('Unsafe patch filename')
        if status not in ('modified', 'added', 'removed') or not item.get('patch'):
            raise ValueError(f'Unsupported or missing file patch: {name}')
        before = '/dev/null' if status == 'added' else 'a/' + name
        after = '/dev/null' if status == 'removed' else 'b/' + name
        chunks.append(f'diff --git a/{name} b/{name}\n--- {before}\n+++ {after}\n'
                      + item['patch'].rstrip('\n') + '\n')
    return ''.join(chunks)


def selectors(raw):
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str):
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            if raw.lstrip().startswith('['):
                values = ast.literal_eval(raw)
            else:
                # Author FeatBench v1 stores node IDs separated by comma + space.
                values = raw.split(', ')
    else:
        raise ValueError('Missing benchmark test selector list')
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError('Malformed benchmark test selectors')
    return values


def load_spec(name):
    if name not in NAMES:
        raise ValueError('Unknown suite task')
    path = ROOT / f'tests/cases/swe/{name}.json'
    return json.loads(path.read_text()), digest(path)


def verify_inputs(directory, spec):
    manifest = json.loads((directory / 'inputs.json').read_text())
    if manifest['instance_id'] != spec['instance_id'] or manifest['base_commit'] != spec['base_commit']:
        raise ValueError('Frozen input identity differs from task specification')
    for name, expected in manifest['files'].items():
        path = directory / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink():
            raise ValueError('Unsafe input manifest path')
        if digest(path) != expected:
            raise ValueError(f'Frozen benchmark input changed: {name}')
    return manifest


def unpack(archive, target):
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as tar:
        tar.extractall(target, filter='data')


def prepare_suite_task(case, output):
    """Called after output.mkdir; never enables a task on metadata alone."""
    import shutil
    from task_adapters import PROJECT_REQUIREMENTS, PROJECT_CHECKS
    name = case['id']
    spec, spec_hash = load_spec(name)
    directory = Path(case['swe_inputs']) / name
    manifest = verify_inputs(directory, spec)
    receipt_path = ROOT / f'tests/reports/qualifications/{name}.json'
    if not receipt_path.is_file():
        raise ValueError(f'{name} is registered but has no passed environment qualification')
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('qualified') is not True or receipt.get('spec_sha256') != spec_hash
            or receipt.get('inputs_sha256') != digest(directory / 'inputs.json')):
        raise ValueError(f'{name} qualification is missing, failed or stale')
    unpack(directory / 'public.tar.gz', output / 'workspace')
    shutil.copytree(directory / 'validator', output / 'validation')
    return {'id': name, 'workspace': 'task/workspace',
            'request': (directory / 'request.txt').read_text() + PROJECT_REQUIREMENTS,
            'acceptance': PROJECT_CHECKS, 'environment': receipt['environment'],
            'validation': {**receipt['validation'], 'overlay': 'task/validation'},
            'provenance': {'source': spec['source'], 'instance_id': spec['instance_id'],
                           'base_commit': spec['base_commit'], 'inputs_sha256': digest(directory / 'inputs.json'),
                           'qualification_sha256': digest(receipt_path), 'adapted_task': True,
                           'adaptation': 'Shared repository/handoff requirements; frozen native functional checks'}}
