from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Iterable, List, Tuple


def compute_md5_hex(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def normalize_local_path(base_dir: str, path: str) -> str:
    full = os.path.abspath(os.path.join(base_dir, path))
    return full


def to_posix_key(path: str) -> str:
    return path.replace(os.sep, "/")


def match_globs(rel_path: str, includes: List[str], excludes: List[str]) -> bool:
    rel_posix = to_posix_key(rel_path)
    for pattern in excludes:
        if fnmatch.fnmatch(rel_posix, pattern):
            return False
    if not includes:
        return True
    for pattern in includes:
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


def walk_local_files(base_dir: str, includes: List[str], excludes: List[str]) -> Iterable[Tuple[str, str]]:
    base_dir_abs = os.path.abspath(base_dir)
    for root, _, files in os.walk(base_dir_abs):
        for name in files:
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, base_dir_abs)
            rel_posix = to_posix_key(rel_path)
            if match_globs(rel_posix, includes, excludes):
                yield full_path, rel_posix


