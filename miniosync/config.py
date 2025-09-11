from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class SyncConfig:
    endpoint: str
    secure: bool
    access_key: str
    secret_key: str

    bucket: str
    prefix: str = ""

    local_dir: str = "."

    include: List[str] = field(default_factory=lambda: ["**/*"]) 
    exclude: List[str] = field(default_factory=list)

    concurrency: int = 4
    etag_by_content: bool = False
    delete_extraneous: bool = False

    def normalize(self) -> None:
        self.local_dir = os.path.abspath(self.local_dir)
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix = self.prefix + "/"
        if self.concurrency < 1:
            self.concurrency = 1


def load_config(path: str) -> SyncConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    cfg = SyncConfig(
        endpoint=str(data.get("endpoint", "127.0.0.1:9000")),
        secure=bool(data.get("secure", False)),
        access_key=str(data.get("access_key", "")),
        secret_key=str(data.get("secret_key", "")),
        bucket=str(data.get("bucket", "")),
        prefix=str(data.get("prefix", "")),
        local_dir=str(data.get("local_dir", ".")),
        include=list(data.get("include", ["**/*"])),
        exclude=list(data.get("exclude", [])),
        concurrency=int(data.get("concurrency", 4)),
        etag_by_content=bool(data.get("etag_by_content", False)),
        delete_extraneous=bool(data.get("delete_extraneous", False)),
    )
    cfg.normalize()
    return cfg


