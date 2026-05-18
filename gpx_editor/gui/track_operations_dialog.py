# -*- coding: utf-8 -*-
"""
航迹操作对话框
功能: 航迹简化、合并、分割
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from ..core.track import TrackManager


class TrackOperationsDialog:
    """航迹操作对话框"""

    def __init__(self, parent):
        self.parent = parent
        self.gpx_handler = parent.gpx_handler
        self.result = None  # 操作结果，用于通知主窗口刷新

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("航迹操作")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry("500x450")
        self.dialog.resizable(False, False)

        self._create_widgets()
        self._refresh_track_lists()

        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=BOTH, expand=True)

        # 简化标签页
        simplify_frame = ttk.Frame(notebook, padding=10)
        notebook.add(simplify_frame, text="简化航迹")
        self._create_simplify_tab(simplify_frame)

        # 合并标签页
        merge_frame = ttk.Frame(notebook, padding=10)
        notebook.add(merge_frame, text="合并航迹")
        self._create_merge_tab(merge_frame)

        # 分割标签页
        split_frame = ttk.Frame(notebook, padding=10)
        notebook.add(split_frame, text="分割航迹")
        self._create_split_tab(split_frame)

    def _create_simplify_tab(self, parent):
        """简化航迹标签页"""
        ttk.Label(parent, text="选择航迹:").pack(anchor=W)
        self.simplify_combo = ttk.Combobox(parent, state="readonly", width=40)
        self.simplify_combo.pack(fill=X, pady=(0, 10))

        ttk.Label(parent, text="容差(米):").pack(anchor=W)
        self.epsilon_var = tk.StringVar(value="10")
        ttk.Entry(parent, textvariable=self.epsilon_var, width=20).pack(anchor=W, pady=(0, 10))

        ttk.Label(parent, text="较小的值保留更多细节，较大的值简化更多", foreground="gray").pack(anchor=W)

        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=X, pady=10)
        self.simplify_info = ttk.Label(info_frame, text="")
        self.simplify_info.pack(anchor=W)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=X, pady=10)
        ttk.Button(btn_frame, text="预览", command=self._preview_simplify).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="应用", command=self._apply_simplify, bootstyle=PRIMARY).pack(side=LEFT, padx=5)

    def _create_merge_tab(self, parent):
        """合并航迹标签页"""
        ttk.Label(parent, text="选择要合并的航迹(可多选):").pack(anchor=W)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.merge_listbox = tk.Listbox(list_frame, selectmode=EXTENDED,
                                         yscrollcommand=scrollbar.set, height=6)
        scrollbar.config(command=self.merge_listbox.yview)
        self.merge_listbox.pack(fill=BOTH, expand=True)

        ttk.Label(parent, text="合并后名称:").pack(anchor=W)
        self.merge_name_var = tk.StringVar(value="合并航迹")
        ttk.Entry(parent, textvariable=self.merge_name_var, width=30).pack(anchor=W, pady=(0, 10))

        ttk.Button(parent, text="合并", command=self._apply_merge, bootstyle=PRIMARY).pack(anchor=W)

    def _create_split_tab(self, parent):
        """分割航迹标签页"""
        ttk.Label(parent, text="选择航迹:").pack(anchor=W)
        self.split_combo = ttk.Combobox(parent, state="readonly", width=40)
        self.split_combo.pack(fill=X, pady=(0, 10))
        self.split_combo.bind("<<ComboboxSelected>>", self._on_split_track_selected)

        ttk.Label(parent, text="分割点索引:").pack(anchor=W)
        self.split_index_var = tk.StringVar(value="0")
        ttk.Entry(parent, textvariable=self.split_index_var, width=20).pack(anchor=W, pady=(0, 5))

        self.split_info = ttk.Label(parent, text="", foreground="gray")
        self.split_info.pack(anchor=W)

        ttk.Label(parent, text="将在该点处分割为两条航迹", foreground="gray").pack(anchor=W, pady=(10, 0))

        ttk.Button(parent, text="分割", command=self._apply_split, bootstyle=PRIMARY).pack(anchor=W, pady=10)

    def _refresh_track_lists(self):
        """刷新航迹列表"""
        tracks = self.gpx_handler.get_tracks()
        track_names = []
        for i, t in enumerate(tracks):
            name = t.name or f"航迹{i+1}"
            pts = TrackManager.get_track_total_points(t) if hasattr(TrackManager, 'get_track_total_points') else sum(len(seg.points) for seg in t.segments)
            track_names.append(f"{name} ({pts}点)")

        self.simplify_combo['values'] = track_names
        self.split_combo['values'] = track_names

        self.merge_listbox.delete(0, END)
        for name in track_names:
            self.merge_listbox.insert(END, name)

    def _get_selected_track_index(self, combo):
        """从combobox获取选中的航迹索引"""
        sel = combo.current()
        if sel < 0:
            messagebox.showwarning("提示", "请先选择一条航迹")
            return None
        return sel

    def _preview_simplify(self):
        """预览简化结果"""
        idx = self._get_selected_track_index(self.simplify_combo)
        if idx is None:
            return

        try:
            epsilon = float(self.epsilon_var.get())
            if epsilon <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "容差必须是正数")
            return

        tracks = self.gpx_handler.get_tracks()
        track = tracks[idx]
        before = sum(len(seg.points) for seg in track.segments)

        # 模拟简化计算点数
        after = 0
        for seg in track.segments:
            if len(seg.points) <= 2:
                after += len(seg.points)
            else:
                simplified = TrackManager.simplify_douglas_peucker(seg.points, epsilon)
                after += len(simplified)

        self.simplify_info.config(text=f"简化前: {before}点 → 简化后: {after}点 (减少 {before - after} 点, {100*(before-after)/before:.1f}%)" if before > 0 else "无数据")

    def _apply_simplify(self):
        """应用简化"""
        idx = self._get_selected_track_index(self.simplify_combo)
        if idx is None:
            return

        try:
            epsilon = float(self.epsilon_var.get())
            if epsilon <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "容差必须是正数")
            return

        tracks = self.gpx_handler.get_tracks()
        track = tracks[idx]
        before = sum(len(seg.points) for seg in track.segments)

        TrackManager.simplify_gpx_track(track, epsilon)

        after = sum(len(seg.points) for seg in track.segments)
        self.simplify_info.config(text=f"简化完成: {before}点 → {after}点")
        self.result = "simplify"
        messagebox.showinfo("完成", f"航迹已简化: {before}点 → {after}点")

    def _apply_merge(self):
        """应用合并"""
        selected = self.merge_listbox.curselection()
        if len(selected) < 2:
            messagebox.showwarning("提示", "请至少选择两条航迹")
            return

        name = self.merge_name_var.get().strip() or "合并航迹"
        tracks = self.gpx_handler.get_tracks()
        tracks_to_merge = [tracks[i] for i in selected]

        merged = TrackManager.merge_gpx_tracks(tracks_to_merge, name)

        # 删除原航迹（从后往前删）
        for i in sorted(selected, reverse=True):
            self.gpx_handler.remove_track(i)

        # 添加合并后的航迹
        self.gpx_handler.gpx.tracks.append(merged)

        self.result = "merge"
        self._refresh_track_lists()
        messagebox.showinfo("完成", f"已合并 {len(selected)} 条航迹为 \"{name}\"")

    def _on_split_track_selected(self, event):
        """分割标签页选择航迹"""
        idx = self._get_selected_track_index(self.split_combo)
        if idx is not None:
            tracks = self.gpx_handler.get_tracks()
            track = tracks[idx]
            total = sum(len(seg.points) for seg in track.segments)
            self.split_info.config(text=f"总点数: {total}，有效索引: 0 ~ {total - 2}")

    def _apply_split(self):
        """应用分割"""
        idx = self._get_selected_track_index(self.split_combo)
        if idx is None:
            return

        tracks = self.gpx_handler.get_tracks()
        track = tracks[idx]

        try:
            point_index = int(self.split_index_var.get())
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的点索引")
            return

        # 找到对应的段和段内索引
        global_idx = point_index
        seg_idx = -1
        local_idx = -1
        for i, seg in enumerate(track.segments):
            if global_idx < len(seg.points):
                seg_idx = i
                local_idx = global_idx
                break
            global_idx -= len(seg.points)

        if seg_idx < 0:
            messagebox.showwarning("提示", "点索引超出范围")
            return

        track1, track2 = TrackManager.split_gpx_track(track, seg_idx, local_idx)
        if track2 is None:
            messagebox.showwarning("提示", "分割失败")
            return

        # 替换原航迹
        self.gpx_handler.gpx.tracks.pop(idx)
        self.gpx_handler.gpx.tracks.insert(idx, track2)
        self.gpx_handler.gpx.tracks.insert(idx, track1)

        self.result = "split"
        self._refresh_track_lists()
        messagebox.showinfo("完成", f"航迹已分割为两段")
