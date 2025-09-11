from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from dataclasses import asdict, dataclass
from typing import Optional

import yaml
from apscheduler.schedulers.background import BackgroundScheduler

from miniosync.mc_sync import MinioEndpoint, sync_a_to_b
from miniosync.gui_blur import enable_acrylic


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "gui_config.yaml")


@dataclass
class GuiConfig:
    mc_path: str = "mc.exe"
    a_endpoint: str = "127.0.0.1:9000"
    a_secure: bool = False
    a_access: str = "minioadmin"
    a_secret: str = "minioadmin"

    b_endpoint: str = "127.0.0.1:9001"
    b_secure: bool = False
    b_access: str = "minioadmin"
    b_secret: str = "minioadmin"

    bucket_a: str = "my-bucket"
    bucket_b: str = "my-bucket"
    daily_time: str = "02:00"  # HH:MM
    remove: bool = False


def load_gui_config() -> GuiConfig:
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            cfg = GuiConfig(**{k: data.get(k, getattr(GuiConfig, k, None)) for k in GuiConfig.__dataclass_fields__.keys()})
            return cfg
        except Exception:
            pass
    return GuiConfig()


def save_gui_config(cfg: GuiConfig) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(cfg), f, allow_unicode=True, sort_keys=False)


class App:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("MinIO A -> B 增量同步 (mc)")
        self.root.geometry("780x600")
        try:
            # 固定窗口大小，禁止缩放与最大化
            self.root.resizable(False, False)
            self.root.minsize(780, 600)
            self.root.maxsize(780, 600)
        except Exception:
            pass
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        try:
            enable_acrylic(self.root.winfo_id())
        except Exception:
            pass
        self.scheduler = BackgroundScheduler()
        self.job = None
        self.cfg = load_gui_config()
        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 8}
        main = ctk.CTkFrame(self.root, corner_radius=16)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sec_mc = ctk.CTkFrame(main, corner_radius=14)
        sec_mc.pack(fill=tk.X, **pad)
        ctk.CTkLabel(sec_mc, text="mc 路径", anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.mc_path_var = tk.StringVar(value=self.cfg.mc_path)
        ctk.CTkEntry(sec_mc, textvariable=self.mc_path_var, width=480).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ctk.CTkButton(sec_mc, text="浏览", command=self._browse_mc, corner_radius=12).grid(row=0, column=2, padx=6)
        sec_mc.grid_columnconfigure(1, weight=1)

        sec_ab = ctk.CTkFrame(main, corner_radius=14)
        sec_ab.pack(fill=tk.X, **pad)

        # A
        box_a = ctk.CTkFrame(sec_ab, corner_radius=12)
        box_a.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        ctk.CTkLabel(box_a, text="服务器 A (源)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6,2))
        self.a_endpoint_var = tk.StringVar(value=self.cfg.a_endpoint)
        self.a_secure_var = tk.BooleanVar(value=self.cfg.a_secure)
        self.a_access_var = tk.StringVar(value=self.cfg.a_access)
        self.a_secret_var = tk.StringVar(value=self.cfg.a_secret)
        self._row(box_a, 1, "地址 host:port", self.a_endpoint_var)
        ctk.CTkCheckBox(box_a, text="https", variable=self.a_secure_var).grid(row=1, column=2, padx=6)
        self._row(box_a, 2, "AccessKey", self.a_access_var)
        self._row(box_a, 3, "SecretKey", self.a_secret_var, show="*")

        # B
        box_b = ctk.CTkFrame(sec_ab, corner_radius=12)
        box_b.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        ctk.CTkLabel(box_b, text="服务器 B (目标)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6,2))
        self.b_endpoint_var = tk.StringVar(value=self.cfg.b_endpoint)
        self.b_secure_var = tk.BooleanVar(value=self.cfg.b_secure)
        self.b_access_var = tk.StringVar(value=self.cfg.b_access)
        self.b_secret_var = tk.StringVar(value=self.cfg.b_secret)
        self._row(box_b, 1, "地址 host:port", self.b_endpoint_var)
        ctk.CTkCheckBox(box_b, text="https", variable=self.b_secure_var).grid(row=1, column=2, padx=6)
        self._row(box_b, 2, "AccessKey", self.b_access_var)
        self._row(box_b, 3, "SecretKey", self.b_secret_var, show="*")

        sec_ab.grid_columnconfigure(0, weight=1)
        sec_ab.grid_columnconfigure(1, weight=1)

        sec_opt = ctk.CTkFrame(main, corner_radius=14)
        sec_opt.pack(fill=tk.X, **pad)
        self.bucket_a_var = tk.StringVar(value=self.cfg.bucket_a)
        self.bucket_b_var = tk.StringVar(value=self.cfg.bucket_b)
        self.time_var = tk.StringVar(value=self.cfg.daily_time)
        self.remove_var = tk.BooleanVar(value=self.cfg.remove)
        self._row(sec_opt, 0, "A 桶 (bucket A)", self.bucket_a_var)
        self._row(sec_opt, 1, "B 桶 (bucket B)", self.bucket_b_var)
        self._row(sec_opt, 2, "每日时间 HH:MM", self.time_var)
        ctk.CTkCheckBox(sec_opt, text="镜像删除(删除目标多余)", variable=self.remove_var).grid(row=2, column=2, padx=6)

        sec_btn = ctk.CTkFrame(main, corner_radius=14)
        sec_btn.pack(fill=tk.X, **pad)
        ctk.CTkButton(sec_btn, text="保存配置", command=self._on_save, corner_radius=14).pack(side=tk.LEFT, padx=6, pady=6)
        ctk.CTkButton(sec_btn, text="立即同步", command=self._on_sync_now, corner_radius=14).pack(side=tk.LEFT, padx=6, pady=6)
        self.start_btn = ctk.CTkButton(sec_btn, text="启动定时", command=self._on_start_schedule, corner_radius=14)
        self.stop_btn = ctk.CTkButton(sec_btn, text="停止定时", command=self._on_stop_schedule, state=tk.DISABLED, corner_radius=14)
        self.start_btn.pack(side=tk.LEFT, padx=6, pady=6)
        self.stop_btn.pack(side=tk.LEFT, padx=6, pady=6)

        sec_log = ctk.CTkFrame(main, corner_radius=14)
        sec_log.pack(fill=tk.BOTH, expand=True, **pad)
        self.log = tk.Text(sec_log, height=12, relief="flat")
        self.log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _row(self, parent, r, label, var, show: Optional[str] = None) -> None:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(row=r, column=0, sticky="w", padx=6, pady=6)
        e = ctk.CTkEntry(parent, textvariable=var, width=280)
        if show:
            e.configure(show=show)
        e.grid(row=r, column=1, sticky="ew", padx=6, pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _browse_mc(self) -> None:
        path = filedialog.askopenfilename(title="选择 mc 可执行文件")
        if path:
            self.mc_path_var.set(path)

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def _current_cfg(self) -> GuiConfig:
        return GuiConfig(
            mc_path=self.mc_path_var.get(),
            a_endpoint=self.a_endpoint_var.get(),
            a_secure=self.a_secure_var.get(),
            a_access=self.a_access_var.get(),
            a_secret=self.a_secret_var.get(),
            b_endpoint=self.b_endpoint_var.get(),
            b_secure=self.b_secure_var.get(),
            b_access=self.b_access_var.get(),
            b_secret=self.b_secret_var.get(),
            bucket_a=self.bucket_a_var.get(),
            bucket_b=self.bucket_b_var.get(),
            daily_time=self.time_var.get(),
            remove=self.remove_var.get(),
        )

    def _on_save(self) -> None:
        self.cfg = self._current_cfg()
        save_gui_config(self.cfg)
        self._append_log("配置已保存")

    def _run_sync_thread(self, cfg: GuiConfig) -> None:
        self._append_log("开始同步...")
        a = MinioEndpoint(alias="a", endpoint=cfg.a_endpoint, access_key=cfg.a_access, secret_key=cfg.a_secret, secure=cfg.a_secure)
        b = MinioEndpoint(alias="b", endpoint=cfg.b_endpoint, access_key=cfg.b_access, secret_key=cfg.b_secret, secure=cfg.b_secure)
        ok, msg = sync_a_to_b(cfg.mc_path, a, b, cfg.bucket_a, cfg.bucket_b, remove=cfg.remove)
        if ok:
            self._append_log("同步完成\n" + msg)
        else:
            self._append_log("同步失败\n" + msg)

    def _on_sync_now(self) -> None:
        cfg = self._current_cfg()
        threading.Thread(target=self._run_sync_thread, args=(cfg,), daemon=True).start()

    def _on_start_schedule(self) -> None:
        cfg = self._current_cfg()
        try:
            hh, mm = cfg.daily_time.strip().split(":")
            hh = int(hh)
            mm = int(mm)
            if not (0 <= hh < 24 and 0 <= mm < 60):
                raise ValueError
        except Exception:
            messagebox.showerror("错误", "时间格式应为 HH:MM，例如 02:30")
            return

        if not self.scheduler.running:
            self.scheduler.start()
        if self.job:
            self.job.remove()
        self.job = self.scheduler.add_job(lambda: self._on_sync_now(), "cron", hour=hh, minute=mm)
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._append_log(f"已启动定时：每日 {cfg.daily_time}")

    def _on_stop_schedule(self) -> None:
        if self.job:
            self.job.remove()
            self.job = None
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self._append_log("已停止定时")


def main() -> None:
    root = ctk.CTk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()


