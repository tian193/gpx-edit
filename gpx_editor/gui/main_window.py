# -*- coding: utf-8 -*-
"""
主窗口模块
功能: 应用程序主窗口界面
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from ..core.gpx_handler import GpxHandler
from ..core.coord_converter import CoordConverter, TiandituTileProvider
from tkintermapview import TkinterMapView
from .undo_manager import UndoManager
from .excel_export_dialog import ExcelExportDialog
from .column_config_dialog import ColumnConfigManager, ColumnConfigDialog, COLUMN_DEFINITIONS


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
        self.gpx_handler = GpxHandler()
        self.is_modified = False
        self.undo_manager = UndoManager()
        self.column_config = ColumnConfigManager()
        self._clipboard = None  # {'type': 'waypoint'|'track', 'data': {...}}
        self._current_zone = None
        self._tianditu_key = None
        self._current_map_layer = "road"

        # 航点拖拽模式
        self._drag_mode = False           # 是否处于拖拽模式
        self._drag_target = None          # 当前拖拽的marker
        self._drag_index = -1             # 当前拖拽的航点索引
        self._drag_data = {}              # 拖拽临时数据

        # 航迹点交互状态
        self._track_point_markers = []    # 航迹点marker列表: [(marker, trk_index, seg_index, pt_index), ...]
        self._dragging_track_marker = None
        self._track_drag_data = {}

        # 航迹点轻量圆点
        self._track_point_dots = []       # [(canvas_id, trk_index, seg_index, pt_index), ...]
        self._selected_track_points = set()  # 选中的航迹点: (trk_index, seg_index, pt_index)
        self._dragging_track_dots = False  # 是否正在拖动航迹点
        self._track_dot_drag_start = None  # 拖动起始canvas坐标

        # 地图工具和选中状态
        self._map_tool = "hand"              # 当前工具: "hand" / "rect" / "lasso"
        self._selected_waypoints = set()     # 选中的航点索引集合
        self._selection_rect_id = None       # 矩形框选canvas对象ID
        self._selection_lasso_id = None      # 任意框选canvas对象ID
        self._selection_points = []          # 框选过程中的坐标点列表
        self._selection_start_x = 0          # 框选起点x
        self._selection_start_y = 0          # 框选起点y
        self._marker_clicked = False         # 标记是否点击了marker
        self._syncing_selection = False      # 防止选中同步的递归触发

        self._setup_ui()
        self._create_menu()
        self._create_main_layout()
        self._create_statusbar()

        # 关闭窗口时检查未保存
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        file_menu.add_command(label="退出", command=self._on_close)

        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="撤销", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="重做", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="添加航点", command=self.add_waypoint, accelerator="Ctrl+Shift+W")
        edit_menu.add_command(label="添加航迹", command=self.add_track, accelerator="Ctrl+Shift+T")
        edit_menu.add_separator()
        edit_menu.add_command(label="编辑航点", command=self._edit_selected_waypoint)
        edit_menu.add_command(label="移动航点...", command=self._move_selected_waypoint)
        edit_menu.add_separator()
        edit_menu.add_command(label="删除选中", command=self._delete_selected, accelerator="Delete")

        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="卫星图层", command=self._toggle_satellite)
        view_menu.add_separator()
        view_menu.add_command(label="设置天地图Key", command=self._settings_tianditu_key)

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
        tools_menu.add_separator()
        tools_menu.add_command(label="航迹操作", command=self.track_operations)
        tools_menu.add_command(label="三方数据校验", command=self.verify_three_way)
        tools_menu.add_separator()
        tools_menu.add_command(label="导出航点到Excel", command=self.export_waypoints_to_excel)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

        # 绑定快捷键
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-c>", lambda e: self._keyboard_copy())
        self.bind("<Control-v>", lambda e: self._keyboard_paste())
        self.bind("<Control-x>", lambda e: self._keyboard_cut())
        self.bind("<Control-Shift-W>", lambda e: self.add_waypoint())
        self.bind("<Control-Shift-T>", lambda e: self.add_track())
        self.bind("<Delete>", lambda e: self._delete_selected())

    def _create_main_layout(self):
        """创建主布局"""
        # 主分割窗口
        paned = ttk.PanedWindow(self, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 航点/航迹列表
        left_frame = ttk.LabelFrame(paned, text="数据列表", padding=5)
        paned.add(left_frame, weight=1)

        # 树形列表 + 滚动条
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=VERTICAL)
        scrollbar_y.pack(side=RIGHT, fill=Y)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=HORIZONTAL)
        scrollbar_x.pack(side=BOTTOM, fill=X)

        # 初始化tree占位，后续由_rebuild_tree_columns重建
        self.tree = None
        self._tree_frame = tree_frame
        self._tree_scrollbar_y = scrollbar_y
        self._tree_scrollbar_x = scrollbar_x
        self._rebuild_tree_columns()

        # 右键菜单
        self._create_context_menu()

        # 右侧面板 - 地图
        right_frame = ttk.LabelFrame(paned, text="地图视图", padding=5)
        paned.add(right_frame, weight=2)

        # 地图工具栏
        toolbar_frame = ttk.Frame(right_frame)
        toolbar_frame.pack(fill=X, pady=(0, 2))

        self._tool_buttons = {}
        tool_info = [
            ("hand", "✋ 手型", "平移地图"),
            ("rect", "▭ 矩形", "矩形框选航点"),
            ("lasso", "✏ 任意", "任意框选航点"),
        ]
        for tool_id, label, tip in tool_info:
            btn = ttk.Button(
                toolbar_frame, text=label, width=8,
                command=lambda t=tool_id: self._set_map_tool(t)
            )
            btn.pack(side=LEFT, padx=2)
            self._tool_buttons[tool_id] = btn

        # 默认高亮手型工具
        self._update_tool_buttons()

        # 地图组件 - 天地图
        self.map_widget = TkinterMapView(right_frame, corner_radius=0)
        self.map_widget.pack(fill=BOTH, expand=True)
        self._init_tianditu_map()

        # 地图标记引用
        self._map_markers = []
        self._map_paths = []

        # 钩入地图重绘以更新航迹点圆点位置
        self._orig_draw_move = self.map_widget.draw_move
        self.map_widget.draw_move = self._patched_draw_move
        self._orig_draw_initial_array = self.map_widget.draw_initial_array
        self.map_widget.draw_initial_array = self._patched_draw_initial_array

        # 地图鼠标事件
        self.map_widget.canvas.bind("<Motion>", self._on_map_mouse_move)
        self.map_widget.canvas.bind("<Double-1>", self._on_map_double_click)
        # 统一的鼠标事件处理（工具栏模式）
        self.map_widget.canvas.bind("<ButtonPress-1>", self._on_tool_press, add=True)
        self.map_widget.canvas.bind("<B1-Motion>", self._on_tool_drag, add=True)
        self.map_widget.canvas.bind("<ButtonRelease-1>", self._on_tool_release, add=True)

        # 键盘快捷键
        self.bind("<Escape>", lambda e: self._clear_all_selections())
        self.bind("<Control-a>", lambda e: self._select_all_waypoints())

        # 地图右键菜单 - 在此添加航点
        self.map_widget.add_right_click_menu_command(
            "在此添加航点", self._add_waypoint_at_map_coords, pass_coords=True
        )

    def _create_statusbar(self):
        """创建状态栏"""
        statusbar = ttk.Frame(self)
        statusbar.pack(fill=X, side=BOTTOM, padx=5, pady=2)

        self.status_label = ttk.Label(statusbar, text="就绪")
        self.status_label.pack(side=LEFT)

        self.count_label = ttk.Label(statusbar, text="")
        self.count_label.pack(side=LEFT, padx=20)

        self.file_label = ttk.Label(statusbar, text="未打开文件")
        self.file_label.pack(side=RIGHT)

    def _update_status_counts(self):
        """更新状态栏的航点/航迹计数"""
        if self.gpx_handler.gpx:
            wpt_count = len(self.gpx_handler.get_waypoints())
            trk_count = len(self.gpx_handler.get_tracks())
            self.count_label.config(text=f"航点: {wpt_count}  航迹: {trk_count}")
        else:
            self.count_label.config(text="")

    # ========== 树形列表 ==========

    def _rebuild_tree_columns(self):
        """重建树形列表列配置"""
        visible_cols = self.column_config.get_ordered_visible_columns()
        col_ids = [col["id"] for col in visible_cols]

        # 保存旧的tree引用
        old_tree = self.tree if hasattr(self, 'tree') and self.tree else None
        tree_frame = getattr(self, '_tree_frame', None)

        if tree_frame is None:
            if old_tree:
                tree_frame = old_tree.master
            else:
                return

        # 获取滚动条
        scrollbar_y = getattr(self, '_tree_scrollbar_y', None)
        scrollbar_x = getattr(self, '_tree_scrollbar_x', None)

        if old_tree:
            old_tree.destroy()

        self.tree = ttk.Treeview(tree_frame, columns=col_ids,
                                  show="tree headings")
        if scrollbar_y:
            scrollbar_y.config(command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar_y.set)
        if scrollbar_x:
            scrollbar_x.config(command=self.tree.xview)
            self.tree.configure(xscrollcommand=scrollbar_x.set)

        # 设置列头
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=30, stretch=False)

        for col in visible_cols:
            col_id = col["id"]
            col_name = col["name"]
            if col_id in ("cgcs2000_x", "cgcs2000_y") and hasattr(self, '_current_zone') and self._current_zone:
                col_name = f"{col_name} ({self._current_zone}带)"
            self.tree.heading(col_id, text=col_name)
            width = self.column_config.get_column_width(col_id)
            self.tree.column(col_id, width=width, minwidth=50)

        self.tree.pack(fill=BOTH, expand=True)

        # 绑定事件
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

    def _show_column_config_popup(self, event):
        """在列头区域右键显示列配置弹出菜单"""
        menu = tk.Menu(self, tearoff=0)
        for col in COLUMN_DEFINITIONS:
            col_id = col["id"]
            col_name = col["name"]
            var = tk.BooleanVar(value=(col_id in self.column_config.visible_columns))
            menu.add_checkbutton(
                label=col_name, variable=var,
                command=lambda cid=col_id, v=var: self._toggle_column(cid, v.get())
            )
        menu.add_separator()
        menu.add_command(label="重置默认列", command=self._reset_columns)
        menu.post(event.x_root, event.y_root)

    def _toggle_column(self, col_id, visible):
        """切换列的显示/隐藏"""
        visible_cols = self.column_config.visible_columns[:]
        if visible and col_id not in visible_cols:
            visible_cols.append(col_id)
        elif not visible and col_id in visible_cols:
            visible_cols.remove(col_id)
        self.column_config.visible_columns = visible_cols
        self.column_config.save()
        self._rebuild_tree_columns()
        self._populate_tree()

    def _reset_columns(self):
        """重置为默认列配置"""
        from .column_config_dialog import DEFAULT_VISIBLE, DEFAULT_ORDER
        self.column_config.visible_columns = DEFAULT_VISIBLE[:]
        self.column_config.column_order = DEFAULT_ORDER[:]
        self.column_config.save()
        self._rebuild_tree_columns()
        self._populate_tree()

    def _populate_tree(self):
        """填充树形列表"""
        self.tree.delete(*self.tree.get_children())

        if not self.gpx_handler.gpx:
            return

        # 计算CGCS2000带号
        self._current_zone = None
        waypoints = self.gpx_handler.get_waypoints()
        if waypoints and waypoints[0].latitude is not None and waypoints[0].longitude is not None:
            _, _, self._current_zone = CoordConverter.wgs84_to_cgcs2000(
                waypoints[0].latitude, waypoints[0].longitude
            )
            self._update_column_headers()

        visible_cols = self.column_config.get_ordered_visible_columns()

        # 直接添加航点（不使用分组）
        for i, wpt in enumerate(waypoints):
            values = self._get_waypoint_values(wpt, visible_cols)
            self.tree.insert("", END, iid=f"wpt_{i}", text=" ", values=values)

        # 直接添加航迹（不使用分组）
        tracks = self.gpx_handler.get_tracks()
        for i, trk in enumerate(tracks):
            values = self._get_track_values(trk, visible_cols)
            self.tree.insert("", END, iid=f"trk_{i}", text=" ", values=values)

        self._update_status_counts()
        self._update_map()

    def _get_waypoint_values(self, wpt, visible_cols):
        """获取航点在各列的值"""
        values = []
        for col in visible_cols:
            col_id = col["id"]
            if col_id == "type":
                values.append("航点")
            elif col_id == "name":
                values.append(wpt.name or "")
            elif col_id == "lat":
                values.append(f"{wpt.latitude:.6f}" if wpt.latitude is not None else "")
            elif col_id == "lon":
                values.append(f"{wpt.longitude:.6f}" if wpt.longitude is not None else "")
            elif col_id == "ele":
                values.append(f"{wpt.elevation:.1f}" if wpt.elevation is not None else "")
            elif col_id == "time":
                values.append(str(wpt.time) if wpt.time else "")
            elif col_id == "desc":
                values.append(wpt.description or "")
            elif col_id == "cmt":
                values.append(wpt.comment or "")
            elif col_id == "sym":
                values.append(wpt.symbol or "")
            elif col_id == "source":
                values.append(wpt.source or "")
            elif col_id in ("cgcs2000_x", "cgcs2000_y"):
                if wpt.latitude is not None and wpt.longitude is not None:
                    x, y, _ = CoordConverter.wgs84_to_cgcs2000(wpt.latitude, wpt.longitude)
                    values.append(f"{x:.3f}" if col_id == "cgcs2000_x" else f"{y:.3f}")
                else:
                    values.append("")
            else:
                values.append("")
        return tuple(values)

    def _get_track_values(self, trk, visible_cols):
        """获取航迹在各列的值"""
        values = []
        for col in visible_cols:
            col_id = col["id"]
            if col_id == "type":
                values.append("航迹")
            elif col_id == "name":
                values.append(trk.name or "")
            elif col_id == "desc":
                values.append(trk.description or "")
            elif col_id == "cmt":
                values.append(trk.comment or "")
            elif col_id == "source":
                values.append(trk.source or "")
            else:
                values.append("")
        return tuple(values)

    def _update_column_headers(self):
        """更新列头显示（带号信息）"""
        if not hasattr(self, '_current_zone') or not self._current_zone:
            return
        for col in self.column_config.get_ordered_visible_columns():
            if col["id"] in ("cgcs2000_x", "cgcs2000_y"):
                self.tree.heading(col["id"], text=f"{col['name']} ({self._current_zone}带)")

    def _on_tree_select(self, event):
        """树形列表选择事件"""
        if self._syncing_selection:
            return

        selected = self.tree.selection()

        # 同步地图marker高亮
        for idx in list(self._selected_waypoints):
            self._unhighlight_marker(idx)
        self._selected_waypoints.clear()

        for item_id in selected:
            if item_id.startswith("wpt_"):
                idx = int(item_id.split("_")[1])
                self._selected_waypoints.add(idx)
                self._highlight_marker(idx)

        if not selected:
            self.status_label.config(text="就绪")
            return
        iid = selected[0]
        if iid.startswith("wpt_"):
            index = int(iid.split("_")[1])
            wpt = self.gpx_handler.get_waypoints()[index]
            self.status_label.config(text=f"选中航点: {wpt.name} ({wpt.latitude:.6f}, {wpt.longitude:.6f})")
        elif iid.startswith("trk_"):
            index = int(iid.split("_")[1])
            track = self.gpx_handler.get_tracks()[index]
            point_count = sum(len(seg.points) for seg in track.segments)
            self.status_label.config(text=f"选中航迹: {track.name} ({point_count}点)")

        self._update_selection_status()

    def _on_tree_double_click(self, event):
        """树形列表双击事件"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        if iid.startswith("wpt_"):
            index = int(iid.split("_")[1])
            self.edit_waypoint(index)
        elif iid.startswith("trk_"):
            index = int(iid.split("_")[1])
            self.edit_track(index)

    # ========== 地图 ==========

    def _set_map_tool(self, tool):
        """切换地图工具"""
        self._clear_selection_graphics()
        self._map_tool = tool
        self._update_tool_buttons()
        if tool == "hand":
            self.map_widget.canvas.config(cursor="arrow")
            self.map_widget.selection_mode = False
        else:
            self.map_widget.canvas.config(cursor="crosshair")
            self.map_widget.selection_mode = True

    def _update_tool_buttons(self):
        """更新工具栏按钮高亮状态"""
        for tool_id, btn in self._tool_buttons.items():
            if tool_id == self._map_tool:
                btn.state(["pressed"])
            else:
                btn.state(["!pressed"])

    def _clear_selection_graphics(self):
        """清除框选临时图形"""
        if self._selection_rect_id:
            self.map_widget.canvas.delete(self._selection_rect_id)
            self._selection_rect_id = None
        if self._selection_lasso_id:
            self.map_widget.canvas.delete(self._selection_lasso_id)
            self._selection_lasso_id = None
        self._selection_points.clear()

    def _on_tool_press(self, event):
        """工具模式下的鼠标按下"""
        if self._drag_mode:
            self._on_map_press(event)
            return
        self._marker_clicked = False
        self._dragging_track_dots = False
        if self._map_tool == "hand":
            # 检查是否点击了选中的航迹点圆点（开始拖动）
            if self._selected_track_points:
                clicked_dot = self._find_track_dot_at(event.x, event.y)
                if clicked_dot and clicked_dot in self._selected_track_points:
                    self._dragging_track_dots = True
                    self._track_dot_drag_start = (event.x, event.y)
                    self._track_dot_drag_orig = {}  # {key: (lat, lon)}
                    tracks = self.gpx_handler.get_tracks()
                    for key in self._selected_track_points:
                        ti, si, pi = key
                        if 0 <= ti < len(tracks):
                            seg = tracks[ti].segments[si]
                            if 0 <= pi < len(seg.points):
                                pt = seg.points[pi]
                                self._track_dot_drag_orig[key] = (pt.latitude, pt.longitude)
                    return
            self._selection_start_x = event.x
            self._selection_start_y = event.y
        elif self._map_tool == "rect":
            self._selection_start_x = event.x
            self._selection_start_y = event.y
            self._clear_selection_graphics()
        elif self._map_tool == "lasso":
            self._selection_points = [(event.x, event.y)]
            self._clear_selection_graphics()

    def _on_tool_drag(self, event):
        """工具模式下的鼠标拖拽"""
        if self._drag_mode:
            self._on_map_motion(event)
            return
        # 拖动航迹点圆点
        if self._dragging_track_dots:
            dx = event.x - self._track_dot_drag_start[0]
            dy = event.y - self._track_dot_drag_start[1]
            canvas = self.map_widget.canvas
            r = self._TRACK_DOT_RADIUS
            for key in self._selected_track_points:
                for dot_id, ti, si, pi in self._track_point_dots:
                    if (ti, si, pi) == key:
                        pos = self._get_track_dot_canvas_pos(ti, si, pi)
                        if pos:
                            orig_cx, orig_cy = pos
                            # 计算原始位置（拖拽前）
                            orig_key = self._track_dot_drag_orig.get(key)
                            if orig_key:
                                try:
                                    orig_pos = self._latlon_to_canvas(*orig_key)
                                    if orig_pos:
                                        new_cx = orig_pos[0] + dx
                                        new_cy = orig_pos[1] + dy
                                        canvas.coords(dot_id, new_cx - r, new_cy - r, new_cx + r, new_cy + r)
                                except Exception:
                                    pass
                        break
            return
        if self._map_tool == "rect":
            if self._selection_rect_id:
                self.map_widget.canvas.delete(self._selection_rect_id)
            self._selection_rect_id = self.map_widget.canvas.create_rectangle(
                self._selection_start_x, self._selection_start_y,
                event.x, event.y,
                outline="#3399ff", width=2,
                fill="#3399ff", stipple="gray25"
            )
        elif self._map_tool == "lasso":
            self._selection_points.append((event.x, event.y))
            if self._selection_lasso_id:
                self.map_widget.canvas.delete(self._selection_lasso_id)
            if len(self._selection_points) >= 2:
                flat_points = [coord for point in self._selection_points for coord in point]
                self._selection_lasso_id = self.map_widget.canvas.create_line(
                    *flat_points, fill="#3399ff", width=2, dash=(4, 4)
                )

    def _on_tool_release(self, event):
        """工具模式下的鼠标释放"""
        if self._drag_mode:
            self._on_map_release(event)
            return
        # 完成航迹点拖动
        if self._dragging_track_dots:
            self._finish_track_dot_drag(event)
            self._dragging_track_dots = False
            return
        if self._map_tool == "hand":
            dx = abs(event.x - self._selection_start_x)
            dy = abs(event.y - self._selection_start_y)
            if dx < 5 and dy < 5:
                if not self._marker_clicked:
                    self._clear_all_selections()
            self._marker_clicked = False
        elif self._map_tool == "rect":
            self._finish_rect_selection(event)
        elif self._map_tool == "lasso":
            self._finish_lasso_selection(event)

    def _update_selection_status(self):
        """更新状态栏的选中信息"""
        wpt_count = len(self._selected_waypoints)
        dot_count = len(self._selected_track_points)
        total = wpt_count + dot_count
        if total == 0:
            self.status_label.config(text="就绪")
        elif total == 1:
            if wpt_count == 1:
                idx = next(iter(self._selected_waypoints))
                wpt = self.gpx_handler.get_waypoints()[idx]
                name = wpt.name or f"航点{idx+1}"
                self.status_label.config(
                    text=f"已选中：{name} ({wpt.latitude:.6f}, {wpt.longitude:.6f})")
            else:
                key = next(iter(self._selected_track_points))
                ti, si, pi = key
                tracks = self.gpx_handler.get_tracks()
                pt = tracks[ti].segments[si].points[pi]
                self.status_label.config(
                    text=f"已选中：航迹点 {pi} ({pt.latitude:.6f}, {pt.longitude:.6f})")
        else:
            parts = []
            if wpt_count > 0:
                parts.append(f"{wpt_count} 个航点")
            if dot_count > 0:
                parts.append(f"{dot_count} 个航迹点")
            self.status_label.config(text=f"已选中 {' + '.join(parts)}")

    def _finish_rect_selection(self, event):
        """完成矩形框选"""
        x0, y0 = self._selection_start_x, self._selection_start_y
        x1, y1 = event.x, event.y
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        self._clear_selection_graphics()

        # 忽略太小的框选
        if max_x - min_x < 5 and max_y - min_y < 5:
            return

        # 如果不按Ctrl，先清除已有选中
        ctrl_pressed = event.state & 0x4
        if not ctrl_pressed:
            self._clear_all_selections()

        # 遍历所有航点marker，检查是否在矩形范围内
        self._syncing_selection = True
        try:
            for i, marker in enumerate(self._map_markers):
                canvas_pos = self._get_marker_canvas_pos(marker)
                if canvas_pos is None:
                    continue
                cx, cy = canvas_pos
                if min_x <= cx <= max_x and min_y <= cy <= max_y:
                    self._selected_waypoints.add(i)
                    self._highlight_marker(i)
                    self.tree.selection_add(f"wpt_{i}")
            # 遍历航迹点圆点，检查是否在矩形范围内
            for dot_id, ti, si, pi in self._track_point_dots:
                pos = self._get_track_dot_canvas_pos(ti, si, pi)
                if pos is None:
                    continue
                cx, cy = pos
                if min_x <= cx <= max_x and min_y <= cy <= max_y:
                    key = (ti, si, pi)
                    self._selected_track_points.add(key)
                    self._highlight_track_dot(key)
        finally:
            self._syncing_selection = False

        self._update_selection_status()

    def _finish_lasso_selection(self, event):
        """完成任意框选"""
        self._selection_points.append((event.x, event.y))
        polygon = list(self._selection_points)
        self._clear_selection_graphics()

        if len(polygon) < 3:
            return

        ctrl_pressed = event.state & 0x4
        if not ctrl_pressed:
            self._clear_all_selections()

        self._syncing_selection = True
        try:
            for i, marker in enumerate(self._map_markers):
                canvas_pos = self._get_marker_canvas_pos(marker)
                if canvas_pos is None:
                    continue
                cx, cy = canvas_pos
                if self._point_in_polygon(cx, cy, polygon):
                    self._selected_waypoints.add(i)
                    self._highlight_marker(i)
                    self.tree.selection_add(f"wpt_{i}")
            # 遍历航迹点圆点，检查是否在多边形内
            for dot_id, ti, si, pi in self._track_point_dots:
                pos = self._get_track_dot_canvas_pos(ti, si, pi)
                if pos is None:
                    continue
                cx, cy = pos
                if self._point_in_polygon(cx, cy, polygon):
                    key = (ti, si, pi)
                    self._selected_track_points.add(key)
                    self._highlight_track_dot(key)
        finally:
            self._syncing_selection = False

        self._update_selection_status()

    @staticmethod
    def _point_in_polygon(x, y, polygon):
        """射线法判断点是否在多边形内"""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def _get_marker_canvas_pos(self, marker):
        """获取marker在canvas上的坐标"""
        try:
            canvas_pos = marker.get_canvas_pos(marker.position)
            return canvas_pos
        except Exception:
            return None

    def _toggle_satellite(self):
        """切换卫星图层"""
        if not self._tianditu_key:
            messagebox.showinfo("提示", "请先配置天地图API Key")
            return

        if self._current_map_layer == "road":
            img_url = TiandituTileProvider.get_satellite_url(self._tianditu_key)
            cia_url = TiandituTileProvider.get_annotation_url(self._tianditu_key)
            self.map_widget.set_overlay_tile_server(cia_url)
            self.map_widget.set_tile_server(img_url, max_zoom=18)
            self._current_map_layer = "satellite"
            self.status_label.config(text="已开启卫星图层")
        else:
            road_url = TiandituTileProvider.get_road_url(self._tianditu_key)
            self.map_widget.set_tile_server(road_url, max_zoom=18)
            self.map_widget.set_overlay_tile_server(None)
            self._current_map_layer = "road"
            self.status_label.config(text="已关闭卫星图层")

    # ========== 天地图配置 ==========

    def _load_config(self):
        """加载配置"""
        config_dir = os.path.expanduser("~/.gpx_editor")
        config_file = os.path.join(config_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, config):
        """保存配置"""
        config_dir = os.path.expanduser("~/.gpx_editor")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "config.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _get_tianditu_key(self):
        """获取天地图API Key"""
        config = self._load_config()
        return config.get("tianditu_api_key", "")

    def _set_tianditu_key(self, key):
        """设置天地图API Key"""
        config = self._load_config()
        config["tianditu_api_key"] = key
        self._save_config(config)

    def _init_tianditu_map(self):
        """初始化天地图"""
        api_key = self._get_tianditu_key()
        if not api_key:
            api_key = self._prompt_api_key()
            if not api_key:
                self._init_default_map()
                return

        self._tianditu_key = api_key
        self._current_map_layer = "road"

        road_url = TiandituTileProvider.get_road_url(api_key)
        self.map_widget.set_tile_server(road_url, max_zoom=18)

        self.map_widget.set_position(35.0, 105.0)
        self.map_widget.set_zoom(5)

    def _init_default_map(self):
        """初始化默认地图（OpenStreetMap）"""
        self._tianditu_key = None
        self._current_map_layer = "road"
        self.map_widget.set_tile_server(
            "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            max_zoom=19
        )
        self.map_widget.set_position(35.0, 105.0)
        self.map_widget.set_zoom(5)

    def _prompt_api_key(self):
        """提示输入天地图API Key"""
        from tkinter import simpledialog
        key = simpledialog.askstring(
            "天地图API Key",
            "请输入天地图API Key（免费申请：https://console.tianditu.gov.cn/）",
            parent=self
        )
        if key:
            self._set_tianditu_key(key.strip())
        return key

    def _settings_tianditu_key(self):
        """设置天地图API Key"""
        from tkinter import simpledialog
        current_key = self._get_tianditu_key()
        key = simpledialog.askstring(
            "天地图API Key",
            "请输入天地图API Key（免费申请：https://console.tianditu.gov.cn/）",
            initialvalue=current_key,
            parent=self
        )
        if key:
            self._set_tianditu_key(key.strip())
            self._tianditu_key = key.strip()
            road_url = TiandituTileProvider.get_road_url(key.strip())
            self.map_widget.set_tile_server(road_url, max_zoom=18)
            self.map_widget.set_overlay_tile_server(None)
            self._current_map_layer = "road"
            self.status_label.config(text="已更新天地图API Key")

    def _on_map_mouse_move(self, event):
        """鼠标悬停显示坐标"""
        if getattr(self, '_drag_mode', False):
            return
        try:
            lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
            self.status_label.config(text=f"坐标: {lat:.6f}, {lon:.6f}")
        except Exception:
            pass

    def _add_waypoint_at_map_coords(self, coords):
        """在地图右键位置添加航点"""
        from .waypoint_dialog import WaypointDialog
        self._ensure_gpx_loaded()
        lat, lon = coords
        dialog = WaypointDialog(self, lat=lat, lon=lon)
        if dialog.result:
            name, lat, lon, ele, desc = dialog.result
            self.gpx_handler.add_waypoint(name, lat, lon, ele, desc)
            self.undo_manager.push({
                'type': 'add_waypoint',
                'data': {'name': name, 'lat': lat, 'lon': lon, 'ele': ele, 'desc': desc},
                'reverse_data': {'index': len(self.gpx_handler.get_waypoints()) - 1}
            })
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已添加航点: {name}")

    def _update_map(self):
        """更新地图显示"""
        for marker in self._map_markers:
            marker.delete()
        for path in self._map_paths:
            path.delete()
        for item in self._track_point_markers:
            item[0].delete()
        # 清除航迹点圆点
        for dot_id, _, _, _ in self._track_point_dots:
            self.map_widget.canvas.delete(dot_id)
        self._map_markers.clear()
        self._map_paths.clear()
        self._track_point_markers.clear()
        self._track_point_dots.clear()

        if not self.gpx_handler.gpx:
            return

        # 添加航点标记（点击选中，右键菜单）
        for i, wpt in enumerate(self.gpx_handler.get_waypoints()):
            if wpt.latitude is not None and wpt.longitude is not None:
                name = wpt.name or f"航点{i+1}"
                marker = self.map_widget.set_marker(wpt.latitude, wpt.longitude, text=name)
                self._map_markers.append(marker)
                # 绑定点击和右键事件
                self._bind_marker_click(marker, i)

        # 添加航迹路径
        track_points_to_draw = []  # 延迟创建航迹点圆点
        for ti, track in enumerate(self.gpx_handler.get_tracks()):
            for si, segment in enumerate(track.segments):
                valid_points = [(pi, p) for pi, p in enumerate(segment.points)
                                if p.latitude is not None and p.longitude is not None]
                if len(valid_points) >= 2:
                    coords = [(p.latitude, p.longitude) for _, p in valid_points]
                    path = self.map_widget.set_path(coords, color="green", width=2)
                    path._trk_index = ti
                    self._map_paths.append(path)
                # 记录航迹点数据，延迟创建圆点
                for pi, point in valid_points:
                    track_points_to_draw.append((point.latitude, point.longitude, ti, si, pi))

        self._zoom_to_fit()

        # 延迟创建航迹点圆点（等地图视口设置完成后）
        if track_points_to_draw:
            self.after(100, lambda: self._create_track_dots_batch(track_points_to_draw))

    def _zoom_to_fit(self):
        """缩放地图以显示所有数据"""
        bounds = self.gpx_handler.get_bounds()
        if bounds:
            min_lat, min_lon, max_lat, max_lon = bounds
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            self.map_widget.set_position(center_lat, center_lon)

            lat_diff = max_lat - min_lat
            lon_diff = max_lon - min_lon
            max_diff = max(lat_diff, lon_diff)
            if max_diff > 0:
                if max_diff > 10:
                    zoom = 4
                elif max_diff > 5:
                    zoom = 5
                elif max_diff > 2:
                    zoom = 6
                elif max_diff > 1:
                    zoom = 7
                elif max_diff > 0.5:
                    zoom = 8
                elif max_diff > 0.1:
                    zoom = 10
                else:
                    zoom = 12
                self.map_widget.set_zoom(zoom)

    # ========== 航迹点圆点交互 ==========

    _TRACK_DOT_COLOR = "#2ECC71"
    _TRACK_DOT_SELECTED = "#E74C3C"
    _TRACK_DOT_RADIUS = 3

    def _latlon_to_canvas(self, lat, lon):
        """将经纬度转换为canvas像素坐标"""
        from tkintermapview.utility_functions import decimal_to_osm
        widget = self.map_widget
        tile_pos = decimal_to_osm(lat, lon, round(widget.zoom))
        tile_w = widget.lower_right_tile_pos[0] - widget.upper_left_tile_pos[0]
        tile_h = widget.lower_right_tile_pos[1] - widget.upper_left_tile_pos[1]
        if tile_w == 0 or tile_h == 0:
            return None
        cx = ((tile_pos[0] - widget.upper_left_tile_pos[0]) / tile_w) * widget.width
        cy = ((tile_pos[1] - widget.upper_left_tile_pos[1]) / tile_h) * widget.height
        return (cx, cy)

    def _create_track_dot(self, lat, lon, trk_index, seg_index, pt_index):
        """创建轻量航迹点圆点"""
        canvas = self.map_widget.canvas
        canvas_pos = self._latlon_to_canvas(lat, lon)
        if canvas_pos is None:
            return
        cx, cy = canvas_pos
        r = self._TRACK_DOT_RADIUS
        dot_id = canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                     fill=self._TRACK_DOT_COLOR,
                                     outline="", tags="track_dot")
        canvas.tag_bind(dot_id, '<Button-1>',
                        lambda e, ti=trk_index, si=seg_index, pi=pt_index:
                            self._on_track_dot_click(ti, si, pi, e))
        canvas.tag_bind(dot_id, '<Button-3>',
                        lambda e, ti=trk_index, si=seg_index, pi=pt_index:
                            self._on_track_dot_right_click(e, ti, si, pi))
        self._track_point_dots.append((dot_id, trk_index, seg_index, pt_index))

    def _create_track_dots_batch(self, points_data):
        """批量创建航迹点圆点（延迟调用，确保视口已设置）"""
        for lat, lon, ti, si, pi in points_data:
            self._create_track_dot(lat, lon, ti, si, pi)

    def _on_track_dot_click(self, trk_index, seg_index, pt_index, event):
        """点击航迹点圆点"""
        self._marker_clicked = True
        key = (trk_index, seg_index, pt_index)
        ctrl_pressed = event.state & 0x4
        if not ctrl_pressed:
            self._clear_all_selections()
        self._syncing_selection = True
        try:
            if key in self._selected_track_points:
                self._selected_track_points.discard(key)
                self._set_track_dot_color(key, self._TRACK_DOT_COLOR)
            else:
                self._selected_track_points.add(key)
                self._set_track_dot_color(key, self._TRACK_DOT_SELECTED)
        finally:
            self._syncing_selection = False
        self._update_selection_status()

    def _on_track_dot_right_click(self, event, trk_index, seg_index, pt_index):
        """右键航迹点圆点"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="删除此航迹点",
                         command=lambda: self._delete_track_point(trk_index, seg_index, pt_index))
        menu.post(event.x_root, event.y_root)

    def _set_track_dot_color(self, key, color):
        """设置航迹点圆点颜色"""
        for dot_id, ti, si, pi in self._track_point_dots:
            if (ti, si, pi) == key:
                self.map_widget.canvas.itemconfigure(dot_id, fill=color)
                break

    def _highlight_track_dot(self, key):
        """高亮航迹点圆点"""
        self._set_track_dot_color(key, self._TRACK_DOT_SELECTED)

    def _unhighlight_track_dot(self, key):
        """取消航迹点圆点高亮"""
        self._set_track_dot_color(key, self._TRACK_DOT_COLOR)

    def _get_track_dot_canvas_pos(self, trk_index, seg_index, pt_index):
        """获取航迹点圆点的canvas坐标"""
        tracks = self.gpx_handler.get_tracks()
        if 0 <= trk_index < len(tracks):
            track = tracks[trk_index]
            if 0 <= seg_index < len(track.segments):
                seg = track.segments[seg_index]
                if 0 <= pt_index < len(seg.points):
                    pt = seg.points[pt_index]
                    if pt.latitude is not None and pt.longitude is not None:
                        return self._latlon_to_canvas(pt.latitude, pt.longitude)
        return None

    def _update_track_dot_positions(self):
        """更新所有航迹点圆点的canvas位置（地图平移/缩放后调用）"""
        canvas = self.map_widget.canvas
        r = self._TRACK_DOT_RADIUS
        for dot_id, ti, si, pi in self._track_point_dots:
            pos = self._get_track_dot_canvas_pos(ti, si, pi)
            if pos:
                cx, cy = pos
                canvas.coords(dot_id, cx - r, cy - r, cx + r, cy + r)

    def _patched_draw_move(self, called_after_zoom=False):
        """地图重绘后更新航迹点圆点位置"""
        self._orig_draw_move(called_after_zoom)
        if self._track_point_dots:
            self._update_track_dot_positions()

    def _patched_draw_initial_array(self):
        """地图初始数组重绘后更新航迹点圆点位置"""
        self._orig_draw_initial_array()
        if self._track_point_dots:
            self.after(10, self._update_track_dot_positions)

    def _find_track_dot_at(self, x, y):
        """查找canvas坐标(x,y)附近的航迹点，返回key (ti,si,pi) 或 None"""
        r = 10  # 点击容差半径
        for dot_id, ti, si, pi in self._track_point_dots:
            pos = self._get_track_dot_canvas_pos(ti, si, pi)
            if pos:
                cx, cy = pos
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    return (ti, si, pi)
        return None

    def _finish_track_dot_drag(self, event):
        """完成航迹点拖动"""
        if not hasattr(self, '_track_dot_drag_orig') or not self._track_dot_drag_orig:
            return
        dx = event.x - self._track_dot_drag_start[0]
        dy = event.y - self._track_dot_drag_start[1]
        if abs(dx) < 3 and abs(dy) < 3:
            return  # 移动太小，忽略

        tracks = self.gpx_handler.get_tracks()
        modified_tracks = set()
        for key in self._selected_track_points:
            ti, si, pi = key
            orig = self._track_dot_drag_orig.get(key)
            if orig is None:
                continue
            orig_lat, orig_lon = orig
            # 计算新位置
            try:
                orig_pos = self._latlon_to_canvas(orig_lat, orig_lon)
                if orig_pos:
                    new_cx = orig_pos[0] + dx
                    new_cy = orig_pos[1] + dy
                    new_coords = self.map_widget.convert_canvas_coords_to_decimal_coords(new_cx, new_cy)
                    new_lat, new_lon = new_coords
                    # 更新GPXTrackPoint
                    if 0 <= ti < len(tracks):
                        seg = tracks[ti].segments[si]
                        if 0 <= pi < len(seg.points):
                            pt = seg.points[pi]
                            pt.latitude = new_lat
                            pt.longitude = new_lon
                            modified_tracks.add(ti)
                            # 推送撤销命令
                            self.undo_manager.push({
                                'type': 'move_track_point',
                                'data': {'trk_index': ti, 'seg_index': si,
                                         'pt_index': pi, 'lat': new_lat, 'lon': new_lon},
                                'reverse_data': {'trk_index': ti, 'seg_index': si,
                                                  'pt_index': pi, 'lat': orig_lat, 'lon': orig_lon}
                            })
            except Exception:
                continue

        # 重绘受影响的航迹路径
        for ti in modified_tracks:
            self._redraw_track_path(ti)
        self._update_map()
        self._mark_modified()
        self.status_label.config(text=f"已移动 {len(self._selected_track_points)} 个航迹点")

    def _redraw_track_path(self, trk_index):
        """重绘指定航迹的路径线条"""
        # 删除该航迹的旧路径
        old_paths = [p for p in self._map_paths if hasattr(p, '_trk_index') and p._trk_index == trk_index]
        for p in old_paths:
            p.delete()
            self._map_paths.remove(p)
        # 重新创建路径
        tracks = self.gpx_handler.get_tracks()
        if 0 <= trk_index < len(tracks):
            track = tracks[trk_index]
            for si, segment in enumerate(track.segments):
                valid_points = [(pi, p) for pi, p in enumerate(segment.points)
                                if p.latitude is not None and p.longitude is not None]
                if len(valid_points) >= 2:
                    coords = [(p.latitude, p.longitude) for _, p in valid_points]
                    path = self.map_widget.set_path(coords, color="green", width=2)
                    path._trk_index = trk_index
                    self._map_paths.append(path)

    # ========== 航点marker交互 ==========

    # 默认marker颜色
    _MARKER_COLOR_DEFAULT_CIRCLE = "#9B261E"
    _MARKER_COLOR_DEFAULT_OUTSIDE = "#C5542D"
    # 选中marker颜色
    _MARKER_COLOR_SELECTED_CIRCLE = "#E8430E"
    _MARKER_COLOR_SELECTED_OUTSIDE = "#FF6B35"

    def _set_marker_color(self, index, circle_color, outside_color):
        """直接修改marker的canvas对象颜色（不删除/重建）"""
        if index < 0 or index >= len(self._map_markers):
            return
        marker = self._map_markers[index]
        marker.marker_color_circle = circle_color
        marker.marker_color_outside = outside_color
        canvas = self.map_widget.canvas
        if marker.polygon:
            canvas.itemconfigure(marker.polygon, fill=outside_color, outline=outside_color)
        if marker.big_circle:
            canvas.itemconfigure(marker.big_circle, fill=circle_color, outline=outside_color)

    def _highlight_marker(self, index):
        """高亮指定索引的marker"""
        self._set_marker_color(index, self._MARKER_COLOR_SELECTED_CIRCLE, self._MARKER_COLOR_SELECTED_OUTSIDE)

    def _unhighlight_marker(self, index):
        """取消指定索引marker的高亮"""
        self._set_marker_color(index, self._MARKER_COLOR_DEFAULT_CIRCLE, self._MARKER_COLOR_DEFAULT_OUTSIDE)

    def _clear_all_selections(self):
        """清除所有选中状态"""
        self._syncing_selection = True
        try:
            for idx in list(self._selected_waypoints):
                self._unhighlight_marker(idx)
            self._selected_waypoints.clear()
            # 清除航迹点选中
            for key in list(self._selected_track_points):
                self._unhighlight_track_dot(key)
            self._selected_track_points.clear()
            self.tree.selection_set()
        finally:
            self._syncing_selection = False
        self.status_label.config(text="就绪")
        self._clear_selection_graphics()

    def _select_all_waypoints(self):
        """全选所有航点和航迹点"""
        self._clear_all_selections()
        self._syncing_selection = True
        try:
            waypoints = self.gpx_handler.get_waypoints()
            for i in range(len(waypoints)):
                self._selected_waypoints.add(i)
                self._highlight_marker(i)
                self.tree.selection_add(f"wpt_{i}")
            # 全选航迹点
            for dot_id, ti, si, pi in self._track_point_dots:
                key = (ti, si, pi)
                self._selected_track_points.add(key)
                self._highlight_track_dot(key)
        finally:
            self._syncing_selection = False
        self._update_selection_status()

    def _bind_marker_click(self, marker, index):
        """为marker绑定点击选中和右键菜单"""
        items = self._get_marker_canvas_items(marker)
        for item in items:
            self.map_widget.canvas.tag_bind(
                item, '<Button-1>',
                lambda e, idx=index: self._on_marker_click(idx))
            self.map_widget.canvas.tag_bind(
                item, '<Button-3>',
                lambda e, m=marker, idx=index: self._on_marker_right_click(e, m, idx))

    def _get_marker_canvas_items(self, marker):
        """获取marker的canvas元素列表"""
        items = []
        for attr in ('polygon', 'big_circle', 'canvas_text', 'canvas_icon', 'canvas_image'):
            item = getattr(marker, attr, None)
            if item:
                items.append(item)
        return items

    def _on_marker_click(self, index):
        """点击marker - 选中/取消选中航点"""
        self._marker_clicked = True
        self._syncing_selection = True
        try:
            if index in self._selected_waypoints:
                self._selected_waypoints.discard(index)
                self._unhighlight_marker(index)
                self.tree.selection_remove(f"wpt_{index}")
            else:
                self._selected_waypoints.add(index)
                self._highlight_marker(index)
                self.tree.selection_set(f"wpt_{index}")
                self.tree.see(f"wpt_{index}")
        finally:
            self._syncing_selection = False
        self._update_selection_status()

    def _on_marker_right_click(self, event, marker, index):
        """航点marker右键菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑航点", command=lambda: self.edit_waypoint(index))
        menu.add_command(label="移动航点...", command=lambda: self._ctx_wpt_move_by_index(index))
        menu.add_command(label="拖拽移动", command=lambda: self._enable_marker_drag(marker, index))
        menu.add_separator()
        menu.add_command(label="删除此航点", command=lambda: self._delete_waypoint_by_index(index))
        menu.post(event.x_root, event.y_root)

    def _ctx_wpt_move_by_index(self, index):
        """通过对话框移动航点"""
        self._ctx_wpt_index = index
        self._ctx_wpt_move()

    def _enable_marker_drag(self, marker, index):
        """启用航点marker拖拽模式"""
        self._drag_mode = True
        self._drag_target = marker
        self._drag_index = index
        self._drag_data = {}
        self.map_widget.canvas.config(cursor="fleur")
        wpt = self.gpx_handler.get_waypoints()[index]
        self.status_label.config(
            text=f"拖拽模式: {wpt.name or f'航点{index+1}'} — 按住左键拖拽移动，完成后自动退出")

    def _disable_drag_mode(self):
        """退出拖拽模式"""
        self._drag_mode = False
        self._drag_target = None
        self._drag_data = {}
        self._drag_index = -1
        self.map_widget.canvas.config(cursor="")

    # 全局地图鼠标事件（在 _create_main_layout 中绑定）
    def _on_map_press(self, event):
        """地图鼠标按下"""
        if not getattr(self, '_drag_mode', False):
            return
        marker = self._drag_target
        if not marker:
            return
        # 检查点击位置是否在marker附近
        try:
            cx, cy = marker.get_canvas_pos(marker.position)
            dist_sq = (event.x - cx) ** 2 + (event.y - cy) ** 2
            if dist_sq > 900:  # 30px半径
                return
        except Exception:
            return
        self._drag_data = {
            'start_pos': marker.position,
            'canvas_start': (event.x, event.y),
            'active': True,
            'threshold_met': False
        }

    def _on_map_motion(self, event):
        """地图鼠标移动"""
        if not getattr(self, '_drag_mode', False):
            return
        if not self._drag_data.get('active'):
            return
        marker = self._drag_target
        if not marker:
            return
        sx, sy = self._drag_data['canvas_start']
        dx = event.x - sx
        dy = event.y - sy
        if dx * dx + dy * dy > 25:
            self._drag_data['threshold_met'] = True
        if self._drag_data['threshold_met']:
            try:
                lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
                marker.set_position(lat, lon)
            except Exception:
                pass

    def _on_map_release(self, event):
        """地图鼠标释放"""
        if not getattr(self, '_drag_mode', False):
            return
        if not self._drag_data.get('active'):
            return
        marker = self._drag_target
        index = self._drag_index
        if not marker or index < 0:
            self._disable_drag_mode()
            return

        if self._drag_data.get('threshold_met'):
            new_lat, new_lon = marker.position
            waypoints = self.gpx_handler.get_waypoints()
            if 0 <= index < len(waypoints):
                wpt = waypoints[index]
                old_lat, old_lon = wpt.latitude, wpt.longitude
                wpt.latitude = new_lat
                wpt.longitude = new_lon
                self.undo_manager.push({
                    'type': 'move_waypoint',
                    'data': {'index': index, 'lat': new_lat, 'lon': new_lon},
                    'reverse_data': {'index': index, 'lat': old_lat, 'lon': old_lon}
                })
                self._populate_tree()
                self._mark_modified()
                self.status_label.config(
                    text=f"已移动航点: {wpt.name or f'航点{index+1}'} ({new_lat:.6f}, {new_lon:.6f})")
        else:
            # 未超过阈值，视为点击
            self._on_marker_click(index)

        self._disable_drag_mode()
        self.status_label.config(text="拖拽完成")

    # ========== 航迹点拖拽 ==========

    def _bind_track_point_drag(self, marker, trk_index, seg_index, pt_index):
        """为航迹点marker绑定拖拽和右键删除事件"""
        items = []
        for attr in ('polygon', 'big_circle', 'canvas_text', 'canvas_icon', 'canvas_image'):
            item = getattr(marker, attr, None)
            if item:
                items.append(item)

        for item in items:
            self.map_widget.canvas.tag_bind(
                item, '<ButtonPress-1>',
                lambda e, m=marker, ti=trk_index, si=seg_index, pi=pt_index:
                    self._on_track_point_press(m, ti, si, pi, e))
            self.map_widget.canvas.tag_bind(
                item, '<B1-Motion>',
                lambda e, m=marker, ti=trk_index, si=seg_index, pi=pt_index:
                    self._on_track_point_motion(m, ti, si, pi, e))
            self.map_widget.canvas.tag_bind(
                item, '<ButtonRelease-1>',
                lambda e, m=marker, ti=trk_index, si=seg_index, pi=pt_index:
                    self._on_track_point_release(m, ti, si, pi, e))
            self.map_widget.canvas.tag_bind(
                item, '<Button-3>',
                lambda e, ti=trk_index, si=seg_index, pi=pt_index:
                    self._on_track_point_right_click(e, ti, si, pi))

    def _on_track_point_press(self, marker, trk_index, seg_index, pt_index, event):
        """航迹点鼠标按下 - 记录拖拽起始位置"""
        self._dragging_track_marker = marker
        self._track_drag_data = {
            'start_pos': marker.position,
            'canvas_start': (event.x, event.y),
            'trk_index': trk_index,
            'seg_index': seg_index,
            'pt_index': pt_index,
            'threshold_met': False
        }

    def _on_track_point_motion(self, marker, trk_index, seg_index, pt_index, event):
        """航迹点鼠标移动 - 超过阈值后拖拽"""
        if self._dragging_track_marker != marker or not self._track_drag_data:
            return

        sx, sy = self._track_drag_data['canvas_start']
        dx = event.x - sx
        dy = event.y - sy
        if dx * dx + dy * dy > 25:
            self._track_drag_data['threshold_met'] = True

        if self._track_drag_data['threshold_met']:
            try:
                lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
                marker.set_position(lat, lon)
            except Exception:
                pass

    def _on_track_point_release(self, marker, trk_index, seg_index, pt_index, event):
        """航迹点鼠标释放 - 完成拖拽"""
        if self._dragging_track_marker != marker:
            self._dragging_track_marker = None
            self._track_drag_data = {}
            return

        if self._track_drag_data.get('threshold_met'):
            new_lat, new_lon = marker.position
            tracks = self.gpx_handler.get_tracks()
            if 0 <= trk_index < len(tracks):
                track = tracks[trk_index]
                if 0 <= seg_index < len(track.segments):
                    segment = track.segments[seg_index]
                    if 0 <= pt_index < len(segment.points):
                        point = segment.points[pt_index]
                        old_lat, old_lon = point.latitude, point.longitude
                        point.latitude = new_lat
                        point.longitude = new_lon
                        self.undo_manager.push({
                            'type': 'move_track_point',
                            'data': {
                                'trk_index': trk_index,
                                'seg_index': seg_index,
                                'pt_index': pt_index,
                                'lat': new_lat, 'lon': new_lon
                            },
                            'reverse_data': {
                                'trk_index': trk_index,
                                'seg_index': seg_index,
                                'pt_index': pt_index,
                                'lat': old_lat, 'lon': old_lon
                            }
                        })
                        self._update_map()
                        self._mark_modified()
                        self.status_label.config(
                            text=f"已移动航迹点 ({new_lat:.6f}, {new_lon:.6f})")

        self._dragging_track_marker = None
        self._track_drag_data = {}

    def _on_track_point_right_click(self, event, trk_index, seg_index, pt_index):
        """航迹点右键 - 显示删除菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="删除航迹点",
            command=lambda: self._delete_track_point(trk_index, seg_index, pt_index))
        menu.post(event.x_root, event.y_root)

    def _delete_track_point(self, trk_index, seg_index, pt_index):
        """删除指定航迹点"""
        tracks = self.gpx_handler.get_tracks()
        if 0 <= trk_index < len(tracks):
            track = tracks[trk_index]
            if 0 <= seg_index < len(track.segments):
                segment = track.segments[seg_index]
                if 0 <= pt_index < len(segment.points):
                    point = segment.points[pt_index]
                    old_lat, old_lon = point.latitude, point.longitude
                    segment.points.pop(pt_index)
                    self.undo_manager.push({
                        'type': 'delete_track_point',
                        'data': {
                            'trk_index': trk_index,
                            'seg_index': seg_index,
                            'pt_index': pt_index,
                            'lat': old_lat, 'lon': old_lon
                        },
                        'reverse_data': {
                            'trk_index': trk_index,
                            'seg_index': seg_index,
                            'pt_index': pt_index,
                            'lat': old_lat, 'lon': old_lon
                        }
                    })
                    self._update_map()
                    self._mark_modified()
                    self.status_label.config(
                        text=f"已删除航迹点 ({old_lat:.6f}, {old_lon:.6f})")

    # ========== 地图双击插入航迹点 ==========

    def _on_map_double_click(self, event):
        """地图双击 - 在最近的航迹边上插入航迹点"""
        try:
            lat, lon = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
        except Exception:
            return

        tracks = self.gpx_handler.get_tracks()
        if not tracks:
            return

        # 查找距离点击位置最近的航迹边
        best_dist = float('inf')
        best_trk = -1
        best_seg = -1
        best_insert_idx = -1

        for ti, track in enumerate(tracks):
            for si, segment in enumerate(track.segments):
                pts = segment.points
                for i in range(len(pts) - 1):
                    p1 = pts[i]
                    p2 = pts[i + 1]
                    if (p1.latitude is None or p1.longitude is None or
                            p2.latitude is None or p2.longitude is None):
                        continue
                    # 计算点到线段的近似距离（用中点距离近似）
                    dist = self._point_to_segment_dist(
                        lat, lon, p1.latitude, p1.longitude, p2.latitude, p2.longitude)
                    if dist < best_dist:
                        best_dist = dist
                        best_trk = ti
                        best_seg = si
                        best_insert_idx = i + 1

        if best_trk < 0:
            return

        # 插入新航迹点
        import gpxpy.gpx
        segment = tracks[best_trk].segments[best_seg]
        new_point = gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon)
        segment.points.insert(best_insert_idx, new_point)

        self.undo_manager.push({
            'type': 'insert_track_point',
            'data': {
                'trk_index': best_trk,
                'seg_index': best_seg,
                'pt_index': best_insert_idx,
                'lat': lat, 'lon': lon
            },
            'reverse_data': {
                'trk_index': best_trk,
                'seg_index': best_seg,
                'pt_index': best_insert_idx,
                'lat': lat, 'lon': lon
            }
        })

        self._update_map()
        self._mark_modified()
        self.status_label.config(
            text=f"已插入航迹点 ({lat:.6f}, {lon:.6f})")

    def _point_to_segment_dist(self, px, py, ax, ay, bx, by):
        """计算点(px,py)到线段(ax,ay)-(bx,by)的近似距离（欧氏距离度量）"""
        import math
        dx = bx - ax
        dy = by - ay
        len_sq = dx * dx + dy * dy
        if len_sq == 0:
            return math.sqrt((px - ax) ** 2 + (py - ay) ** 2)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / len_sq))
        proj_x = ax + t * dx
        proj_y = ay + t * dy
        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    # ========== 右键菜单 ==========

    def _create_context_menu(self):
        """创建右键菜单"""
        # 航点右键菜单
        self.wpt_context_menu = tk.Menu(self, tearoff=0)
        self.wpt_context_menu.add_command(label="在地图显示", command=self._ctx_wpt_show_on_map)
        self.wpt_context_menu.add_command(label="航点属性", command=self._ctx_wpt_properties)
        self.wpt_context_menu.add_separator()
        self.wpt_context_menu.add_command(label="复制", command=self._ctx_wpt_copy)
        self.wpt_context_menu.add_command(label="粘贴", command=self._ctx_wpt_paste)
        self.wpt_context_menu.add_command(label="剪切", command=self._ctx_wpt_cut)
        self.wpt_context_menu.add_separator()
        self.wpt_context_menu.add_command(label="移动航点", command=self._ctx_wpt_move)
        self.wpt_context_menu.add_command(label="删除", command=self._ctx_delete_waypoint)

        # 航迹右键菜单
        self.trk_context_menu = tk.Menu(self, tearoff=0)
        self.trk_context_menu.add_command(label="在地图显示", command=self._ctx_trk_show_on_map)
        self.trk_context_menu.add_command(label="航迹属性", command=self._ctx_trk_properties)
        self.trk_context_menu.add_separator()
        self.trk_context_menu.add_command(label="复制", command=self._ctx_trk_copy)
        self.trk_context_menu.add_command(label="粘贴", command=self._ctx_trk_paste)
        self.trk_context_menu.add_command(label="剪切", command=self._ctx_trk_cut)
        self.trk_context_menu.add_separator()
        self.trk_context_menu.add_command(label="航迹操作", command=self.track_operations)
        self.trk_context_menu.add_command(label="删除", command=self._ctx_delete_track)

        # 空白区右键菜单
        self.empty_context_menu = tk.Menu(self, tearoff=0)
        self.empty_context_menu.add_command(label="粘贴", command=self._ctx_paste_here)
        self.empty_context_menu.add_separator()
        self.empty_context_menu.add_command(label="添加航点", command=self.add_waypoint)
        self.empty_context_menu.add_command(label="添加航迹", command=self.add_track)

    def _on_tree_right_click(self, event):
        """树形列表右键点击"""
        # 检查是否点击在列头区域
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            self._show_column_config_popup(event)
            return

        item = self.tree.identify_row(event.y)
        if not item:
            # 更新空白区粘贴状态
            paste_state = NORMAL if self._clipboard else DISABLED
            self.empty_context_menu.entryconfigure("粘贴", state=paste_state)
            self.empty_context_menu.post(event.x_root, event.y_root)
            return

        self.tree.selection_set(item)
        iid = item

        if iid.startswith("wpt_"):
            self._ctx_wpt_index = int(iid.split("_")[1])
            # 更新粘贴状态
            paste_state = NORMAL if self._clipboard and self._clipboard['type'] == 'waypoint' else DISABLED
            self.wpt_context_menu.entryconfigure("粘贴", state=paste_state)
            self.wpt_context_menu.post(event.x_root, event.y_root)
        elif iid.startswith("trk_"):
            self._ctx_trk_index = int(iid.split("_")[1])
            # 更新粘贴状态
            paste_state = NORMAL if self._clipboard and self._clipboard['type'] == 'track' else DISABLED
            self.trk_context_menu.entryconfigure("粘贴", state=paste_state)
            self.trk_context_menu.post(event.x_root, event.y_root)

    # 航点右键菜单方法
    def _ctx_wpt_show_on_map(self):
        """在地图上居中显示航点"""
        if not hasattr(self, '_ctx_wpt_index'):
            return
        wpt = self.gpx_handler.get_waypoints()[self._ctx_wpt_index]
        if wpt.latitude and wpt.longitude:
            self.map_widget.set_position(wpt.latitude, wpt.longitude)
            self.map_widget.set_zoom(15)

    def _ctx_wpt_properties(self):
        """打开航点属性对话框"""
        if not hasattr(self, '_ctx_wpt_index'):
            return
        from .properties_dialog import WaypointPropertiesDialog
        wpt = self.gpx_handler.get_waypoints()[self._ctx_wpt_index]
        dialog = WaypointPropertiesDialog(self, wpt)
        if dialog.result:
            self._populate_tree()
            self._mark_modified()

    def _ctx_wpt_copy(self):
        """复制航点到剪贴板"""
        if not hasattr(self, '_ctx_wpt_index'):
            return
        wpt = self.gpx_handler.get_waypoints()[self._ctx_wpt_index]
        self._clipboard = {'type': 'waypoint', 'data': self._serialize_waypoint(wpt)}
        # 同时复制坐标文本到系统剪贴板
        try:
            self.clipboard_clear()
            self.clipboard_append(f"{wpt.latitude:.6f} {wpt.longitude:.6f}")
        except Exception:
            pass
        self.status_label.config(text=f"已复制航点: {wpt.name}")

    def _ctx_wpt_paste(self):
        """粘贴航点数据到当前选中航点"""
        if not self._clipboard or self._clipboard['type'] != 'waypoint':
            return
        if not hasattr(self, '_ctx_wpt_index'):
            return
        wpt = self.gpx_handler.get_waypoints()[self._ctx_wpt_index]
        self._apply_waypoint_data(wpt, self._clipboard['data'])
        self._populate_tree()
        self._mark_modified()
        self.status_label.config(text="已粘贴航点数据")

    def _ctx_wpt_cut(self):
        """剪切航点"""
        if not hasattr(self, '_ctx_wpt_index'):
            return
        self._ctx_wpt_copy()
        self.delete_waypoint(self._ctx_wpt_index)

    def _ctx_wpt_move(self):
        """移动航点到新位置"""
        if not hasattr(self, '_ctx_wpt_index'):
            return
        from .move_waypoint_dialog import MoveWaypointDialog
        wpt = self.gpx_handler.get_waypoints()[self._ctx_wpt_index]
        dialog = MoveWaypointDialog(self, self.map_widget, wpt)
        if dialog.result:
            old_lat, old_lon = wpt.latitude, wpt.longitude
            new_lat, new_lon = dialog.result
            wpt.latitude = new_lat
            wpt.longitude = new_lon
            self.undo_manager.push({
                'type': 'edit_waypoint',
                'data': {'index': self._ctx_wpt_index, 'lat': new_lat, 'lon': new_lon,
                         'name': wpt.name, 'ele': wpt.elevation, 'desc': wpt.description},
                'reverse_data': {'index': self._ctx_wpt_index, 'lat': old_lat, 'lon': old_lon,
                                 'name': wpt.name, 'ele': wpt.elevation, 'desc': wpt.description}
            })
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已移动航点: {wpt.name}")

    def _ctx_delete_waypoint(self):
        """右键菜单 - 删除航点"""
        if hasattr(self, '_ctx_wpt_index'):
            self.delete_waypoint(self._ctx_wpt_index)

    def _edit_selected_waypoint(self):
        """编辑选中的航点（仅单选时可用）"""
        selected = [s for s in self.tree.selection() if s.startswith("wpt_")]
        if len(selected) != 1:
            messagebox.showinfo("提示", "请先选中一个航点")
            return
        idx = int(selected[0].split("_")[1])
        self.edit_waypoint(idx)

    def _move_selected_waypoint(self):
        """移动选中的航点（支持多选批量移动）"""
        selected = [s for s in self.tree.selection() if s.startswith("wpt_")]
        if not selected:
            messagebox.showinfo("提示", "请先选中航点")
            return
        if len(selected) == 1:
            idx = int(selected[0].split("_")[1])
            self._ctx_wpt_move_by_index(idx)
        else:
            indices = [int(s.split("_")[1]) for s in selected]
            self._batch_move_waypoints(indices)

    def _batch_move_waypoints(self, indices):
        """批量移动航点（偏移方式）"""
        from ..core.gpx_editor import GpxEditor
        dialog = tk.Toplevel(self)
        dialog.title(f"批量移动 {len(indices)} 个航点")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        ttk.Label(main_frame, text=f"将 {len(indices)} 个航点整体偏移：",
                  foreground="#555555").pack(anchor=W, pady=(0, 8))

        offset_frame = ttk.LabelFrame(main_frame, text="偏移量 (米)", padding=8)
        offset_frame.pack(fill=X, pady=(0, 8))

        ttk.Label(offset_frame, text="东西方向 (正=东, 负=西):").grid(row=0, column=0, sticky=W, pady=3)
        x_offset_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=x_offset_var, width=15).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(offset_frame, text="南北方向 (正=北, 负=南):").grid(row=1, column=0, sticky=W, pady=3)
        y_offset_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=y_offset_var, width=15).grid(row=1, column=1, padx=(5, 0))

        quick_frame = ttk.LabelFrame(main_frame, text="快捷偏移", padding=8)
        quick_frame.pack(fill=X, pady=(0, 8))

        def quick_offset(dx, dy):
            try:
                cur_x = float(x_offset_var.get())
            except ValueError:
                cur_x = 0.0
            try:
                cur_y = float(y_offset_var.get())
            except ValueError:
                cur_y = 0.0
            x_offset_var.set(f"{cur_x + dx:.1f}")
            y_offset_var.set(f"{cur_y + dy:.1f}")

        ns_frame = ttk.Frame(quick_frame)
        ns_frame.pack(pady=3)
        ttk.Button(ns_frame, text="北 +10m", width=10, command=lambda: quick_offset(0, 10)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="北 +1m", width=10, command=lambda: quick_offset(0, 1)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="南 -1m", width=10, command=lambda: quick_offset(0, -1)).pack(side=LEFT, padx=2)
        ttk.Button(ns_frame, text="南 -10m", width=10, command=lambda: quick_offset(0, -10)).pack(side=LEFT, padx=2)

        ew_frame = ttk.Frame(quick_frame)
        ew_frame.pack(pady=3)
        ttk.Button(ew_frame, text="西 -10m", width=10, command=lambda: quick_offset(-10, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="西 -1m", width=10, command=lambda: quick_offset(-1, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="东 +1m", width=10, command=lambda: quick_offset(1, 0)).pack(side=LEFT, padx=2)
        ttk.Button(ew_frame, text="东 +10m", width=10, command=lambda: quick_offset(10, 0)).pack(side=LEFT, padx=2)

        result = [False]

        def on_ok():
            try:
                x_m = float(x_offset_var.get())
            except ValueError:
                messagebox.showwarning("提示", "东西方向偏移量格式不正确", parent=dialog)
                return
            try:
                y_m = float(y_offset_var.get())
            except ValueError:
                messagebox.showwarning("提示", "南北方向偏移量格式不正确", parent=dialog)
                return
            if x_m == 0 and y_m == 0:
                messagebox.showinfo("提示", "偏移量为零，航点不会移动", parent=dialog)
                return
            result[0] = True
            waypoints = self.gpx_handler.get_waypoints()
            for idx in indices:
                if 0 <= idx < len(waypoints):
                    wpt = waypoints[idx]
                    if wpt.latitude is not None and wpt.longitude is not None:
                        new_lat, new_lon = GpxEditor.offset_coordinates(
                            wpt.latitude, wpt.longitude, x_m, y_m)
                        old_lat, old_lon = wpt.latitude, wpt.longitude
                        wpt.latitude = new_lat
                        wpt.longitude = new_lon
                        self.undo_manager.push({
                            'type': 'edit_waypoint',
                            'data': {'index': idx, 'lat': new_lat, 'lon': new_lon,
                                     'name': wpt.name, 'ele': wpt.elevation, 'desc': wpt.description},
                            'reverse_data': {'index': idx, 'lat': old_lat, 'lon': old_lon,
                                             'name': wpt.name, 'ele': wpt.elevation, 'desc': wpt.description}
                        })
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已批量移动 {len(indices)} 个航点")
            dialog.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="确定", command=on_ok, bootstyle=PRIMARY, width=10).pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=RIGHT, padx=5)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        dialog.wait_window()
    def _delete_waypoint_by_index(self, index):
        """按索引删除航点"""
        waypoints = self.gpx_handler.get_waypoints()
        if index < 0 or index >= len(waypoints):
            return
        wpt = waypoints[index]
        name = wpt.name or f"航点{index+1}"
        if messagebox.askyesno("确认删除", f"确定要删除航点 {name} 吗？"):
            old_data = {'name': wpt.name, 'lat': wpt.latitude, 'lon': wpt.longitude,
                        'ele': wpt.elevation, 'desc': wpt.description}
            self.gpx_handler.remove_waypoint(index)
            self.undo_manager.push({
                'type': 'delete_waypoint',
                'data': {'index': index},
                'reverse_data': old_data
            })
            self._selected_waypoints.discard(index)
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已删除航点: {name}")

    # 航迹右键菜单方法
    def _ctx_trk_show_on_map(self):
        """缩放地图到航迹范围"""
        if not hasattr(self, '_ctx_trk_index'):
            return
        track = self.gpx_handler.get_tracks()[self._ctx_trk_index]
        bounds = track.get_bounds()
        if bounds:
            self.map_widget.fit_bounding_box(
                (bounds.max_latitude, bounds.min_longitude),
                (bounds.min_latitude, bounds.max_longitude)
            )

    def _ctx_trk_properties(self):
        """打开航迹属性对话框"""
        if not hasattr(self, '_ctx_trk_index'):
            return
        from .properties_dialog import TrackPropertiesDialog
        track = self.gpx_handler.get_tracks()[self._ctx_trk_index]
        dialog = TrackPropertiesDialog(self, track)
        if dialog.result:
            self._populate_tree()
            self._mark_modified()

    def _ctx_trk_copy(self):
        """复制航迹到剪贴板"""
        if not hasattr(self, '_ctx_trk_index'):
            return
        track = self.gpx_handler.get_tracks()[self._ctx_trk_index]
        self._clipboard = {'type': 'track', 'data': self._serialize_track(track)}
        self.status_label.config(text=f"已复制航迹: {track.name}")

    def _ctx_trk_paste(self):
        """粘贴航迹（追加）"""
        if not self._clipboard or self._clipboard['type'] != 'track':
            return
        self._ensure_gpx_loaded()
        track = self._deserialize_track(self._clipboard['data'])
        self.gpx_handler.gpx.tracks.append(track)
        self._populate_tree()
        self._mark_modified()
        self.status_label.config(text=f"已粘贴航迹: {track.name}")

    def _ctx_trk_cut(self):
        """剪切航迹"""
        if not hasattr(self, '_ctx_trk_index'):
            return
        self._ctx_trk_copy()
        self.delete_track(self._ctx_trk_index)

    def _ctx_delete_track(self):
        """右键菜单 - 删除航迹"""
        if hasattr(self, '_ctx_trk_index'):
            self.delete_track(self._ctx_trk_index)

    def _ctx_paste_here(self):
        """在空白区粘贴"""
        if not self._clipboard:
            return
        self._ensure_gpx_loaded()
        if self._clipboard['type'] == 'waypoint':
            wpt = self._deserialize_waypoint(self._clipboard['data'])
            self.gpx_handler.gpx.waypoints.append(wpt)
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text="已粘贴航点")
        elif self._clipboard['type'] == 'track':
            self._ctx_trk_paste()

    # ========== 序列化辅助 ==========

    def _serialize_waypoint(self, wpt):
        """序列化航点数据"""
        return {
            'name': wpt.name, 'latitude': wpt.latitude, 'longitude': wpt.longitude,
            'elevation': wpt.elevation, 'description': wpt.description,
            'comment': wpt.comment, 'symbol': wpt.symbol, 'time': wpt.time,
            'type': wpt.type, 'source': wpt.source,
        }

    def _deserialize_waypoint(self, data):
        """反序列化航点数据"""
        import gpxpy.gpx
        from datetime import datetime
        wpt = gpxpy.gpx.GPXWaypoint(
            latitude=data['latitude'], longitude=data['longitude'],
            elevation=data.get('elevation'), name=data.get('name'),
            description=data.get('description'), time=data.get('time') or datetime.now(),
            comment=data.get('comment'), symbol=data.get('symbol'),
            type=data.get('type'), source=data.get('source'),
        )
        return wpt

    def _serialize_track(self, track):
        """序列化航迹数据"""
        segments = []
        for seg in track.segments:
            points = []
            for p in seg.points:
                points.append({
                    'latitude': p.latitude, 'longitude': p.longitude,
                    'elevation': p.elevation, 'time': p.time,
                })
            segments.append(points)
        return {
            'name': track.name, 'description': track.description,
            'comment': track.comment, 'type': track.type,
            'number': track.number, 'source': track.source,
            'segments': segments,
        }

    def _deserialize_track(self, data):
        """反序列化航迹数据"""
        import gpxpy.gpx
        track = gpxpy.gpx.GPXTrack()
        track.name = data.get('name')
        track.description = data.get('description')
        track.comment = data.get('comment')
        track.type = data.get('type')
        track.number = data.get('number')
        track.source = data.get('source')
        for seg_data in data.get('segments', []):
            seg = gpxpy.gpx.GPXTrackSegment()
            for p in seg_data:
                pt = gpxpy.gpx.GPXTrackPoint(
                    latitude=p['latitude'], longitude=p['longitude'],
                    elevation=p.get('elevation'), time=p.get('time'),
                )
                seg.points.append(pt)
            track.segments.append(seg)
        return track

    def _apply_waypoint_data(self, wpt, data):
        """将序列化数据应用到已有航点"""
        wpt.name = data.get('name')
        wpt.latitude = data.get('latitude')
        wpt.longitude = data.get('longitude')
        wpt.elevation = data.get('elevation')
        wpt.description = data.get('description')
        wpt.comment = data.get('comment')
        wpt.symbol = data.get('symbol')
        wpt.type = data.get('type')
        wpt.source = data.get('source')

    # ========== 键盘快捷键 ==========

    def _keyboard_copy(self):
        """键盘复制"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        if iid.startswith("wpt_"):
            self._ctx_wpt_index = int(iid.split("_")[1])
            self._ctx_wpt_copy()
        elif iid.startswith("trk_"):
            self._ctx_trk_index = int(iid.split("_")[1])
            self._ctx_trk_copy()

    def _keyboard_paste(self):
        """键盘粘贴"""
        selected = self.tree.selection()
        if not selected:
            # 没有选中项，粘贴到空白区
            self._ctx_paste_here()
            return
        iid = selected[0]
        if iid.startswith("wpt_") and self._clipboard and self._clipboard['type'] == 'waypoint':
            self._ctx_wpt_index = int(iid.split("_")[1])
            self._ctx_wpt_paste()
        elif iid.startswith("trk_") and self._clipboard and self._clipboard['type'] == 'track':
            self._ctx_trk_index = int(iid.split("_")[1])
            self._ctx_trk_paste()

    def _keyboard_cut(self):
        """键盘剪切"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        if iid.startswith("wpt_"):
            self._ctx_wpt_index = int(iid.split("_")[1])
            self._ctx_wpt_cut()
        elif iid.startswith("trk_"):
            self._ctx_trk_index = int(iid.split("_")[1])
            self._ctx_trk_cut()

    # ========== 删除 ==========

    def _delete_selected(self):
        """删除选中项"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        if iid.startswith("wpt_"):
            index = int(iid.split("_")[1])
            self.delete_waypoint(index)
        elif iid.startswith("trk_"):
            index = int(iid.split("_")[1])
            self.delete_track(index)

    # ========== 撤销/重做 ==========

    def undo(self):
        """撤销"""
        cmd = self.undo_manager.undo()
        if cmd:
            self._execute_undo_command(cmd, is_redo=False)
            self.status_label.config(text="已撤销")

    def redo(self):
        """重做"""
        cmd = self.undo_manager.redo()
        if cmd:
            self._execute_undo_command(cmd, is_redo=True)
            self.status_label.config(text="已重做")

    def _execute_undo_command(self, cmd, is_redo=False):
        """执行撤销/重做命令"""
        cmd_type = cmd['type']

        if cmd_type == 'add_waypoint':
            if is_redo:
                data = cmd['data']
                self.gpx_handler.add_waypoint(data['name'], data['lat'], data['lon'], data.get('ele'), data.get('desc'))
            else:
                self.gpx_handler.remove_waypoint(cmd['reverse_data']['index'])

        elif cmd_type == 'delete_waypoint':
            if is_redo:
                self.gpx_handler.remove_waypoint(cmd['data']['index'])
            else:
                data = cmd['reverse_data']
                self.gpx_handler.add_waypoint(data['name'], data['lat'], data['lon'], data.get('ele'), data.get('desc'))

        elif cmd_type == 'edit_waypoint':
            wpt = self.gpx_handler.get_waypoints()[cmd['data']['index']]
            data = cmd['data'] if is_redo else cmd['reverse_data']
            wpt.name = data['name']
            wpt.latitude = data['lat']
            wpt.longitude = data['lon']
            wpt.elevation = data.get('ele')
            wpt.description = data.get('desc')

        elif cmd_type == 'move_waypoint':
            wpt = self.gpx_handler.get_waypoints()[cmd['data']['index']]
            data = cmd['data'] if is_redo else cmd['reverse_data']
            wpt.latitude = data['lat']
            wpt.longitude = data['lon']

        elif cmd_type == 'move_track_point':
            track = self.gpx_handler.get_tracks()[cmd['data']['trk_index']]
            point = track.segments[cmd['data']['seg_index']].points[cmd['data']['pt_index']]
            data = cmd['data'] if is_redo else cmd['reverse_data']
            point.latitude = data['lat']
            point.longitude = data['lon']

        elif cmd_type == 'insert_track_point':
            import gpxpy.gpx
            track = self.gpx_handler.get_tracks()[cmd['data']['trk_index']]
            segment = track.segments[cmd['data']['seg_index']]
            if is_redo:
                new_point = gpxpy.gpx.GPXTrackPoint(
                    latitude=cmd['data']['lat'], longitude=cmd['data']['lon'])
                segment.points.insert(cmd['data']['pt_index'], new_point)
            else:
                segment.points.pop(cmd['data']['pt_index'])

        elif cmd_type == 'delete_track_point':
            import gpxpy.gpx
            track = self.gpx_handler.get_tracks()[cmd['data']['trk_index']]
            segment = track.segments[cmd['data']['seg_index']]
            if is_redo:
                segment.points.pop(cmd['data']['pt_index'])
            else:
                new_point = gpxpy.gpx.GPXTrackPoint(
                    latitude=cmd['data']['lat'], longitude=cmd['data']['lon'])
                segment.points.insert(cmd['data']['pt_index'], new_point)

        self._populate_tree()
        self._update_map()
        self._mark_modified()

    # ========== 状态标记 ==========

    def _mark_modified(self):
        """标记文件已修改"""
        self.is_modified = True
        title = self.title()
        if not title.endswith("*"):
            self.title(title + " *")

    def _clear_modified(self):
        """清除修改标记"""
        self.is_modified = False
        title = self.title()
        if title.endswith(" *"):
            self.title(title[:-2])

    def _on_close(self):
        """窗口关闭事件"""
        if self.is_modified:
            result = messagebox.askyesnocancel("保存确认", "文件已修改，是否保存？")
            if result is True:
                self.save_file()
            elif result is None:
                return
        self.destroy()

    # ========== 文件操作 ==========

    def new_file(self):
        """新建文件"""
        if self.is_modified:
            result = messagebox.askyesnocancel("保存确认", "文件已修改，是否保存？")
            if result is True:
                self.save_file()
            elif result is None:
                return

        self.gpx_handler.new()
        self.current_file = None
        self._populate_tree()
        self.file_label.config(text="未打开文件")
        self.status_label.config(text="已新建空白文件")
        self._clear_modified()

    def open_file(self):
        """打开文件"""
        if self.is_modified:
            result = messagebox.askyesnocancel("保存确认", "文件已修改，是否保存？")
            if result is True:
                self.save_file()
            elif result is None:
                return

        filetypes = [("GPX文件", "*.gpx"), ("所有文件", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            try:
                self.gpx_handler.load(filepath)
                self.current_file = filepath
                self._populate_tree()
                self.file_label.config(text=filepath)
                self.status_label.config(text="已打开文件")
                self._clear_modified()
            except Exception as e:
                messagebox.showerror("打开失败", f"无法打开文件:\n{e}")

    def save_file(self):
        """保存文件"""
        if self.current_file:
            try:
                self.gpx_handler.save(self.current_file)
                self.status_label.config(text="已保存")
                self._clear_modified()
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件:\n{e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        """另存为"""
        filetypes = [("GPX文件", "*.gpx")]
        filepath = filedialog.asksaveasfilename(defaultextension=".gpx", filetypes=filetypes)
        if filepath:
            try:
                self.gpx_handler.save(filepath)
                self.current_file = filepath
                self.file_label.config(text=filepath)
                self.status_label.config(text="已保存")
                self._clear_modified()
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件:\n{e}")

    def _ensure_gpx_loaded(self):
        """确保已有GPX数据，没有则新建"""
        if self.gpx_handler.gpx is None:
            self.gpx_handler.new()

    # ========== 航点/航迹操作 ==========

    def add_waypoint(self):
        """添加航点"""
        from .waypoint_dialog import WaypointDialog
        self._ensure_gpx_loaded()
        dialog = WaypointDialog(self)
        if dialog.result:
            name, lat, lon, ele, desc = dialog.result
            self.gpx_handler.add_waypoint(name, lat, lon, ele, desc)
            index = len(self.gpx_handler.get_waypoints()) - 1
            self.undo_manager.push({
                'type': 'add_waypoint',
                'data': {'name': name, 'lat': lat, 'lon': lon, 'ele': ele, 'desc': desc},
                'reverse_data': {'index': index}
            })
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已添加航点: {name}")

    def edit_waypoint(self, index):
        """编辑航点"""
        from .waypoint_dialog import WaypointDialog
        waypoints = self.gpx_handler.get_waypoints()
        if 0 <= index < len(waypoints):
            wpt = waypoints[index]
            old_data = {'name': wpt.name, 'lat': wpt.latitude, 'lon': wpt.longitude,
                        'ele': wpt.elevation, 'desc': wpt.description}
            dialog = WaypointDialog(self, waypoint=wpt)
            if dialog.result:
                name, lat, lon, ele, desc = dialog.result
                new_data = {'name': name, 'lat': lat, 'lon': lon, 'ele': ele, 'desc': desc}
                wpt.name = name
                wpt.latitude = lat
                wpt.longitude = lon
                wpt.elevation = ele
                wpt.description = desc
                self.undo_manager.push({
                    'type': 'edit_waypoint',
                    'data': {'index': index, **new_data},
                    'reverse_data': {'index': index, **old_data}
                })
                self._populate_tree()
                self._mark_modified()
                self.status_label.config(text=f"已修改航点: {name}")

    def delete_waypoint(self, index):
        """删除航点"""
        waypoints = self.gpx_handler.get_waypoints()
        if 0 <= index < len(waypoints):
            wpt = waypoints[index]
            name = wpt.name or f"航点{index+1}"
            if messagebox.askyesno("确认删除", f"确定要删除航点 \"{name}\" 吗？"):
                old_data = {'name': wpt.name, 'lat': wpt.latitude, 'lon': wpt.longitude,
                            'ele': wpt.elevation, 'desc': wpt.description}
                self.gpx_handler.remove_waypoint(index)
                self.undo_manager.push({
                    'type': 'delete_waypoint',
                    'data': {'index': index},
                    'reverse_data': old_data
                })
                self._populate_tree()
                self._mark_modified()
                self.status_label.config(text=f"已删除航点: {name}")

    def add_track(self):
        """添加航迹"""
        from .track_dialog import TrackDialog
        self._ensure_gpx_loaded()
        dialog = TrackDialog(self)
        if dialog.result:
            name = dialog.result
            self.gpx_handler.add_track(name, [])
            self._populate_tree()
            self._mark_modified()
            self.status_label.config(text=f"已添加航迹: {name}")

    def edit_track(self, index):
        """编辑航迹"""
        from .track_dialog import TrackDialog
        tracks = self.gpx_handler.get_tracks()
        if 0 <= index < len(tracks):
            track = tracks[index]
            dialog = TrackDialog(self, track=track)
            if dialog.result:
                track.name = dialog.result
                self._populate_tree()
                self._mark_modified()
                self.status_label.config(text=f"已修改航迹: {track.name}")

    def delete_track(self, index):
        """删除航迹"""
        tracks = self.gpx_handler.get_tracks()
        if 0 <= index < len(tracks):
            name = tracks[index].name or f"航迹{index+1}"
            if messagebox.askyesno("确认删除", f"确定要删除航迹 \"{name}\" 吗？"):
                self.gpx_handler.remove_track(index)
                self._populate_tree()
                self._mark_modified()
                self.status_label.config(text=f"已删除航迹: {name}")

    # ========== 工具菜单 ==========

    def export_txt(self):
        """导出TXT"""
        from .batch_export_dialog import SingleExportDialog
        SingleExportDialog.export_txt(self)

    def export_gdb(self):
        """导出GDB"""
        from .batch_export_dialog import SingleExportDialog
        SingleExportDialog.export_gdb(self)

    def batch_export_txt(self):
        """批量导出TXT"""
        from .batch_export_dialog import BatchExportDialog
        BatchExportDialog(self, export_type="txt")

    def batch_export_gdb(self):
        """批量导出GDB"""
        from .batch_export_dialog import BatchExportDialog
        BatchExportDialog(self, export_type="gdb")

    def export_waypoints_to_excel(self):
        """导出航点到Excel"""
        current_file = getattr(self, 'current_file', None)
        ExcelExportDialog(self, initial_file=current_file)

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

    def track_operations(self):
        """打开航迹操作对话框"""
        if not self.gpx_handler.get_tracks():
            messagebox.showinfo("提示", "没有可操作的航迹，请先打开包含航迹的GPX文件")
            return
        from .track_operations_dialog import TrackOperationsDialog
        dialog = TrackOperationsDialog(self)
        if dialog.result:
            self._populate_tree()
            self._mark_modified()

    def verify_three_way(self):
        """打开三方数据校验对话框"""
        from .verification_dialog import VerificationDialog
        VerificationDialog(self)
