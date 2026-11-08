"""Complete file-content snapshots of explicit test roots, outside the repository."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def files(root):
    for p in root.rglob('*'):
        if p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse points are not supported')
        if p.is_file(): yield p


def no_reparse(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try: info = part.lstat()
        except FileNotFoundError: continue
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse points are not supported')
    return path


def directories(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())


def manifest_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('unsafe manifest path')
    if any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('unsafe manifest path')
    return value


def roots_checked(roots):
    result = [no_reparse(x).resolve(strict=True) for x in roots]
    for p in result:
        if not p.is_dir() or p == Path(p.anchor) or len(p.parts) < 3:
            raise ValueError('explicit directory below a drive root required')
        for q in result:
            if p != q and p.is_relative_to(q): raise ValueError('overlapping roots')
    if len(set(result)) != len(result): raise ValueError('duplicate roots')
    return result


def capture(roots, destination):
    roots = roots_checked(roots); destination = no_reparse(destination).resolve()
    if destination.exists() or any(destination.is_relative_to(r) for r in roots):
        raise ValueError('fresh backup directory outside test roots required')
    inventory = [[p for p in files(r)] for r in roots]
    required = sum(p.stat().st_size for group in inventory for p in group)
    parent = destination.parent
    if shutil.disk_usage(parent).free < required + 64*1024*1024:
        raise ValueError('insufficient backup space')
    destination.mkdir(mode=0o700)
    manifest = {'version': 1, 'roots': [str(r) for r in roots], 'files': [], 'directories': [directories(r) for r in roots]}
    for i, group in enumerate(inventory):
        for p in group:
            relative = p.relative_to(roots[i]).as_posix()
            before = digest(p)
            target = destination / 'data' / str(i) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            if digest(target) != before or digest(p) != before:
                raise ValueError('source changed during snapshot; do not start test')
            manifest['files'].append({'root':i, 'path':relative, 'sha256':before,
                                     'mtime_ns':p.stat().st_mtime_ns})
    expected = {(entry['root'], entry['path']) for entry in manifest['files']}
    actual = {(i, p.relative_to(root).as_posix()) for i, root in enumerate(roots) for p in files(root)}
    if actual != expected: raise ValueError('file inventory changed during snapshot')
    if [directories(r) for r in roots] != manifest['directories']:
        raise ValueError('directory inventory changed during snapshot')
    for entry in manifest['files']:
        p = roots[entry['root']]/entry['path']
        if (digest(p) != entry['sha256'] or p.stat().st_mtime_ns != entry['mtime_ns'] or
            (destination/'data'/str(entry['root'])/entry['path']).stat().st_mtime_ns != entry['mtime_ns']):
            raise ValueError('file state changed during snapshot')
    # Only a completed copy receives a usable manifest.
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return len(manifest['files'])


def restore(roots, snapshot, remove_new=False):
    roots = roots_checked(roots); snapshot = no_reparse(snapshot).resolve(strict=True)
    m = json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
    if m.get('version') != 1 or [str(r) for r in roots] != m.get('roots'):
        raise ValueError('explicit roots must match snapshot')
    if not isinstance(m.get('files'), list) or not isinstance(m.get('directories'), list) or len(m['directories']) != len(roots):
        raise ValueError('invalid snapshot inventory')
    expected, wanted_dirs, prepared = set(), set(), []
    # Validate ALL paths, backup contents and metadata before any write or mkdir.
    for entry in m['files']:
        i = entry.get('root')
        if type(i) is not int or not 0 <= i < len(roots): raise ValueError('invalid root index')
        relative = manifest_relative(entry.get('path'))
        root = roots[i]
        target = no_reparse(root/relative).resolve()
        backup_root = no_reparse(snapshot/'data'/str(i)).resolve()
        backup = no_reparse(backup_root/relative).resolve(strict=True)
        if not target.is_relative_to(root) or not backup.is_relative_to(backup_root):
            raise ValueError('unsafe manifest path')
        if target in expected: raise ValueError('duplicate file path')
        if not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', '')) or type(entry.get('mtime_ns')) is not int:
            raise ValueError('invalid file metadata')
        if digest(backup) != entry['sha256'] or backup.stat().st_mtime_ns != entry['mtime_ns']:
            raise ValueError('damaged backup')
        expected.add(target); prepared.append((target, backup, entry))
    for i, items in enumerate(m['directories']):
        if not isinstance(items, list): raise ValueError('invalid directories')
        for relative in items:
            relative = manifest_relative(relative)
            target = no_reparse(roots[i]/relative).resolve()
            if not target.is_relative_to(roots[i]) or target in wanted_dirs:
                raise ValueError('unsafe or duplicate directory path')
            wanted_dirs.add(target)
    if any(p in expected or any(a in expected for a in p.parents) for p in wanted_dirs):
        raise ValueError('file/directory collision')
    if any(any(a in expected for a in p.parents) for p in expected):
        raise ValueError('file path collision')
    current = set(p.resolve() for root in roots for p in files(root))
    added = current - expected
    if added and not remove_new:
        raise ValueError('new files exist; preserve evidence, then explicitly authorize --remove-new')
    if any(p.exists() and not p.is_dir() for p in wanted_dirs) or any(p.exists() and not p.is_file() for p in expected):
        raise ValueError('destination type collision')
    for target in wanted_dirs: target.mkdir(parents=True, exist_ok=True)
    for target, backup, entry in prepared:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
    if remove_new:
        for p in added: p.unlink()  # Individual verified files within explicit roots.
    for target, backup, entry in prepared:
        if digest(target) != entry['sha256'] or target.stat().st_mtime_ns != entry['mtime_ns']:
            raise ValueError('restoration verification failed')
    if remove_new:
        for root in roots:
            for directory in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                if directory.resolve() not in wanted_dirs: directory.rmdir()
    return len(expected)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture','restore'])
    p.add_argument('--root', action='append', required=True)
    p.add_argument('--snapshot', required=True)
    p.add_argument('--remove-new', action='store_true')
    a = p.parse_args()
    count = capture(a.root,a.snapshot) if a.action == 'capture' else restore(a.root,a.snapshot,a.remove_new)
    print(json.dumps({'result':'PASS','files':count,'action':a.action}))


if __name__ == '__main__': main()
