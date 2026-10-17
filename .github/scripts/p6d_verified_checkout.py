#!/usr/bin/env python3
"""Restore exact P6D CI sources using authenticated GitHub REST.

This script MUST be loaded by its callers from the current immutable Git
tree and its Git-blob SHA-1 verified before executing it. Every restored
source blob is independently checked against that same tree. An incomplete
source set causes an explicit failure, never a fallback to stale runner data.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
OWNER = os.environ["GITHUB_REPOSITORY"]
SHA = os.environ["GITHUB_SHA"]
TOKEN = os.environ["GH_TOKEN"]
API = "https://api.github.com/repos/" + OWNER
HEADERS = {
    "Authorization": "Bearer " + TOKEN,
    "Accept": "application/vnd.github+json",
    "User-Agent": "CTEAS-P6D-verified-CI",
    "X-GitHub-Api-Version": "2022-11-28",
}

def api(path: str):
    last_error = None
    for attempt in range(3):
        try:
            req = Request(API + path, headers=HEADERS)
            with urlopen(req, timeout=30) as stream:
                return json.load(stream)
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                break
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError("GitHub REST source request failed: " + path) from last_error

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main():
    commit = api("/git/commits/" + SHA)
    tree = api("/git/trees/" + commit["tree"]["sha"] + "?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("Immutable source tree is truncated")
    vendor = "engine/vendor/src/CALMET_v6.5.0_L150223/"
    modern = "native_cpp/modules/p6_calmet/"
    action = ".github/actions/cteas-linux-toolchain/"
    accepted = [
        item for item in tree["tree"]
        if item["type"] == "blob" and
        (item["path"].startswith(modern)
         or item["path"].startswith(vendor)
         or item["path"].startswith(action))
    ]
    files = {item["path"] for item in accepted}
    required = {
        modern + "CMakeLists.txt",
        modern + "reference/compare_original_inter2.py",
        modern + "reference/compare_original_similt_neutral.py",
        vendor + "calmet.for",
        vendor + "params.met",
        action + "action.yml",
    }
    if len(accepted) < 100 or not required.issubset(files):
        raise RuntimeError("Incomplete P6D source tree; refusing unverified build")
    # Self-hosted workspaces persist between jobs: erase only the scoped
    # C++/vendor/action roots to prevent mixing revisions.
    for prefix in (modern, vendor, action):
        target = ROOT / prefix.rstrip("/")
        if target.exists():
            shutil.rmtree(target)
    def transfer(item):
        path = Path(item["path"])
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError("Unsafe source path")
        obj = api("/git/blobs/" + item["sha"])
        if obj.get("encoding") != "base64":
            raise RuntimeError("Invalid Git blob encoding")
        data = base64.b64decode(obj["content"])
        if git_blob(data) != item["sha"]:
            raise RuntimeError("Git blob SHA-1 mismatch: " + item["path"])
        destination = ROOT / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return item["path"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(transfer, item) for item in accepted]
        for number, result in enumerate(as_completed(futures), 1):
            result.result()
            if number % 25 == 0 or number == len(futures):
                print(f"P6D verified Git blobs {number}/{len(futures)}", flush=True)
    print(f"P6D source bootstrap PASS commit={SHA}; source_blobs={len(accepted)}", flush=True)

if __name__ == "__main__":
    main()
