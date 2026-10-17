#!/usr/bin/env python3
"""Verify/materialize pinned CTEAS case artifacts from the checked-out Git commit.

A subset of self-hosted runner checkouts has dropped tracked project/cases/*
files despite reporting a successful checkout. Do not copy an arbitrary
previous case or download an unverified artifact. If a required path is absent,
restore ONLY its exact Git blob from HEAD, then verify its Git object hash.

Never modify an existing file with the wrong hash. Fail closed if a required
path is absent from HEAD, a Git submodule/symlink, or cannot be verified.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

CASE = "project/cases/hefei5km_2022_reference_case_20261011"
SOURCE = [
    "run/met/met.inp",
]
GRID = SOURCE + [
    "case.yaml",
    "grid/grid.cmn",
    "grid/center_location",
    "geo/terrel/terrel.inp",
    "geo/ctgproc/ctgproc.inp",
    "geo/makegeo/makegeo.inp",
    "geo/makegeo/geo.dat",
    "met/surface/final/stations.csv",
    "met/surface/final/surf.dat",
    "met/upperair/final/stations.csv",
    "met/upperair/final/up_58424.dat",
]
FULL = GRID + [
    "run/met/met.dat",
    "run/puff/puff.inp",
]


def git(repo: Path, *argv: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *argv], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode:
        raise RuntimeError(f"Git object lookup failed: {argv}: {p.stderr.strip()}")
    return p.stdout.strip()


def verify_git_blob(repo: Path, relative_path: str) -> bool:
    oid = git(repo, "rev-parse", f"HEAD:{relative_path}")
    kind = git(repo, "cat-file", "-t", oid)
    if kind != "blob":
        raise RuntimeError(f"Not a pinned Git blob: {relative_path} (type={kind})")
    entry = git(repo, "ls-tree", "HEAD", "--", relative_path)
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise RuntimeError(f"Unsafe/nonregular Git entry for {relative_path}: {entry}")
    target = repo / relative_path
    if target.is_symlink():
        raise RuntimeError(f"Refusing symlink path in frozen case: {relative_path}")
    restored = False
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent,
            prefix=".cteas-git-restore-", delete=False
        ) as temp:
            tmp = Path(temp.name)
            proc = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "blob", oid],
                stdout=temp, stderr=subprocess.PIPE, check=False,
            )
        try:
            if proc.returncode:
                raise RuntimeError(
                    f"Unable to materialize Git blob {oid}: "
                    + proc.stderr.decode(errors="replace"))
            observed = git(repo, "hash-object", "--path="+relative_path, str(tmp))
            if observed != oid:
                raise RuntimeError(
                    f"Restored Git hash differs for {relative_path}: {observed} vs {oid}")
            os.replace(tmp, target)
            restored = True
        finally:
            tmp.unlink(missing_ok=True)
    actual = git(repo, "hash-object", "--path="+relative_path, str(target))
    if actual != oid:
        raise RuntimeError(
            f"Git provenance mismatch: {relative_path} observed={actual} expected={oid}")
    if target.stat().st_size == 0:
        raise RuntimeError(f"Frozen scientific input is empty: {relative_path}")
    with target.open("rb") as f:
        if f.read(128).startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise RuntimeError(f"Unresolved Git LFS pointer: {relative_path}")
    return restored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--mode", required=True, choices=["source", "grid", "full"])
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise RuntimeError(f"Not a Git checkout: {repo}")
    files = {"source": SOURCE, "grid": GRID, "full": FULL}[args.mode]
    restored = 0
    for item in files:
        relative = f"{CASE}/{item}"
        did_restore = verify_git_blob(repo, relative)
        restored += did_restore
        print(f"{'RESTORED' if did_restore else 'VERIFIED'} {relative}", flush=True)
    print(f"PASS_FROZEN_GIT_PROVENANCE mode={args.mode} files={len(files)} "
          f"materialized_from_HEAD={restored} commit={git(repo, 'rev-parse', 'HEAD')}")


if __name__ == "__main__":
    main()
