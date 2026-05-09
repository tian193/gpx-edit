# -*- coding: utf-8 -*-
"""
主窗口模块
功能: 应用程序主窗口界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class MainWindow(ttkb.Window):
    """主窗口类"""

    def __init__(self):
        super().__init__(
            title="GPX编辑器",
            themename="litera",
            size=(1200, 800),
            minsize=(800, 600)
        )

        self.current_file = None
        self.gpx_data = None

        self._setup_ui()
        self._create_menu()
        self._create_toolbar()
        self._create_main_layout()
        self._create_statusbar()

    def _setup_ui(self):
        """初始化界面"""
        self.center_window()

    def center_window(self):
        """窗口居中"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)

        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="添加航点", command=self.add_waypoint)
        edit_menu.add_command(label="添加航迹", command=self.add_track)

        # 导出菜单
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="导出", menu=export_menu)
        export_menu.add_command(label="导出为TXT", command=self.export_txt)
        export_menu.add_command(label="导出为GDB", command=self.export_gdb)
        export_menu.add_separator()
        export_menu.add_command(label="批量导出TXT", command=self.batch_export_txt)
        export_menu.add_command(label="批量导出GDB", command=self.batch_export_gdb)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="批量匹配航点", command=self.batch_match_waypoints)
        tools_menu.add_command(label="GPX属性编辑", command=self.gpx_editor)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

        # 绑定快捷键
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=5, pady=2)

        ttk.Button(toolbar, text="新建", command=self.new_file, bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        ttk.Button(toolbar, text="打开", command=self.open_file, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(toolbar, text="保存", command=self.save_file, bootstyle=PRIMARY).pack(side=LEFT, padx=2)

        ttk.Separator(toolbar, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)

        ttk.Button(toolbar, text="添加航点", command=self.add_waypoint, bootstyle=WARNING).pack(side=LEFT, padx=2)
        ttk.Button(toolbar, text="添加航迹", command=self.add_track, bootstyle=WARNING).pack(side=LEFT, padx=2)

    def _create_main_layout(self):
        """创建主布局"""
        # 主分割窗口
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 航点/航迹列表
        left_frame = ttk.LabelFrame(paned, text="数据列表", padding=5)
        paned.add(left_frame, weight=1)

        # 树形列表
        self.tree = ttk.Treeview(left_frame, columns=("type", "name", "lat", "lon"), show="headings")
        self.tree.heading("type", text="类型")
        self.tree.heading("name", text="名称")
        self.tree.heading("lat", text="纬度")
        self.tree.heading("lon", text="经度")
        self.tree.column("type", width=60)
        self.tree.column("name", width=120)
        self.tree.column("lat", width=100)
        self.tree.column("lon", width=100)
        self.tree.pack(fill=BOTH, expand=True)

        # 右侧面板 - 地图和详情
        right_frame = ttk.LabelFrame(paned, text="地图视图", padding=5)
        paned.add(right_frame, weight=2)

        # 地图占位符
        self.map_label = ttk.Label(right_frame, text="地图区域", anchor=CENTER)
        self.map_label.pack(fill=BOTH, expand=True)

    def _create_statusbar(self):
        """创建状态栏"""
        statusbar = ttk.Frame(self)
        statusbar.pack(fill=X, side=BOTTOM, padx=5, pady=2)

        self.status_label = ttk.Label(statusbar, text="就绪")
        self.status_label.pack(side=LEFT)

        self.file_label = ttk.Label(statusbar, text="未打开文件")
        self.file_label.pack(side=RIGHT)

    def new_file(self):
        """新建文件"""
        self.current_file = None
        self.gpx_data = None
        self.tree.delete(*self.tree.get_children())
        self.file_label.config(text="未打开文件")
        self.status_label.config(text="已新建空白文件")

    def open_file(self):
        """打开文件"""
        filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.current_file = filepath
            self.file_label.config(text=filepath)
            self.status_label.config(text="已打开文件")

    def save_file(self):
        """保存文件"""
        if self.current_file:
            self.status_label.config(text="已保存")
        else:
            self.save_as_file()

    def save_as_file(self):
        """另存为"""
        filetypes = [("GPX文件", "*.gpx")]
        filepath = filedialog.asksaveasfilename(defaultextension=".gpx", filetypes=filetypes)
        if filepath:
            self.current_file = filepath
            self.file_label.config(text=filepath)
            self.status_label.config(text="已保存")

    def add_waypoint(self):
        """添加航点"""
        self.status_label.config(text="添加航点功能待实现")

    def add_track(self):
        """添加航迹"""
        self.status_label.config(text="添加航迹功能待实现")

    def export_txt(self):
        """导出TXT"""
        self.status_label.config(text="导出TXT功能待实现")

    def export_gdb(self):
        """导出GDB"""
        self.status_label.config(text="导出GDB功能待实现")

    def batch_export_txt(self):
        """批量导出TXT"""
        self.status_label.config(text="批量导出TXT功能待实现")

    def batch_export_gdb(self):
        """批量导出GDB"""
        self.status_label.config(text="批量导出GDB功能待实现")

    def show_about(self):
        """显示关于"""
        messagebox.showinfo("关于", "GPX编辑器 v1.0.0\n\nGPX航点航迹编辑处理工具")

    def batch_match_waypoints(self):
        """打开批量匹配航点对话框"""
        from .batch_match_dialog import BatchMatchDialog
        BatchMatchDialog(self)

    def gpx_editor(self):
        """打开GPX属性编辑器对话框"""
        from .gpx_editor_dialog import GpxEditorDialog
        GpxEditorDialog(self)
