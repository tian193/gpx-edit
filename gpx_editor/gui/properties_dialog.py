# -*- coding: utf-8 -*-
"""
属性对话框
功能: MapSource风格分标签页属性编辑（航点/航迹）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *


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
    """航迹属性对话框 - MapSource风格"""

    def __init__(self, parent, track):
        self.result = False
        self.track = track

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"航迹属性 — {track.name or '未命名'}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        self.dialog.geometry("800x600")

        self._create_widgets()

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

        # 标签页1: 航迹点列表
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="航迹点列表")
        self._create_point_list_tab(tab1)

        # 标签页2: 统计汇总
        tab2 = ttk.Frame(notebook, padding=15)
        notebook.add(tab2, text="统计汇总")
        self._create_stats_tab(tab2)

        # 标签页3: 海拔剖面图
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="海拔剖面图")
        self._create_profile_tab(tab3)

        # 关闭按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="关闭", command=self._on_close, width=10).pack(side=RIGHT, padx=5)

    def _create_point_list_tab(self, parent):
        """航迹点列表标签页"""
        from ..core.track_stats import get_point_details, format_time_delta, format_direction

        # 列定义
        columns = ("index", "time", "elevation", "latitude", "longitude",
                   "seg_dist", "seg_time", "seg_speed", "bearing")
        col_names = {
            "index": "索引", "time": "时间", "elevation": "海拔(m)",
            "latitude": "纬度", "longitude": "经度",
            "seg_dist": "航段距离(m)", "seg_time": "航段时间",
            "seg_speed": "航段速度(km/h)", "bearing": "航段方向"
        }
        col_widths = {
            "index": 50, "time": 150, "elevation": 70,
            "latitude": 100, "longitude": 100,
            "seg_dist": 90, "seg_time": 80,
            "seg_speed": 100, "bearing": 70
        }

        # Treeview + 滚动条
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=HORIZONTAL)

        self.point_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set
        )
        scrollbar_y.config(command=self.point_tree.yview)
        scrollbar_x.config(command=self.point_tree.xview)

        scrollbar_y.pack(side=RIGHT, fill=Y)
        scrollbar_x.pack(side=BOTTOM, fill=X)
        self.point_tree.pack(fill=BOTH, expand=True)

        # 设置列标题和宽度
        for col in columns:
            self.point_tree.heading(col, text=col_names[col])
            self.point_tree.column(col, width=col_widths[col], minwidth=40)

        # 填充数据
        details = get_point_details(self.track)
        for d in details:
            time_str = d['time'].strftime("%Y-%m-%d %H:%M:%S") if d['time'] else "—"
            ele_str = f"{d['elevation']:.1f}" if d['elevation'] is not None else "—"
            lat_str = f"{d['latitude']:.6f}" if d['latitude'] is not None else "—"
            lon_str = f"{d['longitude']:.6f}" if d['longitude'] is not None else "—"

            if d['index'] < len(details) - 1:
                dist_str = f"{d['seg_distance']:.1f}"
                time_d_str = format_time_delta(d['seg_time']) if d['seg_time'] is not None else "—"
                speed_str = f"{d['seg_speed']:.1f}" if d['seg_speed'] is not None else "—"
                bear_str = f"{d['seg_bearing']:.0f}° {format_direction(d['seg_bearing'])}" if d['seg_bearing'] is not None else "—"
            else:
                dist_str = "—"
                time_d_str = "—"
                speed_str = "—"
                bear_str = "—"

            self.point_tree.insert("", END, values=(
                d['index'], time_str, ele_str, lat_str, lon_str,
                dist_str, time_d_str, speed_str, bear_str
            ))

    def _create_stats_tab(self, parent):
        """统计汇总标签页"""
        from ..core.track_stats import get_track_statistics, format_time_delta

        stats = get_track_statistics(self.track)

        # 用两列布局
        info_frame = ttk.LabelFrame(parent, text="航迹统计", padding=15)
        info_frame.pack(fill=X, pady=(0, 10))

        row = 0
        items = [
            ("航迹点数量:", f"{stats['total_points']} 个"),
            ("总长度:", self._format_distance(stats['total_distance'])),
            ("总时间:", format_time_delta(stats['total_time']) if stats['total_time'] is not None else "—"),
            ("平均速度:", f"{stats['avg_speed']:.1f} km/h" if stats['avg_speed'] is not None else "—"),
        ]
        for label, value in items:
            ttk.Label(info_frame, text=label, font=("", 10)).grid(
                row=row, column=0, sticky=W, pady=4, padx=(0, 10))
            ttk.Label(info_frame, text=value, font=("", 10, "bold")).grid(
                row=row, column=1, sticky=W, pady=4)
            row += 1

        ele_frame = ttk.LabelFrame(parent, text="海拔统计", padding=15)
        ele_frame.pack(fill=X, pady=(0, 10))

        row = 0
        ele_items = [
            ("最大海拔:", f"{stats['max_elevation']:.1f} m" if stats['max_elevation'] is not None else "—"),
            ("最小海拔:", f"{stats['min_elevation']:.1f} m" if stats['min_elevation'] is not None else "—"),
            ("累计爬升:", f"{stats['elevation_gain']:.1f} m"),
            ("累计下降:", f"{stats['elevation_loss']:.1f} m"),
        ]
        for label, value in ele_items:
            ttk.Label(ele_frame, text=label, font=("", 10)).grid(
                row=row, column=0, sticky=W, pady=4, padx=(0, 10))
            ttk.Label(ele_frame, text=value, font=("", 10, "bold")).grid(
                row=row, column=1, sticky=W, pady=4)
            row += 1

    def _create_profile_tab(self, parent):
        """海拔剖面图标签页"""
        from ..core.track_stats import get_elevation_profile_data
        from .elevation_chart import ElevationChart

        chart = ElevationChart(parent, width=700, height=350)
        chart.pack(fill=BOTH, expand=True, padx=5, pady=5)

        data = get_elevation_profile_data(self.track)
        if data:
            chart.set_data(data)
        else:
            chart.set_data([])

    @staticmethod
    def _format_distance(meters):
        """格式化距离"""
        if meters < 1000:
            return f"{meters:.1f} m"
        return f"{meters / 1000:.2f} km"

    def _on_close(self):
        self.dialog.destroy()
