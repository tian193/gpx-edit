# -*- coding: utf-8 -*-
"""
属性对话框
功能: MapSource风格分标签页属性编辑（航点/航迹）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *

from ..core.track import TrackManager
from ..utils.helpers import format_distance


class WaypointPropertiesDialog:
    """航点属性对话框 - 分标签页"""

    def __init__(self, parent, waypoint):
        self.result = False
        self.waypoint = waypoint

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"航点属性 - {waypoint.name or '未命名'}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.geometry("450x400")

        self._create_widgets()
        self._populate_fields()

        # 居中
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=BOTH, expand=True)

        # 标签页1: 基本信息
        tab1 = ttk.Frame(notebook, padding=10)
        notebook.add(tab1, text="基本信息")
        self._create_basic_tab(tab1)

        # 标签页2: 位置坐标
        tab2 = ttk.Frame(notebook, padding=10)
        notebook.add(tab2, text="位置坐标")
        self._create_location_tab(tab2)

        # 标签页3: 详细描述
        tab3 = ttk.Frame(notebook, padding=10)
        notebook.add(tab3, text="详细描述")
        self._create_description_tab(tab3)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok, bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=RIGHT, padx=5)

    def _create_basic_tab(self, parent):
        row = 0
        ttk.Label(parent, text="名称:").grid(row=row, column=0, sticky=W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.name_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="符号:").grid(row=row, column=0, sticky=W, pady=5)
        self.symbol_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.symbol_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="类型:").grid(row=row, column=0, sticky=W, pady=5)
        self.type_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.type_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

    def _create_location_tab(self, parent):
        row = 0
        ttk.Label(parent, text="纬度:").grid(row=row, column=0, sticky=W, pady=5)
        self.lat_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.lat_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))
        ttk.Label(parent, text="(-90 ~ 90)", foreground="gray").grid(row=row, column=2, padx=5)

        row += 1
        ttk.Label(parent, text="经度:").grid(row=row, column=0, sticky=W, pady=5)
        self.lon_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.lon_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))
        ttk.Label(parent, text="(-180 ~ 180)", foreground="gray").grid(row=row, column=2, padx=5)

        row += 1
        ttk.Label(parent, text="海拔(米):").grid(row=row, column=0, sticky=W, pady=5)
        self.ele_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.ele_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

    def _create_description_tab(self, parent):
        row = 0
        ttk.Label(parent, text="描述:").grid(row=row, column=0, sticky=NW, pady=5)
        self.desc_text = tk.Text(parent, width=35, height=4)
        self.desc_text.grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="备注:").grid(row=row, column=0, sticky=NW, pady=5)
        self.comment_text = tk.Text(parent, width=35, height=4)
        self.comment_text.grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="来源:").grid(row=row, column=0, sticky=W, pady=5)
        self.source_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.source_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

    def _populate_fields(self):
        wpt = self.waypoint
        self.name_var.set(wpt.name or "")
        self.symbol_var.set(wpt.symbol or "")
        self.type_var.set(wpt.type or "")
        if wpt.latitude is not None:
            self.lat_var.set(str(wpt.latitude))
        if wpt.longitude is not None:
            self.lon_var.set(str(wpt.longitude))
        if wpt.elevation is not None:
            self.ele_var.set(str(wpt.elevation))
        if wpt.description:
            self.desc_text.insert("1.0", wpt.description)
        if wpt.comment:
            self.comment_text.insert("1.0", wpt.comment)
        self.source_var.set(wpt.source or "")

    def _on_ok(self):
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
        ele = float(ele_str) if ele_str else None

        # 应用到航点对象
        wpt = self.waypoint
        wpt.name = self.name_var.get().strip() or None
        wpt.symbol = self.symbol_var.get().strip() or None
        wpt.type = self.type_var.get().strip() or None
        wpt.latitude = lat
        wpt.longitude = lon
        wpt.elevation = ele
        wpt.description = self.desc_text.get("1.0", END).strip() or None
        wpt.comment = self.comment_text.get("1.0", END).strip() or None
        wpt.source = self.source_var.get().strip() or None

        self.result = True
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()


class TrackPropertiesDialog:
    """航迹属性对话框 - 分标签页"""

    def __init__(self, parent, track):
        self.result = False
        self.track = track

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"航迹属性 - {track.name or '未命名'}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.geometry("450x400")

        self._create_widgets()
        self._populate_fields()

        # 居中
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=BOTH, expand=True)

        # 标签页1: 基本信息
        tab1 = ttk.Frame(notebook, padding=10)
        notebook.add(tab1, text="基本信息")
        self._create_basic_tab(tab1)

        # 标签页2: 详细描述
        tab2 = ttk.Frame(notebook, padding=10)
        notebook.add(tab2, text="详细描述")
        self._create_description_tab(tab2)

        # 标签页3: 统计信息
        tab3 = ttk.Frame(notebook, padding=10)
        notebook.add(tab3, text="统计信息")
        self._create_stats_tab(tab3)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok, bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=RIGHT, padx=5)

    def _create_basic_tab(self, parent):
        row = 0
        ttk.Label(parent, text="名称:").grid(row=row, column=0, sticky=W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.name_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="类型:").grid(row=row, column=0, sticky=W, pady=5)
        self.type_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.type_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="编号:").grid(row=row, column=0, sticky=W, pady=5)
        self.number_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.number_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="来源:").grid(row=row, column=0, sticky=W, pady=5)
        self.source_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.source_var, width=35).grid(row=row, column=1, pady=5, padx=(5, 0))

    def _create_description_tab(self, parent):
        row = 0
        ttk.Label(parent, text="描述:").grid(row=row, column=0, sticky=NW, pady=5)
        self.desc_text = tk.Text(parent, width=35, height=4)
        self.desc_text.grid(row=row, column=1, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="备注:").grid(row=row, column=0, sticky=NW, pady=5)
        self.comment_text = tk.Text(parent, width=35, height=4)
        self.comment_text.grid(row=row, column=1, pady=5, padx=(5, 0))

    def _create_stats_tab(self, parent):
        track = self.track
        total_points = TrackManager.get_track_point_count(track)
        total_distance = TrackManager.get_track_total_distance(track)
        seg_count = len(track.segments)

        row = 0
        ttk.Label(parent, text="总点数:").grid(row=row, column=0, sticky=W, pady=5)
        ttk.Label(parent, text=str(total_points)).grid(row=row, column=1, sticky=W, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="段数:").grid(row=row, column=0, sticky=W, pady=5)
        ttk.Label(parent, text=str(seg_count)).grid(row=row, column=1, sticky=W, pady=5, padx=(5, 0))

        row += 1
        ttk.Label(parent, text="总距离:").grid(row=row, column=0, sticky=W, pady=5)
        dist_text = format_distance(total_distance)
        ttk.Label(parent, text=dist_text).grid(row=row, column=1, sticky=W, pady=5, padx=(5, 0))

    def _populate_fields(self):
        trk = self.track
        self.name_var.set(trk.name or "")
        self.type_var.set(trk.type or "")
        if trk.number is not None:
            self.number_var.set(str(trk.number))
        self.source_var.set(trk.source or "")
        if trk.description:
            self.desc_text.insert("1.0", trk.description)
        if trk.comment:
            self.comment_text.insert("1.0", trk.comment)

    def _on_ok(self):
        trk = self.track
        trk.name = self.name_var.get().strip() or None
        trk.type = self.type_var.get().strip() or None
        num_str = self.number_var.get().strip()
        trk.number = int(num_str) if num_str else None
        trk.source = self.source_var.get().strip() or None
        trk.description = self.desc_text.get("1.0", END).strip() or None
        trk.comment = self.comment_text.get("1.0", END).strip() or None

        self.result = True
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()
