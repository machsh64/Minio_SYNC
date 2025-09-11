from __future__ import annotations

from typing import Iterable, Optional, Tuple

from minio import Minio
from minio.deleteobjects import DeleteObject


def build_minio_client(endpoint: str, access_key: str, secret_key: str, secure: bool) -> Minio:
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def iter_objects(client: Minio, bucket: str, prefix: str) -> Iterable:
    return client.list_objects(bucket, prefix=prefix, recursive=True)


def remove_objects(client: Minio, bucket: str, keys: Iterable[str]) -> None:
    delete_objects = (DeleteObject(k) for k in keys)
    for _ in client.remove_objects(bucket, delete_objects):
        pass


