from __future__ import annotations

import concurrent.futures
import os
import time
from typing import Dict, Iterable, List, Tuple

from minio.commonconfig import REPLACE
from minio.datatypes import Object

from .client import build_minio_client, ensure_bucket, iter_objects, remove_objects
from .config import SyncConfig
from .utils import compute_md5_hex, to_posix_key, walk_local_files


def _object_etag(obj: Object) -> str:
    return (obj.etag or "").replace('"', "")


def build_remote_index(client, cfg: SyncConfig) -> Dict[str, Tuple[str, int]]:
    index: Dict[str, Tuple[str, int]] = {}
    for obj in iter_objects(client, cfg.bucket, cfg.prefix):
        if obj.is_dir:
            continue
        key = obj.object_name
        rel = key[len(cfg.prefix):] if cfg.prefix and key.startswith(cfg.prefix) else key
        index[rel] = (_object_etag(obj), int(obj.size or 0))
    return index


def upload_missing_and_changed(client, cfg: SyncConfig, remote_index: Dict[str, Tuple[str, int]]) -> Tuple[int, int]:
    uploaded = 0
    skipped = 0

    def need_upload(local_path: str, rel_posix: str) -> bool:
        if rel_posix not in remote_index:
            return True
        remote_etag, remote_size = remote_index[rel_posix]
        if not cfg.etag_by_content:
            try:
                local_size = os.path.getsize(local_path)
            except OSError:
                return True
            if local_size != remote_size:
                return True
            return False
        local_md5 = compute_md5_hex(local_path)
        return local_md5 != remote_etag

    def do_upload(item: Tuple[str, str]) -> bool:
        local_path, rel_posix = item
        if not need_upload(local_path, rel_posix):
            return False
        object_name = cfg.prefix + rel_posix if cfg.prefix else rel_posix
        client.fput_object(cfg.bucket, object_name, local_path)
        return True

    items = list(walk_local_files(cfg.local_dir, cfg.include, cfg.exclude))
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
        futures = [ex.submit(do_upload, it) for it in items]
        for fut in concurrent.futures.as_completed(futures):
            if fut.result():
                uploaded += 1
            else:
                skipped += 1
    return uploaded, skipped


def delete_remote_extraneous(client, cfg: SyncConfig, remote_index: Dict[str, Tuple[str, int]]) -> int:
    wanted: Dict[str, None] = {rel for _, rel in walk_local_files(cfg.local_dir, cfg.include, cfg.exclude)}
    extraneous = []
    for rel in remote_index.keys():
        if rel not in wanted:
            key = cfg.prefix + rel if cfg.prefix else rel
            extraneous.append(key)
    if extraneous:
        remove_objects(client, cfg.bucket, extraneous)
    return len(extraneous)


def sync_up(cfg: SyncConfig) -> None:
    client = build_minio_client(cfg.endpoint, cfg.access_key, cfg.secret_key, cfg.secure)
    ensure_bucket(client, cfg.bucket)
    remote_index = build_remote_index(client, cfg)
    uploaded, skipped = upload_missing_and_changed(client, cfg, remote_index)
    deleted = 0
    if cfg.delete_extraneous:
        remote_index = build_remote_index(client, cfg)
        deleted = delete_remote_extraneous(client, cfg, remote_index)
    print(f"Uploaded: {uploaded}, Skipped: {skipped}, Deleted: {deleted}")


def ensure_local_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def download_missing_and_changed(client, cfg: SyncConfig, remote_index: Dict[str, Tuple[str, int]]) -> Tuple[int, int]:
    downloaded = 0
    skipped = 0

    def need_download(rel: str, etag: str, size: int) -> bool:
        local_path = os.path.join(cfg.local_dir, rel.replace("/", os.sep))
        if not os.path.exists(local_path):
            return True
        if not cfg.etag_by_content:
            try:
                local_size = os.path.getsize(local_path)
            except OSError:
                return True
            return local_size != size
        local_md5 = compute_md5_hex(local_path)
        return local_md5 != etag

    def do_download(item: Tuple[str, Tuple[str, int]]) -> bool:
        rel, (etag, size) = item
        if not need_download(rel, etag, size):
            return False
        object_name = cfg.prefix + rel if cfg.prefix else rel
        local_path = os.path.join(cfg.local_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client.fget_object(cfg.bucket, object_name, local_path)
        return True

    items = list(remote_index.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
        futures = [ex.submit(do_download, it) for it in items]
        for fut in concurrent.futures.as_completed(futures):
            if fut.result():
                downloaded += 1
            else:
                skipped += 1
    return downloaded, skipped


def delete_local_extraneous(cfg: SyncConfig, remote_index: Dict[str, Tuple[str, int]]) -> int:
    wanted = set(remote_index.keys())
    extraneous = []
    for full, rel in walk_local_files(cfg.local_dir, cfg.include, cfg.exclude):
        if rel not in wanted:
            extraneous.append(full)
    for p in extraneous:
        try:
            os.remove(p)
        except OSError:
            pass
    return len(extraneous)


def sync_down(cfg: SyncConfig) -> None:
    client = build_minio_client(cfg.endpoint, cfg.access_key, cfg.secret_key, cfg.secure)
    ensure_local_dir(cfg.local_dir)
    remote_index = build_remote_index(client, cfg)
    downloaded, skipped = download_missing_and_changed(client, cfg, remote_index)
    deleted = 0
    if cfg.delete_extraneous:
        deleted = delete_local_extraneous(cfg, remote_index)
    print(f"Downloaded: {downloaded}, Skipped: {skipped}, Deleted: {deleted}")


def watch_loop(mode: str, cfg: SyncConfig, interval: int) -> None:
    while True:
        try:
            if mode == "up":
                sync_up(cfg)
            else:
                sync_down(cfg)
        except Exception as e:
            print(f"Error during sync: {e}")
        time.sleep(max(1, interval))


