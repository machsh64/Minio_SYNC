from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
import time
from typing import Optional


@dataclass
class MinioEndpoint:
    alias: str
    endpoint: str  # host:port 或 http(s)://host:port
    access_key: str
    secret_key: str
    secure: bool = False

    def normalized_endpoint(self) -> str:
        ep = self.endpoint.strip()
        if ep.startswith("http://") or ep.startswith("https://"):
            return ep
        return ("https://" if self.secure else "http://") + ep


def run_cmd(cmd: list[str], env: Optional[dict] = None, cwd: Optional[str] = None) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env or os.environ.copy(),
        text=True,
        shell=False,
    )
    out, err = proc.communicate()
    return proc.returncode, out, err


def mc_alias_set(mc_path: str, ep: MinioEndpoint) -> tuple[int, str, str]:
    cmd = [mc_path, "alias", "set", ep.alias, ep.normalized_endpoint(), ep.access_key, ep.secret_key]
    return run_cmd(cmd)


def mc_mb(mc_path: str, alias: str, bucket: str) -> tuple[int, str, str]:
    # 创建桶（已存在则忽略）
    target = f"{alias}/{bucket}"
    cmd = [mc_path, "mb", "--ignore-existing", target]
    return run_cmd(cmd)


def mc_mirror(mc_path: str, src: str, dst: str, remove: bool = False, overwrite: bool = True) -> tuple[int, str, str]:
    cmd = [mc_path, "mirror"]
    if overwrite:
        cmd.append("--overwrite")
    if remove:
        cmd.append("--remove")
    cmd.extend([src, dst])
    return run_cmd(cmd)


def sync_a_to_b(
    mc_path: str,
    a: MinioEndpoint,
    b: MinioEndpoint,
    bucket_a: str,
    bucket_b: str,
    remove: bool = False,
    attempts: int = 3,
) -> tuple[bool, str]:
    rc1, out1, err1 = mc_alias_set(mc_path, a)
    rc2, out2, err2 = mc_alias_set(mc_path, b)
    if rc1 != 0:
        return False, f"mc alias set {a.alias} failed: {err1 or out1}"
    if rc2 != 0:
        return False, f"mc alias set {b.alias} failed: {err2 or out2}"

    # 确保目标桶存在
    rcmk, outmk, errmk = mc_mb(mc_path, b.alias, bucket_b)
    if rcmk != 0 and "already own it" not in (outmk + errmk):
        return False, f"mc mb {b.alias}/{bucket_b} failed: {errmk or outmk}"

    src = f"{a.alias}/{bucket_a}"
    dst = f"{b.alias}/{bucket_b}"
    last_out = ""
    last_err = ""
    for i in range(max(1, attempts)):
        rc, out, err = mc_mirror(mc_path, src, dst, remove=remove, overwrite=True)
        if rc == 0:
            return True, out or "ok"
        last_out, last_err = out, err
        if i < attempts - 1:
            time.sleep(2 ** i)
    return False, last_err or last_out


