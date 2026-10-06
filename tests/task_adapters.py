"""Normalize benchmark sources into public workspaces and private validation data."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib

from evaluation_runtime import digest, snapshot


ROOT = Path(__file__).resolve().parents[1]
SWE_NAMES = ('packaging',)
PROJECT_REQUIREMENTS = (
    '\n\nAdditional shared project requirements: Read and follow applicable repository guidance '
    '(including AGENTS.md and contributing instructions). Preserve existing compatibility and '
    'keep changes within scope. Explain the relevant design choices, checks actually performed, '
    'and unresolved limitations in a concise handoff. Keep design/work records where they are '
    'needed to understand or continue the change; no prescribed filenames or document count. '
    'Do not install additional dependencies; the provided environment is prepared for this task.')
PROJECT_CHECKS = [
    'Changes respect applicable repository conventions, scope, responsibilities and compatibility; '
    'cite concrete evidence rather than preferring a different style.',
    'Design/work records and the final handoff explain the relevant choices, actual verification '
    'and remaining limitations at a depth appropriate to the task. Do not require a fixed template '
    'or standalone design document for a small internal fix.',
]


def load_task(name, inputs=None):
    from run_smoke import load_case
    if name not in SWE_NAMES:
        return load_case(name)
    if inputs is None:
        raise ValueError('Real tasks require --swe-inputs pointing to frozen source data')
    return {'id': name, 'swe_inputs': str(Path(inputs).resolve())}


def prepare_task(case, output):
    """Return one source-independent task contract with a relative public workspace."""
    output.mkdir()
    if 'swe_inputs' not in case:
        workspace = output / 'workspace'
        workspace.mkdir()
        for name, content in case['files'].items():
            path = workspace / name
            if path.is_absolute() and not path.is_relative_to(workspace):
                raise ValueError('Fixture path escapes workspace')
            if '..' in Path(name).parts:
                raise ValueError('Fixture path escapes workspace')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return {**case, 'workspace': 'task/workspace', 'environment': {'kind': 'local'},
                'validation': None, 'provenance': {'source': 'behavior'}}
    name = case['id']
    if name not in SWE_NAMES:
        raise ValueError('Candidate has not qualified for paired execution')
    spec = json.loads((ROOT / f'tests/cases/swe/{name}.json').read_text())
    report = json.loads((ROOT / 'tests/reports/swe-preflight-2026-10-05.json').read_text())
    receipt = next(r for r in report['cases'] if r['name'] == name)
    if receipt['summary']['test_contract'] != 'pass' or receipt['spec'] != spec:
        raise ValueError('A matching passed preflight is required')
    environment = {'kind': 'docker', 'image': receipt['image_id'], 'network': 'none'}
    if name == 'packaging':
        qualification = ROOT / 'tests/reports/packaging-execution-environment-2026-10-06.json'
        if not qualification.is_file():
            raise ValueError('Packaging is paused until the clean executor environment qualifies')
        qualified = json.loads(qualification.read_text())
        if (qualified.get('qualified') is not True or qualified.get('spec') != spec
                or qualified.get('base_verifier_image') != receipt['image_id']):
            raise ValueError('Packaging execution environment qualification is missing or stale')
        environment.update(execution_image=qualified['executor_image'], audit_packaging_sources=True,
                           execution_qualification_sha256=digest(qualification))
    inputs = Path(case['swe_inputs'])
    row = inputs / (spec['instance_id'] + '.json')
    archive = inputs / spec['instance_id'] / 'source.tar.gz'
    if digest(row) != spec['metadata_sha256'] or digest(archive) != spec['source_sha256']:
        raise ValueError('Frozen benchmark input changed')
    metadata = json.loads(row.read_text())
    with tempfile.TemporaryDirectory(prefix='swe-adapter-') as tmp:
        scratch = Path(tmp)
        with tarfile.open(archive) as tar:
            tar.extractall(scratch / 'source', filter='data')
        source = next((scratch / 'source').iterdir())
        variants = scratch / 'variants'
        variants.mkdir()
        control, _ = prepare_variants(source, metadata, variants, spec['patch_mode'] == 'mask')
        snapshot(variants / 'learner', output / 'workspace')
        test_root = 'tests'
        overlay = output / 'validation'
        overlay.mkdir()
        shutil.copytree(control / test_root, overlay / test_root)
    return {'id': name, 'request': metadata['problem_statement'] + PROJECT_REQUIREMENTS,
            'acceptance': PROJECT_CHECKS, 'workspace': 'task/workspace',
            'environment': environment,
            'validation': {'kind': 'pytest', 'overlay': 'task/validation', 'test_roots': [test_root],
                           'groups': {g: test_items(metadata[g]) for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')},
                           'expected_outcomes': {r['group']: r['outcome_sha256'] for r in receipt['runs']
                                                 if r['variant'] == 'reference' and r['repetition'] == 1}},
            'provenance': {'source': spec['dataset'], 'instance_id': spec['instance_id'],
                           'base_commit': spec['base_commit'], 'metadata_sha256': spec['metadata_sha256'],
                           'source_sha256': spec['source_sha256'], 'adapted_task': True,
                           'adaptation': 'Shared engineering/handoff requirements and fixed preinstalled dependencies; native functional tests retained'}}

def test_items(value):
    return json.loads(value) if isinstance(value, str) else value



def apply_patch(source, patch, reverse=False):
    subprocess.run(['git', '-C', str(source), 'apply', '--whitespace=nowarn',
                    *(['--reverse'] if reverse else []), str(patch)], check=True,
                   capture_output=True, text=True)



def prepare_variants(source, metadata, output, mask):
    """Keep the learner's workspace separate from held-out tests and solutions."""
    learner = output / 'learner'
    shutil.copytree(source, learner, ignore=shutil.ignore_patterns('.git', '__pycache__'))
    subprocess.run(['git', 'init', '-q', str(learner)], check=True)
    patch, tests = output / 'source.patch', output / 'tests.patch'
    patch.write_text(metadata['patch'] + ('' if metadata['patch'].endswith('\n') else '\n'))
    tests.write_text(metadata['test_patch'] + ('' if metadata['test_patch'].endswith('\n') else '\n'))
    if mask:
        apply_patch(learner, patch)
        apply_patch(learner, tests)  # FeatureBench removes hidden tests in this direction.
    control = output / 'control'
    shutil.copytree(learner, control)
    apply_patch(control, tests, reverse=mask)
    reference = output / 'reference'
    shutil.copytree(control, reference)
    apply_patch(reference, patch, reverse=mask)
    return control, reference



def requirements(source, case):
    if case == 'packaging':
        return ['uv==0.8.18', 'flit_core==3.12.0', 'pytest==8.3.5', 'pytest-xdist==3.6.1',
                'pytest-cov==6.1.1', 'pretend==1.0.9', 'tomli==2.2.1', 'tomli_w==1.2.0'], []
    project = tomllib.loads((source / 'pyproject.toml').read_text())['project']
    lock = tomllib.loads((source / 'uv.lock').read_text())
    versions = {}
    for package in lock['package']:
        if 'version' in package and package.get('source', {}).get('registry'):
            versions.setdefault(package['name'], set()).add(package['version'])
    constraints = [f'{name}=={next(iter(values))}' for name, values in sorted(versions.items())
                   if len(values) == 1]
    if case == 'dspy':
        return ['uv==0.8.18', 'setuptools', 'wheel', *project['dependencies'],
                'pytest', 'pytest-asyncio', 'pytest-mock', 'pillow', 'mcp', 'litellm[proxy]'], constraints
    return ['uv==0.8.18', 'hatchling', 'editables==0.5', *project['dependencies'],
            *project['optional-dependencies']['litellm'], 'pytest', 'pytest-asyncio',
            'pytest-mock', 'inline-snapshot', 'rich', 'graphviz', 'fastapi', 'ruff'], constraints
