from __future__ import annotations

import argparse
import sys

from .config import load_config
from .sync import sync_down, sync_up, watch_loop


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="miniosync", description="MinIO 同步工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sync = sub.add_parser("sync", help="执行同步")
    sync_sub = sync.add_subparsers(dest="direction", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--config", required=True, help="配置文件路径 config.yaml")
        sp.add_argument("--mirror", action="store_true", help="镜像删除")
        sp.add_argument("--watch", type=int, default=0, help="轮询间隔秒，0 表示只执行一次")

    up = sync_sub.add_parser("up", help="本地 -> MinIO")
    add_common(up)

    down = sync_sub.add_parser("down", help="MinIO -> 本地")
    add_common(down)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)

    cfg = load_config(ns.config)
    if ns.mirror:
        cfg.delete_extraneous = True

    if ns.direction == "up":
        if ns.watch and ns.watch > 0:
            watch_loop("up", cfg, ns.watch)
        else:
            sync_up(cfg)
            return 0
    elif ns.direction == "down":
        if ns.watch and ns.watch > 0:
            watch_loop("down", cfg, ns.watch)
        else:
            sync_down(cfg)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


