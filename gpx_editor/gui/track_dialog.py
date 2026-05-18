# -*- coding: utf-8 -*-
"""
航迹编辑对话框
功能: 添加/编辑航迹属性
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class TrackDialog:
    """航迹编辑对话框"""

    def __init__(self, parent, track=None):
        """
        Args:
            parent: 父窗口
            track: gpxpy GPXTrack对象，None表示添加模式
        """
        self.result = None
        self.track = track

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑航迹" if track else "添加航迹")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self._create_widgets()
        self._populate_fields()

        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # 名称
        ttk.Label(main_frame, text="航迹名称:").grid(row=0, column=0, sticky=W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=5, padx=(5, 0))

        # 描述
        ttk.Label(main_frame, text="描述:").grid(row=1, column=0, sticky=W, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.desc_var, width=30).grid(row=1, column=1, pady=5, padx=(5, 0))

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0))

        ttk.Button(btn_frame, text="确定", command=self._on_ok, bootstyle=PRIMARY, width=10).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=LEFT, padx=5)

    def _populate_fields(self):
        """填充现有数据（编辑模式）"""
        if self.track:
            self.name_var.set(self.track.name or "")
            self.desc_var.set(self.track.description or "")

    def _on_ok(self):
        """确定按钮"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入航迹名称")
            return

        self.result = name
        self.dialog.destroy()

    def _on_cancel(self):
        """取消按钮"""
        self.dialog.destroy()
