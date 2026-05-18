# -*- coding: utf-8 -*-
"""
移动航点对话框
功能: 在地图上点击或手动输入坐标移动航点
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *


class MoveWaypointDialog:
    """移动航点对话框"""

    def __init__(self, parent, map_widget, waypoint):
        """
        Args:
            parent: 父窗口
            map_widget: TkinterMapView实例
            waypoint: 要移动的GPXWaypoint对象
        """
        self.result = None
        self.map_widget = map_widget
        self.waypoint = waypoint
        self._click_binding = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("移动航点")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self._create_widgets()

        # 居中
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # 当前位置
        wpt = self.waypoint
        current_text = f"当前位置: {wpt.latitude:.6f}, {wpt.longitude:.6f}" if wpt.latitude else "当前位置: 未知"
        ttk.Label(main_frame, text=current_text, foreground="gray").pack(anchor=W, pady=(0, 10))

        # 选择模式
        self.mode_var = tk.StringVar(value="coords")

        ttk.Radiobutton(main_frame, text="手动输入坐标", variable=self.mode_var,
                         value="coords", command=self._on_mode_change).pack(anchor=W)

        # 坐标输入区域
        self.coords_frame = ttk.Frame(main_frame)
        self.coords_frame.pack(fill=X, pady=5)

        ttk.Label(self.coords_frame, text="纬度:").grid(row=0, column=0, sticky=W, pady=3)
        self.lat_var = tk.StringVar()
        if wpt.latitude is not None:
            self.lat_var.set(str(wpt.latitude))
        ttk.Entry(self.coords_frame, textvariable=self.lat_var, width=25).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(self.coords_frame, text="经度:").grid(row=1, column=0, sticky=W, pady=3)
        self.lon_var = tk.StringVar()
        if wpt.longitude is not None:
            self.lon_var.set(str(wpt.longitude))
        ttk.Entry(self.coords_frame, textvariable=self.lon_var, width=25).grid(row=1, column=1, padx=(5, 0))

        ttk.Radiobutton(main_frame, text="在地图上点击选择位置", variable=self.mode_var,
                         value="map", command=self._on_mode_change).pack(anchor=W, pady=(10, 0))

        # 提示
        self.hint_label = ttk.Label(main_frame, text="", foreground="blue")
        self.hint_label.pack(anchor=W, pady=5)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(15, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok, bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=RIGHT, padx=5)

    def _on_mode_change(self):
        if self.mode_var.get() == "map":
            self.hint_label.config(text="点击确定后，在地图上点击新位置")
        else:
            self.hint_label.config(text="")

    def _on_ok(self):
        if self.mode_var.get() == "coords":
            # 手动输入模式
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

            self.result = (lat, lon)
            self.dialog.destroy()
        else:
            # 地图点击模式
            self.dialog.destroy()
            self._start_map_click()

    def _start_map_click(self):
        """开始地图点击模式"""
        # 改变光标
        self.map_widget.canvas.config(cursor="crosshair")
        # 绑定一次性点击事件
        self._click_binding = self.map_widget.canvas.bind("<Button-1>", self._on_map_click)
        # 绑定ESC取消
        self.map_widget.winfo_toplevel().bind("<Escape>", self._cancel_map_click)

    def _on_map_click(self, event):
        """地图点击回调"""
        try:
            lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
            self.result = (lat, lon)
        except Exception:
            pass
        self._cleanup_map_click()

    def _cancel_map_click(self, event=None):
        """取消地图点击"""
        self._cleanup_map_click()

    def _cleanup_map_click(self):
        """清理地图点击绑定"""
        self.map_widget.canvas.config(cursor="")
        if self._click_binding:
            self.map_widget.canvas.unbind("<Button-1>")
            self._click_binding = None
        self.map_widget.winfo_toplevel().unbind("<Escape>")

    def _on_cancel(self):
        self.dialog.destroy()
