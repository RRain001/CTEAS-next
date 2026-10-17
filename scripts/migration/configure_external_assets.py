#!/usr/bin/env python3
"""Restore private local scientific dependencies, checking the frozen SHA256.

No downloads or git operations that publish assets are performed. Use a locally
authorized checkout or asset root. Restored paths are ignored by CTEAS-next Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    sources = ap.add_mutually_exclusive_group()
    sources.add_argument('--source-repo', type=Path, help='Read pinned Git objects from an authorized local CTEAS repository')
    sources.add_argument('--asset-root', type=Path, help='Directory containing the original relative asset paths')
    ap.add_argument('--check', action='store_true', help='Only check existing local files; do not restore')
    args = ap.parse_args()
    if not args.check and not (args.source_repo or args.asset_root):
        ap.error('Choose --check, --source-repo, or --asset-root')
    root = args.root.resolve()
    manifest = json.loads((root / 'docs/migration/SOURCE_MANIFEST.json').read_text())
    entries = [e for e in manifest['files'] if e.get('local_dependency_path')]
    tracked = set(subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0'))
    problems = []
    for e in entries:
        rel = e['local_dependency_path']
        dest = root / rel
        if dest.resolve() != dest.absolute() or root not in dest.resolve().parents:
            problems.append('Unsafe symlink or path: ' + rel)
            continue
        if rel in tracked:
            problems.append('External asset must not be tracked: ' + rel)
            continue
        if dest.exists():
            data = dest.read_bytes()
        elif args.check:
            problems.append('Missing external asset: ' + rel)
            continue
        elif args.source_repo:
            proc = subprocess.run(['git', '-C', str(args.source_repo), 'show', manifest['source_commit'] + ':' + e['source_path']], capture_output=True)
            if proc.returncode:
                problems.append('Pinned asset unavailable in local source: ' + rel)
                continue
            data = proc.stdout
        else:
            src = args.asset_root / e['source_path']
            if not src.is_file():
                problems.append('Missing asset-root file: ' + rel)
                continue
            data = src.read_bytes()
        if hashlib.sha256(data).hexdigest() != e['sha256']:
            problems.append('SHA256 mismatch (refusing overwrite): ' + rel)
            continue
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            dest.chmod(0o755 if e['mode'] == '100755' else 0o644)
    print(json.dumps(dict(status='FAIL' if problems else 'PASS', assets=len(entries), errors=problems), indent=2))
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
