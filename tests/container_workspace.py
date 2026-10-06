"""Copy-mode workspaces retain image dependencies without hiding them with a bind mount."""
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


def install_workspace(container, source, workdir, base_files=()):
    """Overlay submitted public files, including deletions, onto the pristine image."""
    source = Path(source).resolve()
    for path in source.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(source):
            raise ValueError('Submitted workspace contains an escaping symlink')
    current = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() or p.is_symlink()}
    deleted = sorted(set(base_files) - current)
    if any(Path(p).is_absolute() or '..' in Path(p).parts or '.git' in Path(p).parts for p in deleted):
        raise ValueError('Unsafe baseline file inventory')
    script = ('import pathlib,json,sys; root=pathlib.Path(sys.argv[1]); '
              'paths=json.loads(sys.stdin.read()); '
              '[(root/p).unlink(missing_ok=True) for p in paths if (root/p).is_symlink() or (root/p).is_file()]')
    subprocess.run(['docker', 'exec', '-i', container, 'python3', '-c', script, workdir],
                   input=json.dumps(deleted), text=True, check=True, capture_output=True)
    subprocess.run(['docker', 'cp', str(source) + '/.', f'{container}:{workdir}/'],
                   check=True, capture_output=True)


def export_workspace(container, workdir, target, exclude=()):
    """Capture all public files, including new docs; exclude only declared image dependencies."""
    with tempfile.TemporaryDirectory(prefix='swe-export-') as tmp:
        archive = Path(tmp) / 'workspace.tar'
        with archive.open('wb') as stream:
            subprocess.run(['docker', 'exec', container, 'tar', '-C', workdir,
                '--exclude=./.git', *[f'--exclude=./{p}' for p in exclude], '-cf', '-', '.'],
                check=True, stdout=stream, stderr=subprocess.PIPE)
        extracted = Path(tmp) / 'extracted'
        extracted.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(extracted, filter='data')
        target = Path(target)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(extracted, target, symlinks=True)


def allow_workspace_owner(container, workdir, uid, gid, exclude=()):
    script = '''
import os,sys,json
root,uid,gid,excluded=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),set(json.loads(sys.argv[4]))
for folder, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if os.path.relpath(os.path.join(folder,d),root) not in excluded]
    os.chown(folder,uid,gid)
    for name in files:
        os.chown(os.path.join(folder,name),uid,gid,follow_symlinks=False)
'''
    subprocess.run(['docker', 'exec', container, 'python3', '-c', script,
                    workdir, str(uid), str(gid), json.dumps(list(exclude))], check=True, capture_output=True)
