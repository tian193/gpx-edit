# -*- coding: utf-8 -*-
"""
移动航点对话框（三标签页版）
功能: 手动输入坐标 / 地图选点 / 精细移动
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.constants import *

from ..core.coord_converter import CoordConverter
from ..core.gpx_editor import GpxEditor


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
        self._esc_binding = None
        self._temp_marker = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"移动航点 — {waypoint.name or '未命名'}")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self._create_widgets()

        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 当前位置显示
        self._create_current_position_display(main_frame)

        # 标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=(10, 0))

        self._create_manual_tab()
        self._create_map_click_tab()
        self._create_fine_move_tab()

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok,
                   bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel,
                   width=10).pack(side=RIGHT, padx=5)

    def _create_current_position_display(self, parent):
        """创建当前位置显示区域"""
        wpt = self.waypoint
        group = ttk.LabelFrame(parent, text="当前位置", padding=8)
        group.pack(fill=X)

        if wpt.latitude is not None and wpt.longitude is not None:
            wgs_text = f"WGS84:  纬度 {wpt.latitude:.6f}  经度 {wpt.longitude:.6f}"
            cgcs_text = f"CGCS2000:  {CoordConverter.format_cgcs2000(wpt.latitude, wpt.longitude)}"
        else:
            wgs_text = "WGS84: 未知"
            cgcs_text = "CGCS2000: 未知"

        ttk.Label(group, text=wgs_text, foreground="gray").pack(anchor=W)
        ttk.Label(group, text=cgcs_text, foreground="gray").pack(anchor=W)

    # ============================================================
    # 标签页 1: 手动输入
    # ============================================================
    def _create_manual_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="手动输入")

        # 坐标系选择
        self.manual_coord_sys = tk.StringVar(value="wgs84")
        sys_frame = ttk.Frame(tab)
        sys_frame.pack(fill=X, pady=(0, 8))
        ttk.Radiobutton(sys_frame, text="WGS84 经纬度", variable=self.manual_coord_sys,
                        value="wgs84", command=self._on_manual_sys_change).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(sys_frame, text="CGCS2000 投影坐标", variable=self.manual_coord_sys,
                        value="cgcs2000", command=self._on_manual_sys_change).pack(side=LEFT)

        # WGS84 输入区
        self.wgs84_frame = ttk.Frame(tab)
        self.wgs84_frame.pack(fill=X, pady=3)

        ttk.Label(self.wgs84_frame, text="纬度:").grid(row=0, column=0, sticky=W, pady=3)
        self.lat_var = tk.StringVar()
        wpt = self.waypoint
        if wpt.latitude is not None:
            self.lat_var.set(str(wpt.latitude))
        ttk.Entry(self.wgs84_frame, textvariable=self.lat_var, width=25).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(self.wgs84_frame, text="经度:").grid(row=1, column=0, sticky=W, pady=3)
        self.lon_var = tk.StringVar()
        if wpt.longitude is not None:
            self.lon_var.set(str(wpt.longitude))
        ttk.Entry(self.wgs84_frame, textvariable=self.lon_var, width=25).grid(row=1, column=1, padx=(5, 0))

        # CGCS2000 输入区
        self.cgcs_frame = ttk.Frame(tab)
        self.cgcs_frame.pack(fill=X, pady=3)

        ttk.Label(self.cgcs_frame, text="带号:").grid(row=0, column=0, sticky=W, pady=3)
        self.zone_var = tk.StringVar(value="0")
        ttk.Entry(self.cgcs_frame, textvariable=self.zone_var, width=10).grid(row=0, column=1, padx=(5, 0), sticky=W)

        ttk.Label(self.cgcs_frame, text="X (东坐标):").grid(row=1, column=0, sticky=W, pady=3)
        self.cgcs_x_var = tk.StringVar()
        ttk.Entry(self.cgcs_frame, textvariable=self.cgcs_x_var, width=25).grid(row=1, column=1, padx=(5, 0))

        ttk.Label(self.cgcs_frame, text="Y (北坐标):").grid(row=2, column=0, sticky=W, pady=3)
        self.cgcs_y_var = tk.StringVar()
        ttk.Entry(self.cgcs_frame, textvariable=self.cgcs_y_var, width=25).grid(row=2, column=1, padx=(5, 0))

        # 如果当前有坐标，预填CGCS2000值
        if wpt.latitude is not None and wpt.longitude is not None:
            try:
                x, y, zone = CoordConverter.wgs84_to_cgcs2000(wpt.latitude, wpt.longitude)
                self.zone_var.set(str(zone))
                self.cgcs_x_var.set(f"{x:.3f}")
                self.cgcs_y_var.set(f"{y:.3f}")
            except Exception:
                pass

        # 初始隐藏CGCS2000区域
        self._on_manual_sys_change()

    def _on_manual_sys_change(self):
        """切换坐标系时显示/隐藏对应输入区"""
        if self.manual_coord_sys.get() == "wgs84":
            self.wgs84_frame.pack(fill=X, pady=3)
            self.cgcs_frame.pack_forget()
        else:
            self.wgs84_frame.pack_forget()
            self.cgcs_frame.pack(fill=X, pady=3)

    # ============================================================
    # 标签页 2: 地图选点
    # ============================================================
    def _create_map_click_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="地图选点")

        hint_text = (
            "操作步骤:\n"
            "1. 点击下方【确定】按钮\n"
            "2. 对话框关闭后，在地图上点击新位置\n"
            "3. 当前航点位置将以红色标记显示\n"
            "4. 按 ESC 可取消地图选点"
        )
        ttk.Label(tab, text=hint_text, justify=LEFT, foreground="#555555").pack(anchor=W, pady=10)

    # ============================================================
    # 标签页 3: 精细移动
    # ============================================================
    def _create_fine_move_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="精细移动")

        wpt = self.waypoint
        self._base_lat = wpt.latitude if wpt.latitude is not None else 0.0
        self._base_lon = wpt.longitude if wpt.longitude is not None else 0.0

        # 偏移输入区
        offset_frame = ttk.LabelFrame(tab, text="偏移量 (米)", padding=8)
        offset_frame.pack(fill=X, pady=(0, 8))

        ttk.Label(offset_frame, text="东西方向 (正=东, 负=西):").grid(row=0, column=0, sticky=W, pady=3)
        self.x_offset_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.x_offset_var, width=15).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(offset_frame, text="南北方向 (正=北, 负=南):").grid(row=1, column=0, sticky=W, pady=3)
        self.y_offset_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.y_offset_var, width=15).grid(row=1, column=1, padx=(5, 0))

        # 绑定输入变化事件，实时更新预览
        self.x_offset_var.trace_add("write", lambda *args: self._update_fine_preview())
        self.y_offset_var.trace_add("write", lambda *args: self._update_fine_preview())

        # 快捷按钮区
        quick_frame = ttk.LabelFrame(tab, text="快捷偏移", padding=8)
        quick_frame.pack(fill=X, pady=(0, 8))

        # 北/南按钮
        ns_frame = ttk.Frame(quick_frame)
        ns_frame.pack(pady=3)
        ttk.Button(ns_frame, text="北 +10m", width=10,
                   command=lambda: self._quick_offset(0, 10)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="北 +1m", width=10,
                   command=lambda: self._quick_offset(0, 1)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="南 -1m", width=10,
                   command=lambda: self._quick_offset(0, -1)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="南 -10m", width=10,
                   command=lambda: self._quick_offset(0, -10)).pack(side=LEFT, padx=2)

        # 东/西按钮
        ew_frame = ttk.Frame(quick_frame)
        ew_frame.pack(pady=3)
        ttk.Button(ew_frame, text="西 -10m", width=10,
                   command=lambda: self._quick_offset(-10, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="西 -1m", width=10,
                   command=lambda: self._quick_offset(-1, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="东 +1m", width=10,
                   command=lambda: self._quick_offset(1, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="东 +10m", width=10,
                   command=lambda: self._quick_offset(10, 0)).pack(side=LEFT, padx=2)

        # 重置按钮
        ttk.Button(quick_frame, text="重置为 0", width=10,
                   command=self._reset_fine_offset).pack(pady=5)

        # 预览区
        preview_frame = ttk.LabelFrame(tab, text="新位置预览", padding=8)
        preview_frame.pack(fill=X)

        self.fine_wgs_label = ttk.Label(preview_frame, text="WGS84: -", foreground="#333333")
        self.fine_wgs_label.pack(anchor=W)
        self.fine_cgcs_label = ttk.Label(preview_frame, text="CGCS2000: -", foreground="#333333")
        self.fine_cgcs_label.pack(anchor=W)

        # 初始预览
        self._update_fine_preview()

    def _quick_offset(self, dx, dy):
        """快捷偏移按钮回调"""
        try:
            cur_x = float(self.x_offset_var.get())
        except ValueError:
            cur_x = 0.0
        try:
            cur_y = float(self.y_offset_var.get())
        except ValueError:
            cur_y = 0.0

        self.x_offset_var.set(f"{cur_x + dx:.1f}")
        self.y_offset_var.set(f"{cur_y + dy:.1f}")

    def _reset_fine_offset(self):
        """重置偏移量"""
        self.x_offset_var.set("0")
        self.y_offset_var.set("0")

    def _update_fine_preview(self):
        """更新精细移动的新位置预览"""
        try:
            x_m = float(self.x_offset_var.get())
        except ValueError:
            x_m = 0.0
        try:
            y_m = float(self.y_offset_var.get())
        except ValueError:
            y_m = 0.0

        new_lat, new_lon = GpxEditor.offset_coordinates(self._base_lat, self._base_lon, x_m, y_m)
        self.fine_wgs_label.config(text=f"WGS84:  纬度 {new_lat:.6f}  经度 {new_lon:.6f}")
        self.fine_cgcs_label.config(text=f"CGCS2000:  {CoordConverter.format_cgcs2000(new_lat, new_lon)}")

    # ============================================================
    # 确定 / 取消
    # ============================================================
    def _on_ok(self):
        tab_index = self.notebook.index(self.notebook.select())

        if tab_index == 0:
            # 手动输入
            self._handle_manual_input()
        elif tab_index == 1:
            # 地图选点
            self.dialog.destroy()
            self._start_map_click()
        elif tab_index == 2:
            # 精细移动
            self._handle_fine_move()

    def _handle_manual_input(self):
        """处理手动输入模式"""
        if self.manual_coord_sys.get() == "wgs84":
            # WGS84 模式
            try:
                lat = float(self.lat_var.get())
                if not (-90 <= lat <= 90):
                    messagebox.showwarning("提示", "纬度必须在 -90 到 90 之间", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showwarning("提示", "纬度格式不正确", parent=self.dialog)
                return

            try:
                lon = float(self.lon_var.get())
                if not (-180 <= lon <= 180):
                    messagebox.showwarning("提示", "经度必须在 -180 到 180 之间", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showwarning("提示", "经度格式不正确", parent=self.dialog)
                return

            self.result = (lat, lon)
            self.dialog.destroy()
        else:
            # CGCS2000 模式
            try:
                zone = int(self.zone_var.get())
                if not (19 <= zone <= 42):
                    messagebox.showwarning("提示", "6度带带号必须在 19 到 42 之间（中国范围）", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showwarning("提示", "带号格式不正确", parent=self.dialog)
                return

            try:
                x = float(self.cgcs_x_var.get())
                if x < 0:
                    messagebox.showwarning("提示", "X 坐标必须为正数", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showwarning("提示", "X 坐标格式不正确", parent=self.dialog)
                return

            try:
                y = float(self.cgcs_y_var.get())
                if y < 0:
                    messagebox.showwarning("提示", "Y 坐标必须为正数", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showwarning("提示", "Y 坐标格式不正确", parent=self.dialog)
                return

            try:
                lat, lon = CoordConverter.cgcs2000_to_wgs84(x, y, zone)
                self.result = (lat, lon)
                self.dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"坐标转换失败: {str(e)}", parent=self.dialog)

    def _handle_fine_move(self):
        """处理精细移动模式"""
        try:
            x_m = float(self.x_offset_var.get())
        except ValueError:
            messagebox.showwarning("提示", "东西方向偏移量格式不正确", parent=self.dialog)
            return

        try:
            y_m = float(self.y_offset_var.get())
        except ValueError:
            messagebox.showwarning("提示", "南北方向偏移量格式不正确", parent=self.dialog)
            return

        if x_m == 0 and y_m == 0:
            messagebox.showinfo("提示", "偏移量为零，航点不会移动", parent=self.dialog)
            return

        new_lat, new_lon = GpxEditor.offset_coordinates(self._base_lat, self._base_lon, x_m, y_m)
        self.result = (new_lat, new_lon)
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()

    # ============================================================
    # 地图选点模式
    # ============================================================
    def _start_map_click(self):
        """开始地图点击模式"""
        # 在地图上标记当前位置
        wpt = self.waypoint
        if wpt.latitude is not None and wpt.longitude is not None:
            try:
                self._temp_marker = self.map_widget.set_marker(
                    wpt.latitude, wpt.longitude,
                    text=f"当前: {wpt.name}" if wpt.name else "当前"
                )
                # 尝试设置红色标记（marker颜色由库决定，此处尽量标注）
            except Exception:
                pass

        # 改变光标
        self.map_widget.canvas.config(cursor="crosshair")

        # 绑定点击事件
        self._click_binding = self.map_widget.canvas.bind("<Button-1>", self._on_map_click)

        # 绑定ESC取消（绑定到主窗口）
        top_level = self.map_widget.winfo_toplevel()
        self._esc_binding = top_level.bind("<Escape>", self._cancel_map_click)

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
        """清理地图点击绑定和临时标记"""
        # 恢复光标
        self.map_widget.canvas.config(cursor="")

        # 解绑点击事件
        if self._click_binding:
            self.map_widget.canvas.unbind("<Button-1>")
            self._click_binding = None

        # 解绑ESC
        top_level = self.map_widget.winfo_toplevel()
        if self._esc_binding:
            top_level.unbind("<Escape>")
            self._esc_binding = None

        # 删除临时标记
        if self._temp_marker:
            try:
                self._temp_marker.delete()
            except Exception:
                pass
            self._temp_marker = None
