# -*- coding: utf-8 -*-
"""
航点Excel导出对话框
功能: 选择导出属性和航点，导出为Excel文件
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
import subprocess
import platform
from collections import OrderedDict

from ..core.excel_exporter import ExcelExporter, FIELD_CONFIG


class ExcelExportDialog(tk.Toplevel):
    """航点Excel导出对话框"""

    def __init__(self, parent, initial_file=None):
        """
        初始化对话框
        Args:
            parent: 父窗口
            initial_file: 初始加载的GPX文件路径（可选）
        """
        super().__init__(parent)

        self.title("导出航点到Excel")
        self.geometry("800x600")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 字段勾选变量
        self.field_vars = {}
        for field_code, field_name in FIELD_CONFIG.items():
            self.field_vars[field_code] = tk.BooleanVar(value=True)

        # 文件数据存储: {文件路径: [waypoint_info, ...]}
        self.file_data = OrderedDict()

        self._create_widgets()
        self._center_window()

        # 自动加载初始文件
        if initial_file and os.path.exists(initial_file):
            self._load_gpx_file(initial_file)

    def _load_gpx_file(self, file_path):
        """加载单个GPX文件"""
        try:
            import gpxpy
            with open(file_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)

            waypoints = []
            for wp in gpx.waypoints:
                waypoints.append({
                    'waypoint': wp,
                    'checked': tk.BooleanVar(value=True),
                    'file_path': file_path
                })

            self.file_data[file_path] = waypoints
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败:\n{file_path}\n{e}")

        self._update_export_state()

    def _center_window(self):
        """窗口居中"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # 上半部分：左右分栏
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # ===== 左侧：属性选择 =====
        left_frame = ttk.LabelFrame(top_frame, text="选择导出属性", padding=10)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        # 全选按钮
        btn_row = ttk.Frame(left_frame)
        btn_row.pack(fill=X, pady=(0, 5))
        ttk.Button(btn_row, text="全选", command=self._select_all_fields, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(btn_row, text="取消全选", command=self._deselect_all_fields, bootstyle=INFO).pack(side=LEFT, padx=2)

        # 字段勾选框
        for field_code, field_name in FIELD_CONFIG.items():
            ttk.Checkbutton(
                left_frame,
                text=field_name,
                variable=self.field_vars[field_code],
                command=self._update_export_state
            ).pack(anchor=W, pady=2)

        # ===== 右侧：航点列表 =====
        right_frame = ttk.LabelFrame(top_frame, text="选择航点", padding=10)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))

        # 全选按钮（将在Task 6中重新实现）
        wp_btn_row = ttk.Frame(right_frame)
        wp_btn_row.pack(fill=X, pady=(0, 5))
        self.wp_select_all_btn = ttk.Button(wp_btn_row, text="全选", bootstyle=INFO, state=DISABLED)
        self.wp_select_all_btn.pack(side=LEFT, padx=2)
        self.wp_deselect_all_btn = ttk.Button(wp_btn_row, text="取消全选", bootstyle=INFO, state=DISABLED)
        self.wp_deselect_all_btn.pack(side=LEFT, padx=2)

        # 航点Treeview
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        columns = ("check", "index", "name", "lat", "lon")
        self.waypoint_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        self.waypoint_tree.heading("check", text="✓")
        self.waypoint_tree.heading("index", text="序号")
        self.waypoint_tree.heading("name", text="名称")
        self.waypoint_tree.heading("lat", text="纬度")
        self.waypoint_tree.heading("lon", text="经度")

        self.waypoint_tree.column("check", width=30, anchor=CENTER)
        self.waypoint_tree.column("index", width=50, anchor=CENTER)
        self.waypoint_tree.column("name", width=120)
        self.waypoint_tree.column("lat", width=80)
        self.waypoint_tree.column("lon", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.waypoint_tree.yview)
        self.waypoint_tree.configure(yscrollcommand=scrollbar.set)
        self.waypoint_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ===== 底部按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        self.export_btn = ttk.Button(btn_frame, text="导出", command=self._do_export, bootstyle=SUCCESS)
        self.export_btn.pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        # 状态标签
        self.status_label = ttk.Label(btn_frame, text="", foreground="gray")
        self.status_label.pack(side=LEFT, padx=15)

    def _select_all_fields(self):
        """全选属性"""
        for var in self.field_vars.values():
            var.set(True)
        self._update_export_state()

    def _deselect_all_fields(self):
        """取消全选属性"""
        for var in self.field_vars.values():
            var.set(False)
        self._update_export_state()

    def _update_export_state(self):
        """更新导出按钮状态"""
        # 临时占位，将在Task 6中重新实现
        self.export_btn.config(state=DISABLED)
        self.status_label.config(text="请添加GPX文件")

    def _do_export(self):
        """执行导出"""
        # 临时占位，将在Task 6中重新实现
        messagebox.showinfo("提示", "功能开发中")

    def _open_file_directory(self, filepath):
        """打开文件所在目录"""
        directory = os.path.dirname(os.path.abspath(filepath))
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", directory])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", directory])
        else:
            subprocess.Popen(["xdg-open", directory])
