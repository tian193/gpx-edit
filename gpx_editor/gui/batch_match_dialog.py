# -*- coding: utf-8 -*-
"""
批量航点匹配向导对话框
功能: 多步骤标签页向导，支持灵活的删除选项和多种输入方式
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import threading
import os

from ..core.batch_matcher import BatchMatcher, DeleteOptions


class BatchMatchDialog(tk.Toplevel):
    """批量航点匹配向导对话框"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("批量航点匹配向导")
        self.geometry("1000x800")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # 变量
        self.baseline_path = tk.StringVar()
        self.baseline_is_dir = tk.BooleanVar(value=False)
        self.baseline_merge = tk.BooleanVar(value=True)
        self.source_path = tk.StringVar()
        self.source_is_dir = tk.BooleanVar(value=False)
        self.output_dir = tk.StringVar()
        self.threshold = tk.StringVar(value="100")
        self.prefix = tk.StringVar(value="")

        # 删除选项
        self.delete_unmatched_baseline = tk.BooleanVar(value=False)
        self.delete_unmatched_source = tk.BooleanVar(value=False)
        self.delete_matched_baseline = tk.BooleanVar(value=False)
        self.delete_matched_source = tk.BooleanVar(value=False)

        # 处理状态
        self.is_processing = False

        # 基线航点缓存
        self.baseline_waypoints = None

        self._create_widgets()
        self._center_window()

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

        # 标签页控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 创建4个标签页
        self._create_file_selection_tab()
        self._create_match_settings_tab()
        self._create_delete_options_tab()
        self._create_preview_tab()

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)

        ttk.Button(btn_frame, text="上一步", command=self._prev_tab, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="下一步", command=self._next_tab, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self._on_close, bootstyle=SECONDARY).pack(side=RIGHT, padx=5)

        # 进度区域
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=X, pady=(0, 5))

        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(fill=X)

    def _create_file_selection_tab(self):
        """创建文件选择标签页"""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="  1. 文件选择  ")

        # 基线设置
        bl_frame = ttk.LabelFrame(tab, text="基线设置", padding=10)
        bl_frame.pack(fill=X, pady=(0, 10))

        bl_type_frame = ttk.Frame(bl_frame)
        bl_type_frame.pack(fill=X, pady=(0, 5))
        ttk.Radiobutton(bl_type_frame, text="单文件", variable=self.baseline_is_dir,
                         value=False, command=self._on_baseline_type_change).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(bl_type_frame, text="文件夹", variable=self.baseline_is_dir,
                         value=True, command=self._on_baseline_type_change).pack(side=LEFT)

        bl_path_frame = ttk.Frame(bl_frame)
        bl_path_frame.pack(fill=X, pady=5)
        ttk.Entry(bl_path_frame, textvariable=self.baseline_path, width=60).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(bl_path_frame, text="选择", command=self._select_baseline, bootstyle=INFO).pack(side=RIGHT)

        self.bl_merge_frame = ttk.Frame(bl_frame)
        self.bl_merge_frame.pack(fill=X, pady=5)
        ttk.Radiobutton(self.bl_merge_frame, text="合并所有航点", variable=self.baseline_merge,
                         value=True).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(self.bl_merge_frame, text="逐个文件匹配", variable=self.baseline_merge,
                         value=False).pack(side=LEFT)
        self.bl_merge_frame.pack_forget()

        # 源文件设置
        src_frame = ttk.LabelFrame(tab, text="源文件设置", padding=10)
        src_frame.pack(fill=X, pady=(0, 10))

        src_type_frame = ttk.Frame(src_frame)
        src_type_frame.pack(fill=X, pady=(0, 5))
        ttk.Radiobutton(src_type_frame, text="单文件", variable=self.source_is_dir,
                         value=False).pack(side=LEFT, padx=(0, 15))
        ttk.Radiobutton(src_type_frame, text="文件夹", variable=self.source_is_dir,
                         value=True).pack(side=LEFT)

        src_path_frame = ttk.Frame(src_frame)
        src_path_frame.pack(fill=X, pady=5)
        ttk.Entry(src_path_frame, textvariable=self.source_path, width=60).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(src_path_frame, text="选择", command=self._select_source, bootstyle=INFO).pack(side=RIGHT)

        # 输出目录
        out_frame = ttk.LabelFrame(tab, text="输出目录", padding=10)
        out_frame.pack(fill=X)

        out_path_frame = ttk.Frame(out_frame)
        out_path_frame.pack(fill=X)
        ttk.Entry(out_path_frame, textvariable=self.output_dir, width=60).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(out_path_frame, text="选择", command=self._select_output_dir, bootstyle=INFO).pack(side=RIGHT)

    def _create_match_settings_tab(self):
        """创建匹配设置标签页"""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="  2. 匹配设置  ")

        settings_frame = ttk.LabelFrame(tab, text="匹配参数", padding=15)
        settings_frame.pack(fill=X, pady=10)

        ttk.Label(settings_frame, text="匹配距离(米):").grid(row=0, column=0, sticky=W, pady=10)
        ttk.Entry(settings_frame, textvariable=self.threshold, width=15).grid(row=0, column=1, sticky=W, padx=10, pady=10)

        ttk.Label(settings_frame, text="航点前缀(可选):").grid(row=1, column=0, sticky=W, pady=10)
        ttk.Entry(settings_frame, textvariable=self.prefix, width=20).grid(row=1, column=1, sticky=W, padx=10, pady=10)

        tip_frame = ttk.LabelFrame(tab, text="说明", padding=10)
        tip_frame.pack(fill=X, pady=10)
        ttk.Label(tip_frame, text="• 匹配距离：源航点与基线航点的距离小于此值时视为匹配成功\n"
                                   "• 航点前缀：匹配成功后，为源航点名称添加的前缀",
                  justify=LEFT).pack(anchor=W)

    def _create_delete_options_tab(self):
        """创建删除选项标签页"""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="  3. 删除选项  ")

        opt_frame = ttk.LabelFrame(tab, text="删除选项（可多选）", padding=15)
        opt_frame.pack(fill=X, pady=10)

        ttk.Checkbutton(opt_frame, text="删除未匹配的基线航点",
                         variable=self.delete_unmatched_baseline).pack(anchor=W, pady=5)
        ttk.Checkbutton(opt_frame, text="删除未匹配的源航点",
                         variable=self.delete_unmatched_source).pack(anchor=W, pady=5)
        ttk.Checkbutton(opt_frame, text="删除匹配的基线航点",
                         variable=self.delete_matched_baseline).pack(anchor=W, pady=5)
        ttk.Checkbutton(opt_frame, text="删除匹配的源航点",
                         variable=self.delete_matched_source).pack(anchor=W, pady=5)

        tip_frame = ttk.LabelFrame(tab, text="说明", padding=10)
        tip_frame.pack(fill=X, pady=10)
        ttk.Label(tip_frame, text="• 删除未匹配的基线航点：从基线文件中移除没有被源航点匹配到的航点\n"
                                   "• 删除未匹配的源航点：从源文件中移除没有匹配到基线的航点\n"
                                   "• 删除匹配的基线航点：从基线文件中移除被匹配到的航点\n"
                                   "• 删除匹配的源航点：从源文件中移除匹配到基线的航点\n"
                                   "• 基线文件修改后保存到输出目录，不修改原文件",
                  justify=LEFT).pack(anchor=W)

    def _create_preview_tab(self):
        """创建预览与执行标签页"""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="  4. 预览与执行  ")

        # 预览控制
        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill=X, pady=(0, 10))

        ttk.Button(ctrl_frame, text="刷新预览", command=self._refresh_preview, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(ctrl_frame, text="扫描所有文件", command=self._scan_all_files, bootstyle=WARNING).pack(side=LEFT, padx=5)

        # 全局统计
        self.global_stats = ttk.Label(ctrl_frame, text="未扫描", foreground="darkgreen")
        self.global_stats.pack(side=RIGHT, padx=5)

        # 预览区域
        preview_frame = ttk.LabelFrame(tab, text="文件预览", padding=10)
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 文件选择
        file_ctrl = ttk.Frame(preview_frame)
        file_ctrl.pack(fill=X, pady=(0, 5))

        self.file_label = ttk.Label(file_ctrl, text="源文件:")
        self.file_label.pack(side=LEFT, padx=(0, 5))
        self.file_combo = ttk.Combobox(file_ctrl, state="readonly", width=40)
        self.file_combo.pack(side=LEFT, padx=(0, 10))
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)

        self.preview_stats = ttk.Label(file_ctrl, text="", foreground="blue")
        self.preview_stats.pack(side=RIGHT, padx=5)

        # 预览树形列表
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        columns = ("source_name", "lat", "lon", "matched_name", "distance", "status")
        self.preview_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)

        self.preview_tree.heading("source_name", text="源航点名称")
        self.preview_tree.heading("lat", text="纬度")
        self.preview_tree.heading("lon", text="经度")
        self.preview_tree.heading("matched_name", text="匹配基线航点")
        self.preview_tree.heading("distance", text="距离(米)")
        self.preview_tree.heading("status", text="状态")

        self.preview_tree.column("source_name", width=120)
        self.preview_tree.column("lat", width=90)
        self.preview_tree.column("lon", width=90)
        self.preview_tree.column("matched_name", width=120)
        self.preview_tree.column("distance", width=80)
        self.preview_tree.column("status", width=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        self.preview_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 开始处理按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=X, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="开始处理", command=self._start_process, bootstyle=SUCCESS)
        self.start_btn.pack(side=LEFT, padx=5)

    def _on_baseline_type_change(self):
        """基线类型切换"""
        if self.baseline_is_dir.get():
            self.bl_merge_frame.pack(fill=X, pady=5)
        else:
            self.bl_merge_frame.pack_forget()

    def _select_baseline(self):
        """选择基线文件或目录"""
        if self.baseline_is_dir.get():
            path = filedialog.askdirectory()
        else:
            filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
            path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.baseline_path.set(path)
            self.baseline_waypoints = None

    def _select_source(self):
        """选择源文件或目录"""
        if self.source_is_dir.get():
            path = filedialog.askdirectory()
        else:
            filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
            path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.source_path.set(path)

    def _select_output_dir(self):
        """选择输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _prev_tab(self):
        """上一步"""
        current = self.notebook.index(self.notebook.select())
        if current > 0:
            self.notebook.select(current - 1)

    def _next_tab(self):
        """下一步"""
        current = self.notebook.index(self.notebook.select())
        if current < len(self.notebook.tabs()) - 1:
            self.notebook.select(current + 1)

    def _load_baseline(self):
        """加载基线航点"""
        if self.baseline_waypoints is not None:
            return True
        baseline_path = self.baseline_path.get()
        if not baseline_path:
            messagebox.showwarning("提示", "请先选择基线GPX文件")
            return False
        try:
            if self.baseline_is_dir.get():
                baseline_dict = BatchMatcher.load_baseline_from_dir(
                    baseline_path, self.baseline_merge.get()
                )
                self.baseline_waypoints = list(baseline_dict.values())[0]
            else:
                self.baseline_waypoints = BatchMatcher.load_baseline(baseline_path)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"加载基线文件失败:\n{e}")
            return False

    def _get_source_files(self):
        """获取源文件列表"""
        source_path = self.source_path.get()
        if not source_path:
            return []
        return BatchMatcher.get_source_files(source_path, self.source_is_dir.get())

    def _refresh_preview(self):
        """刷新文件列表"""
        if not self._load_baseline():
            return
        source_files = self._get_source_files()
        if not source_files:
            messagebox.showwarning("提示", "请先选择源文件")
            return

        is_baseline = self._is_baseline_preview()
        if is_baseline:
            # 基线预览模式：显示基线文件列表
            baseline_path = self.baseline_path.get()
            if self.baseline_is_dir.get():
                filenames = [f for f in os.listdir(baseline_path) if f.lower().endswith('.gpx')]
            else:
                filenames = [os.path.basename(baseline_path)]
        else:
            # 源文件预览模式：显示源文件列表
            filenames = [os.path.basename(f) for f in source_files]

        self.file_combo['values'] = filenames
        if filenames:
            self.file_combo.current(0)
            self._preview_current_file()

    def _on_file_selected(self, event=None):
        """文件选择事件"""
        self._preview_current_file()

    def _get_delete_options(self):
        """从UI获取当前删除选项"""
        return DeleteOptions(
            delete_unmatched_baseline=self.delete_unmatched_baseline.get(),
            delete_unmatched_source=self.delete_unmatched_source.get(),
            delete_matched_baseline=self.delete_matched_baseline.get(),
            delete_matched_source=self.delete_matched_source.get()
        )

    def _is_baseline_preview(self):
        """判断当前是否应该预览基线文件"""
        options = self._get_delete_options()
        return options.delete_matched_baseline or options.delete_unmatched_baseline

    def _preview_current_file(self):
        """预览当前选中的文件"""
        if not self.baseline_waypoints:
            return

        filename = self.file_combo.get()
        if not filename:
            return

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值")
            return

        options = self._get_delete_options()
        is_baseline = self._is_baseline_preview()

        if is_baseline:
            # 预览基线文件
            baseline_path = self.baseline_path.get()
            if self.baseline_is_dir.get():
                baseline_file = os.path.join(baseline_path, filename)
            else:
                baseline_file = baseline_path
            source_files = self._get_source_files()
            preview = BatchMatcher.preview_baseline_file(
                baseline_file, self.baseline_waypoints,
                source_files, threshold, options
            )
            # 更新标签
            self.file_label.config(text="基线文件:")
            self.preview_tree.heading("source_name", text="基线航点名称")
            self.preview_tree.heading("matched_name", text="匹配源航点")
        else:
            # 预览源文件
            source_path = self.source_path.get()
            if self.source_is_dir.get():
                source_path = os.path.join(source_path, filename)
            preview = BatchMatcher.preview_file(source_path, self.baseline_waypoints, threshold)
            # 更新标签
            self.file_label.config(text="源文件:")
            self.preview_tree.heading("source_name", text="源航点名称")
            self.preview_tree.heading("matched_name", text="匹配基线航点")

        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        for wp in preview.waypoints:
            tags = ("keep",) if wp.status == "保留" else ("remove",)
            self.preview_tree.insert("", END, values=(
                wp.source_name,
                f"{wp.source_lat:.6f}",
                f"{wp.source_lon:.6f}",
                wp.matched_name,
                wp.distance,
                wp.status
            ), tags=tags)

        self.preview_tree.tag_configure("keep", background="#d4edda")
        self.preview_tree.tag_configure("remove", background="#f8d7da")

        self.preview_stats.config(
            text=f"保留 {preview.matched} | 删除 {preview.removed} | 总计 {preview.matched + preview.removed}"
        )

    def _scan_all_files(self):
        """扫描所有源文件"""
        if not self._load_baseline():
            return

        source_files = self._get_source_files()
        if not source_files:
            messagebox.showwarning("提示", "请先选择源文件")
            return

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值")
            return

        self.global_stats.config(text="扫描中...", foreground="orange")
        self.update()

        total_files = len(source_files)
        total_waypoints = 0
        total_matched = 0
        total_removed = 0

        for src_file in source_files:
            preview = BatchMatcher.preview_file(src_file, self.baseline_waypoints, threshold)
            total_waypoints += preview.matched + preview.removed
            total_matched += preview.matched
            total_removed += preview.removed

        self.global_stats.config(
            text=f"文件: {total_files} | 航点: {total_waypoints} | 匹配: {total_matched} | 删除: {total_removed}",
            foreground="darkgreen"
        )

    def _validate_inputs(self) -> bool:
        """验证输入"""
        if not self.baseline_path.get():
            messagebox.showwarning("提示", "请选择基线GPX文件")
            return False
        if not self.source_path.get():
            messagebox.showwarning("提示", "请选择源文件")
            return False
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请选择输出目录")
            return False
        try:
            threshold = float(self.threshold.get())
            if threshold <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的距离阈值（正数）")
            return False
        return True

    def _start_process(self):
        """开始处理"""
        if self.is_processing:
            return
        if not self._validate_inputs():
            return

        self.is_processing = True
        self.start_btn.config(state=DISABLED)
        self.progress_var.set(0)

        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()

    def _process_thread(self):
        """处理线程"""
        try:
            threshold = float(self.threshold.get())
            prefix = self.prefix.get()

            options = DeleteOptions(
                delete_unmatched_baseline=self.delete_unmatched_baseline.get(),
                delete_unmatched_source=self.delete_unmatched_source.get(),
                delete_matched_baseline=self.delete_matched_baseline.get(),
                delete_matched_source=self.delete_matched_source.get()
            )

            def update_progress(filename, current, total):
                progress = (current / total) * 100
                self.after(0, self._update_progress_ui, filename, progress, current, total)

            result = BatchMatcher.batch_process_with_options(
                self.baseline_path.get(),
                self.baseline_is_dir.get(),
                self.source_path.get(),
                self.source_is_dir.get(),
                self.output_dir.get(),
                threshold,
                prefix,
                options,
                callback=update_progress,
                baseline_merge=self.baseline_merge.get()
            )

            self.after(0, self._show_result, result)

        except Exception as e:
            self.after(0, self._show_error, str(e))

        finally:
            self.after(0, self._process_complete)

    def _update_progress_ui(self, filename: str, progress: float, current: int, total: int):
        """更新进度UI"""
        self.progress_var.set(progress)
        self.progress_label.config(text=f"处理中: {filename} ({current}/{total})")

    def _show_result(self, result):
        """显示处理结果"""
        msg = (
            f"处理完成!\n\n"
            f"处理文件数: {result.processed_files}\n"
            f"失败文件数: {result.failed_files}\n"
            f"匹配航点数: {result.total_matched}\n"
            f"删除航点数: {result.total_removed}"
        )
        messagebox.showinfo("处理结果", msg)
        self.progress_label.config(text="处理完成")

    def _show_error(self, error_msg):
        """显示错误"""
        messagebox.showerror("错误", f"处理过程中发生错误:\n{error_msg}")
        self.progress_label.config(text="处理失败")

    def _process_complete(self):
        """处理完成"""
        self.is_processing = False
        self.start_btn.config(state=NORMAL)

    def _on_close(self):
        """关闭对话框"""
        if self.is_processing:
            if messagebox.askyesno("确认", "正在处理中，确定要关闭吗？"):
                self.destroy()
        else:
            self.destroy()
