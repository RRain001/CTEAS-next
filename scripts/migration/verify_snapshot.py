#!/usr/bin/env python3
"""Verify byte and executable-mode identity against the frozen export manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--source-repo', type=Path, help='Optional original repo for independent Git tree verification')
    args = ap.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / 'docs/migration/SOURCE_MANIFEST.json').read_text())
    tracked = set(subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0'))
    checked = excluded = 0
    errors = []
    for entry in manifest['files']:
        if entry['target_path'] is None:
            excluded += 1
            if entry['source_path'] in tracked:
                errors.append('Excluded asset is Git-tracked: ' + entry['source_path'])
            if not entry.get('local_dependency_path') and (root / entry['source_path']).exists():
                errors.append('Excluded asset exists: ' + entry['source_path'])
            continue
        path = root / entry['target_path']
        if not path.is_file() or path.is_symlink():
            errors.append('Missing or symlink: ' + entry['target_path'])
            continue
        data = path.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        mode = '100755' if path.stat().st_mode & 0o111 else '100644'
        if hashlib.sha256(data).hexdigest() != entry.get('target_sha256', entry['sha256']) or oid != entry.get('target_git_blob', entry['git_blob']) or mode != entry['mode']:
            errors.append('Content or mode mismatch: ' + entry['target_path'])
        checked += 1
    if args.source_repo:
        for path, oid in manifest['frozen_trees'].items():
            source_oid = subprocess.check_output(['git', '-C', str(args.source_repo), 'rev-parse',
                manifest['source_commit'] + ':' + path], text=True).strip()
            if source_oid != oid:
                errors.append('Upstream tree mismatch: ' + path)
    print(json.dumps(dict(status='FAIL' if errors else 'PASS', checked=checked,
                          excluded=excluded, errors=errors), indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
