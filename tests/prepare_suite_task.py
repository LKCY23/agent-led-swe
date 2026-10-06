#!/usr/bin/env python3
"""Freeze a selected task's public source and private verifier inputs (no model)."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import uuid

from container_workspace import export_workspace
from evaluation_runtime import digest, file_hashes, snapshot, write_json
from suite_tasks import NAMES, github_patch, load_spec, selectors
from task_adapters import prepare_variants


def prepare(name, inputs, image):
    spec, _ = load_spec(name)
    directory = inputs / name
    metadata = json.loads((directory / 'metadata.json').read_text())
    if digest(directory / 'metadata.json') != spec['metadata_sha256']:
        raise ValueError('Source metadata changed')
    if metadata['instance_id'] != spec['instance_id'] or metadata['base_commit'] != spec['base_commit']:
        raise ValueError('Task identity mismatch')
    image = subprocess.check_output(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], text=True).strip()
    if (directory / 'inputs.json').exists():
        raise ValueError('Inputs already frozen; use a fresh input directory for a revised preparation')
    public, validator = directory / 'public', directory / 'validator'
    public.mkdir()
    validator.mkdir()
    environment = {'kind': 'docker', 'image': image, 'network': 'none', 'workdir': '/testbed'}
    if spec['adapter'] == 'featbench-v1':
        if digest(directory / 'source.tar.gz') != spec['source_sha256']:
            raise ValueError('Source archive changed')
        normalized = {**metadata, 'patch': github_patch(metadata['patch']),
                      'test_patch': github_patch(metadata['test_patch'])}
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp)
            with tarfile.open(directory / 'source.tar.gz') as tar:
                tar.extractall(scratch / 'source', filter='data')
            source = next((scratch / 'source').iterdir())
            variants = scratch / 'variants'
            variants.mkdir()
            control, _ = prepare_variants(source, normalized, variants, False)
            shutil.copytree(variants / 'learner', public, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('.git'))
            for test_root in spec['test_roots']:
                shutil.copytree(control / test_root, validator / test_root)
        (directory / 'reference.patch').write_text(normalized['patch'])
        (directory / 'test.patch').write_text(normalized['test_patch'])
        request = metadata['problem_statement']
        environment['platform'] = 'linux/arm64'
        validation = {'kind': 'pytest', 'test_roots': spec['test_roots'],
                      'groups': {g: selectors(metadata[g]) for g in ('FAIL_TO_PASS', 'PASS_TO_PASS')},
                      'timeout_seconds': 600, 'allowed_skips': spec.get('allowed_skips', {})}
    else:
        for name, sha in spec['verifier_sha256'].items():
            if digest(directory / name) != sha:
                raise ValueError(f'Native verifier material changed: {name}')
        container = 'swe-public-' + uuid.uuid4().hex[:10]
        try:
            subprocess.run(['docker', 'run', '-d', '--name', container, '--network', 'none',
                '--platform', 'linux/amd64', image, 'sleep', '900'], check=True, capture_output=True)
            head = subprocess.check_output(['docker', 'exec', container, 'git', '-C', '/app',
                                            'rev-parse', 'HEAD'], text=True).strip()
            if head != spec['base_commit']:
                raise ValueError('Task image HEAD differs from the declared base commit')
            write_json(directory / 'image-source.json', {'image': image, 'head': head,
                        'declared_base_commit': spec['base_commit']})
            probe = subprocess.run(['docker', 'exec', container, 'sh', '-c',
                'test ! -e /solution/gold_patch.diff && test ! -e /tests/test_patch.patch'], capture_output=True)
            if probe.returncode:
                raise ValueError('Task image exposes private solution/test material')
            export_workspace(container, '/app', public, spec.get('workspace_excludes', []))
        finally:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
        shutil.copytree(directory / 'tests', validator / 'tests')
        write_json(validator / 'public-files.json', sorted(file_hashes(public)))
        shutil.copyfile(directory / 'solution/gold_patch.diff', directory / 'reference.patch')
        request = (directory / 'instruction.md').read_text()
        environment.update(platform='linux/amd64', workdir='/app', workspace_mode='copy',
                           workspace_excludes=spec.get('workspace_excludes', []), install_argv=[])
        validation = {'kind': 'swe-pro-v2', 'timeout_seconds': 600,
                      'supplemental': spec.get('supplemental', [])}
    with tarfile.open(directory / 'public.tar.gz', 'w:gz') as tar:
        for path in sorted(public.iterdir()):
            tar.add(path, arcname=path.name)
    (directory / 'request.txt').write_text(request)
    write_json(directory / 'environment.json', environment)
    write_json(directory / 'validation.json', validation)
    frozen = ['metadata.json', 'public.tar.gz', 'reference.patch', 'request.txt',
              'environment.json', 'validation.json']
    frozen += [str(p.relative_to(directory)) for p in sorted(validator.rglob('*')) if p.is_file()]
    write_json(directory / 'inputs.json', {'instance_id': spec['instance_id'], 'base_commit': spec['base_commit'],
                                         'files': {p: digest(directory / p) for p in frozen}})
    return {'task': spec['name'], 'image': image, 'public_files': len(file_hashes(public))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=NAMES)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.name, args.inputs.resolve(), args.image)))
