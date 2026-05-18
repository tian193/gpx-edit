# -*- coding: utf-8 -*-
"""
三方数据一致性校验对话框
功能: 对比分配航点、GPS实际航点、手写样品编号三者是否一致
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap.constants import *
import threading

from ..core.verifier import (
    Verifier, MatchStatus,
    VerificationResult, BatchVerificationResult
)


class VerificationDialog(tk.Toplevel):
    """三方数据一致性校验对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("三方数据一致性校验")
        self.transient(parent)
        self.grab_set()
        self.geometry("1000x750")
        self.resizable(True, True)

        self.assigned_path = tk.StringVar()
        self.gps_path = tk.StringVar()
        self.sample_path = tk.StringVar()
        self.base_dir = tk.StringVar()
        self.threshold = tk.StringVar(value="200")

        self.single_result = None
        self.batch_result = None

        self._create_widgets()
        self._center_window()

    def _center_window(self):
        """居中显示窗口"""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _create_widgets(self):
        """创建界面组件"""
        # 顶部标签页
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 单次校验页
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="单次校验")
        self._create_single_tab(self.single_frame)

        # 批量校验页
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_frame, text="批量校验")
        self._create_batch_tab(self.batch_frame)

    def _create_single_tab(self, parent):
        """创建单次校验标签页"""
        # 文件选择区域
        file_frame = ttk.LabelFrame(parent, text="文件设置", padding=10)
        file_frame.pack(fill=X, padx=5, pady=5)

        # 分配航点GPX
        row1 = ttk.Frame(file_frame)
        row1.pack(fill=X, pady=2)
        ttk.Label(row1, text="分配航点GPX:", width=14).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.assigned_path).pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(row1, text="选择", command=lambda: self._select_file(
            self.assigned_path, "GPX文件", [("GPX文件", "*.gpx")])).pack(side=LEFT)

        # GPS实际GPX
        row2 = ttk.Frame(file_frame)
        row2.pack(fill=X, pady=2)
        ttk.Label(row2, text="GPS实际GPX:", width=14).pack(side=LEFT)
        ttk.Entry(row2, textvariable=self.gps_path).pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(row2, text="选择", command=lambda: self._select_file(
            self.gps_path, "GPX文件", [("GPX文件", "*.gpx")])).pack(side=LEFT)

        # 样品编号文件
        row3 = ttk.Frame(file_frame)
        row3.pack(fill=X, pady=2)
        ttk.Label(row3, text="样品编号文件:", width=14).pack(side=LEFT)
        ttk.Entry(row3, textvariable=self.sample_path).pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(row3, text="选择", command=lambda: self._select_file(
            self.sample_path, "样品文件", [("Excel/CSV文件", "*.xlsx *.csv")])).pack(side=LEFT)

        # 距离阈值
        row4 = ttk.Frame(file_frame)
        row4.pack(fill=X, pady=2)
        ttk.Label(row4, text="距离阈值(米):", width=14).pack(side=LEFT)
        ttk.Entry(row4, textvariable=self.threshold, width=10).pack(side=LEFT, padx=5)

        # 按钮区域
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=X, padx=5, pady=5)
        ttk.Button(btn_frame, text="开始校验", command=self._run_single_verify,
                   bootstyle="primary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="导出Excel", command=self._export_single_excel,
                   bootstyle="success").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=RIGHT, padx=5)

        # 结果表格
        result_frame = ttk.LabelFrame(parent, text="校验结果", padding=5)
        result_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        columns = ("name", "assigned", "gps", "sample", "distance", "status")
        self.single_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)

        self.single_tree.heading("name", text="航点名称")
        self.single_tree.heading("assigned", text="分配航点")
        self.single_tree.heading("gps", text="GPS航点")
        self.single_tree.heading("sample", text="样品编号")
        self.single_tree.heading("distance", text="距离(米)")
        self.single_tree.heading("status", text="状态")

        self.single_tree.column("name", width=120)
        self.single_tree.column("assigned", width=180)
        self.single_tree.column("gps", width=180)
        self.single_tree.column("sample", width=100)
        self.single_tree.column("distance", width=80)
        self.single_tree.column("status", width=100)

        scrollbar = ttk.Scrollbar(result_frame, orient=VERTICAL, command=self.single_tree.yview)
        self.single_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.single_tree.pack(fill=BOTH, expand=True)

        # 配置颜色标签
        self.single_tree.tag_configure("matched", background="#C6EFCE")
        self.single_tree.tag_configure("missing_gps", background="#FFC7CE")
        self.single_tree.tag_configure("extra_gps", background="#BDD7EE")
        self.single_tree.tag_configure("missing_sample", background="#FFEB9C")
        self.single_tree.tag_configure("extra_sample", background="#FFC7CE")
        self.single_tree.tag_configure("distance_warning", background="#FFEB9C")

        # 统计栏
        self.single_stats = ttk.Label(parent, text="统计: -")
        self.single_stats.pack(fill=X, padx=10, pady=5)

    def _create_batch_tab(self, parent):
        """创建批量校验标签页"""
        # 文件选择区域
        file_frame = ttk.LabelFrame(parent, text="目录设置", padding=10)
        file_frame.pack(fill=X, padx=5, pady=5)

        row1 = ttk.Frame(file_frame)
        row1.pack(fill=X, pady=2)
        ttk.Label(row1, text="根目录:", width=14).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.base_dir).pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(row1, text="选择", command=self._select_base_dir).pack(side=LEFT)

        row2 = ttk.Frame(file_frame)
        row2.pack(fill=X, pady=2)
        ttk.Label(row2, text="距离阈值(米):", width=14).pack(side=LEFT)
        ttk.Entry(row2, textvariable=self.threshold, width=10).pack(side=LEFT, padx=5)

        # 按钮区域
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=X, padx=5, pady=5)
        ttk.Button(btn_frame, text="扫描目录", command=self._scan_directory,
                   bootstyle="info").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="开始批量校验", command=self._run_batch_verify,
                   bootstyle="primary").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="导出Excel", command=self._export_batch_excel,
                   bootstyle="success").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=RIGHT, padx=5)

        # 分组列表
        result_frame = ttk.LabelFrame(parent, text="分组列表", padding=5)
        result_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        columns = ("label", "assigned", "gps", "sample", "matched", "issues")
        self.batch_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)

        self.batch_tree.heading("label", text="分组")
        self.batch_tree.heading("assigned", text="分配航点数")
        self.batch_tree.heading("gps", text="GPS航点数")
        self.batch_tree.heading("sample", text="样品数")
        self.batch_tree.heading("matched", text="一致数")
        self.batch_tree.heading("issues", text="问题数")

        self.batch_tree.column("label", width=150)
        self.batch_tree.column("assigned", width=100)
        self.batch_tree.column("gps", width=100)
        self.batch_tree.column("sample", width=100)
        self.batch_tree.column("matched", width=100)
        self.batch_tree.column("issues", width=100)

        scrollbar = ttk.Scrollbar(result_frame, orient=VERTICAL, command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.batch_tree.pack(fill=BOTH, expand=True)

        self.batch_tree.bind("<Double-1>", self._on_batch_double_click)

        # 统计栏
        self.batch_stats = ttk.Label(parent, text="统计: -")
        self.batch_stats.pack(fill=X, padx=10, pady=5)

        # 进度条
        self.progress = ttk.Progressbar(parent, mode='determinate')
        self.progress.pack(fill=X, padx=10, pady=5)

    def _select_file(self, var, title, filetypes):
        """选择文件"""
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            var.set(path)

    def _select_base_dir(self):
        """选择根目录"""
        path = filedialog.askdirectory(title="选择根目录")
        if path:
            self.base_dir.set(path)

    def _get_status_tag(self, status: MatchStatus) -> str:
        """获取状态对应的标签名"""
        tag_map = {
            MatchStatus.MATCHED: "matched",
            MatchStatus.MISSING_GPS: "missing_gps",
            MatchStatus.EXTRA_GPS: "extra_gps",
            MatchStatus.MISSING_SAMPLE: "missing_sample",
            MatchStatus.EXTRA_SAMPLE: "extra_sample",
            MatchStatus.DISTANCE_WARNING: "distance_warning"
        }
        return tag_map.get(status, "")

    def _run_single_verify(self):
        """执行单次校验"""
        if not self.assigned_path.get() or not self.gps_path.get():
            messagebox.showwarning("提示", "请选择分配航点GPX和GPS实际GPX文件")
            return

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "距离阈值必须是数字")
            return

        try:
            assigned = Verifier.load_gpx_waypoints(self.assigned_path.get())
            gps = Verifier.load_gpx_waypoints(self.gps_path.get())
            samples = []

            if self.sample_path.get():
                samples = Verifier.load_samples(self.sample_path.get())

            items = Verifier.verify_single(assigned, gps, samples, threshold)

            self.single_result = VerificationResult(
                group_label="单次校验",
                assigned_file=self.assigned_path.get(),
                gps_file=self.gps_path.get(),
                sample_file=self.sample_path.get(),
                items=items
            )

            self._display_single_result()

        except Exception as e:
            messagebox.showerror("错误", f"校验失败: {str(e)}")

    def _display_single_result(self):
        """显示单次校验结果"""
        # 清空表格
        for item in self.single_tree.get_children():
            self.single_tree.delete(item)

        if not self.single_result:
            return

        for item in self.single_result.items:
            # 分配坐标
            if item.assigned and item.assigned.latitude:
                assigned_text = f"{item.assigned.latitude:.6f}, {item.assigned.longitude:.6f}"
            else:
                assigned_text = "(无)"

            # GPS坐标
            if item.gps_actual and item.gps_actual.latitude:
                gps_text = f"{item.gps_actual.latitude:.6f}, {item.gps_actual.longitude:.6f}"
            else:
                gps_text = "(无)"

            # 样品编号
            sample_text = item.sample.sample_id if item.sample else "(无)"

            # 距离
            distance_text = f"{item.distance:.1f}" if item.distance is not None else "-"

            # 状态
            status_text = item.status.value

            # 标签
            tag = self._get_status_tag(item.status)

            self.single_tree.insert("", END, values=(
                item.waypoint_name, assigned_text, gps_text,
                sample_text, distance_text, status_text
            ), tags=(tag,))

        # 更新统计
        r = self.single_result
        stats_text = f"统计: 总计 {len(r.items)} | 一致 {r.total_matched} | 问题 {r.total_issues}"
        self.single_stats.config(text=stats_text)

    def _export_single_excel(self):
        """导出单次校验结果到Excel"""
        if not self.single_result:
            messagebox.showwarning("提示", "请先执行校验")
            return

        path = filedialog.asksaveasfilename(
            title="导出Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )
        if not path:
            return

        try:
            Verifier.export_to_excel([self.single_result], path)
            messagebox.showinfo("成功", f"已导出到: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _scan_directory(self):
        """扫描目录"""
        if not self.base_dir.get():
            messagebox.showwarning("提示", "请选择根目录")
            return

        try:
            groups = Verifier.scan_directory(self.base_dir.get())

            # 清空表格
            for item in self.batch_tree.get_children():
                self.batch_tree.delete(item)

            if not groups:
                messagebox.showinfo("提示", "未找到有效的分组目录")
                return

            for group in groups:
                self.batch_tree.insert("", END, values=(
                    group['label'], "-", "-", "-", "-", "-"
                ))

            messagebox.showinfo("扫描完成", f"找到 {len(groups)} 个分组")

        except Exception as e:
            messagebox.showerror("错误", f"扫描失败: {str(e)}")

    def _run_batch_verify(self):
        """执行批量校验"""
        if not self.base_dir.get():
            messagebox.showwarning("提示", "请选择根目录")
            return

        try:
            threshold = float(self.threshold.get())
        except ValueError:
            messagebox.showwarning("提示", "距离阈值必须是数字")
            return

        def progress_callback(label, current, total):
            self.after(0, lambda: self.progress.configure(
                value=current / total * 100
            ))
            self.after(0, lambda: self.batch_stats.config(
                text=f"正在处理: {label} ({current}/{total})"
            ))

        def verify_thread():
            try:
                result = Verifier.verify_batch(
                    self.base_dir.get(), threshold, progress_callback
                )
                self.after(0, lambda: self._display_batch_result(result))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"批量校验失败: {str(e)}"))

        # 清空表格
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)

        self.progress.configure(value=0)
        threading.Thread(target=verify_thread, daemon=True).start()

    def _display_batch_result(self, result: BatchVerificationResult):
        """显示批量校验结果"""
        self.batch_result = result

        # 清空表格
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)

        total_items = 0
        total_matched = 0
        total_issues = 0

        for group in result.group_results:
            self.batch_tree.insert("", END, values=(
                group.group_label,
                group.total_assigned,
                group.total_gps,
                group.total_samples,
                group.total_matched,
                group.total_issues
            ))

            total_items += len(group.items)
            total_matched += group.total_matched
            total_issues += group.total_issues

        # 显示错误
        if result.errors:
            for err in result.errors:
                messagebox.showwarning("警告", err)

        # 更新统计
        stats_text = f"统计: 共 {len(result.group_results)} 组 | 总计 {total_items} 项 | 一致 {total_matched} | 问题 {total_issues}"
        self.batch_stats.config(text=stats_text)
        self.progress.configure(value=100)

    def _on_batch_double_click(self, event):
        """双击分组行显示详细结果"""
        selection = self.batch_tree.selection()
        if not selection or not self.batch_result:
            return

        item = self.batch_tree.item(selection[0])
        group_label = item['values'][0]

        # 查找对应的分组结果
        for group in self.batch_result.group_results:
            if group.group_label == group_label:
                self._show_detail_dialog(group)
                break

    def _show_detail_dialog(self, result: VerificationResult):
        """显示详细结果对话框"""
        detail = tk.Toplevel(self)
        detail.title(f"详细结果 - {result.group_label}")
        detail.geometry("900x500")
        detail.transient(self)

        # 结果表格
        columns = ("name", "assigned", "gps", "sample", "distance", "status", "notes")
        tree = ttk.Treeview(detail, columns=columns, show="headings", height=20)

        tree.heading("name", text="航点名称")
        tree.heading("assigned", text="分配航点")
        tree.heading("gps", text="GPS航点")
        tree.heading("sample", text="样品编号")
        tree.heading("distance", text="距离(米)")
        tree.heading("status", text="状态")
        tree.heading("notes", text="备注")

        tree.column("name", width=100)
        tree.column("assigned", width=160)
        tree.column("gps", width=160)
        tree.column("sample", width=80)
        tree.column("distance", width=70)
        tree.column("status", width=90)
        tree.column("notes", width=200)

        scrollbar = ttk.Scrollbar(detail, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 配置颜色标签
        tree.tag_configure("matched", background="#C6EFCE")
        tree.tag_configure("missing_gps", background="#FFC7CE")
        tree.tag_configure("extra_gps", background="#BDD7EE")
        tree.tag_configure("missing_sample", background="#FFEB9C")
        tree.tag_configure("extra_sample", background="#FFC7CE")
        tree.tag_configure("distance_warning", background="#FFEB9C")

        # 填充数据
        for item in result.items:
            assigned_text = f"{item.assigned.latitude:.6f}, {item.assigned.longitude:.6f}" \
                if item.assigned and item.assigned.latitude else "(无)"
            gps_text = f"{item.gps_actual.latitude:.6f}, {item.gps_actual.longitude:.6f}" \
                if item.gps_actual and item.gps_actual.latitude else "(无)"
            sample_text = item.sample.sample_id if item.sample else "(无)"
            distance_text = f"{item.distance:.1f}" if item.distance is not None else "-"

            tag = self._get_status_tag(item.status)

            tree.insert("", END, values=(
                item.waypoint_name, assigned_text, gps_text,
                sample_text, distance_text, item.status.value, item.notes
            ), tags=(tag,))

    def _export_batch_excel(self):
        """导出批量校验结果到Excel"""
        if not self.batch_result:
            messagebox.showwarning("提示", "请先执行批量校验")
            return

        path = filedialog.asksaveasfilename(
            title="导出Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )
        if not path:
            return

        try:
            Verifier.export_to_excel(self.batch_result.group_results, path)
            messagebox.showinfo("成功", f"已导出到: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
