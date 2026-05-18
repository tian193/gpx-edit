# -*- coding: utf-8 -*-
"""
航点编辑对话框
功能: 添加/编辑航点
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class WaypointDialog:
    """航点编辑对话框"""

    def __init__(self, parent, waypoint=None, lat=None, lon=None):
        """
        Args:
            parent: 父窗口
            waypoint: gpxpy GPXWaypoint对象，None表示添加模式
            lat: 预填纬度（地图点击时使用）
            lon: 预填经度（地图点击时使用）
        """
        self.result = None
        self.waypoint = waypoint
        self._preset_lat = lat
        self._preset_lon = lon

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑航点" if waypoint else "添加航点")
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
        ttk.Label(main_frame, text="名称:").grid(row=0, column=0, sticky=W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=5, padx=(5, 0))

        # 纬度
        ttk.Label(main_frame, text="纬度:").grid(row=1, column=0, sticky=W, pady=5)
        self.lat_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.lat_var, width=30).grid(row=1, column=1, pady=5, padx=(5, 0))
        ttk.Label(main_frame, text="(-90 ~ 90)", foreground="gray").grid(row=1, column=2, padx=5)

        # 经度
        ttk.Label(main_frame, text="经度:").grid(row=2, column=0, sticky=W, pady=5)
        self.lon_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.lon_var, width=30).grid(row=2, column=1, pady=5, padx=(5, 0))
        ttk.Label(main_frame, text="(-180 ~ 180)", foreground="gray").grid(row=2, column=2, padx=5)

        # 海拔
        ttk.Label(main_frame, text="海拔(米):").grid(row=3, column=0, sticky=W, pady=5)
        self.ele_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.ele_var, width=30).grid(row=3, column=1, pady=5, padx=(5, 0))
        ttk.Label(main_frame, text="(可选)", foreground="gray").grid(row=3, column=2, padx=5)

        # 描述
        ttk.Label(main_frame, text="描述:").grid(row=4, column=0, sticky=W, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.desc_var, width=30).grid(row=4, column=1, pady=5, padx=(5, 0))

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(15, 0))

        ttk.Button(btn_frame, text="确定", command=self._on_ok, bootstyle=PRIMARY, width=10).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=LEFT, padx=5)

    def _populate_fields(self):
        """填充现有数据（编辑模式或预填坐标）"""
        if self.waypoint:
            self.name_var.set(self.waypoint.name or "")
            if self.waypoint.latitude is not None:
                self.lat_var.set(str(self.waypoint.latitude))
            if self.waypoint.longitude is not None:
                self.lon_var.set(str(self.waypoint.longitude))
            if self.waypoint.elevation is not None:
                self.ele_var.set(str(self.waypoint.elevation))
            self.desc_var.set(self.waypoint.description or "")
        else:
            # 预填坐标（地图点击）
            if self._preset_lat is not None:
                self.lat_var.set(f"{self._preset_lat:.6f}")
            if self._preset_lon is not None:
                self.lon_var.set(f"{self._preset_lon:.6f}")

    def _on_ok(self):
        """确定按钮"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入航点名称")
            return

        try:
            lat = float(self.lat_var.get())
            if not (-90 <= lat <= 90):
                messagebox.showwarning("提示", "纬度必须在 -90 到 90 之间")
                return
        except ValueError:
            messagebox.showwarning("提示", "纬度格式不正确")
            return

        try:
            lon = float(self.lon_var.get())
            if not (-180 <= lon <= 180):
                messagebox.showwarning("提示", "经度必须在 -180 到 180 之间")
                return
        except ValueError:
            messagebox.showwarning("提示", "经度格式不正确")
            return

        ele_str = self.ele_var.get().strip()
        ele = None
        if ele_str:
            try:
                ele = float(ele_str)
            except ValueError:
                messagebox.showwarning("提示", "海拔格式不正确")
                return

        desc = self.desc_var.get().strip() or None

        self.result = (name, lat, lon, ele, desc)
        self.dialog.destroy()

    def _on_cancel(self):
        """取消按钮"""
        self.dialog.destroy()
