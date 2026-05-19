# 地图框选航点功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在地图视图上方添加工具栏，支持矩形框选和任意框选航点，选中航点可通过编辑菜单操作

**Architecture:** 全部在 `main_window.py` 中实现。添加工具栏Frame管理三种工具状态（手型/矩形/任意），通过canvas事件处理框选逻辑，marker通过delete+重建实现颜色切换高亮，选中状态与树形列表双向同步。

**Tech Stack:** Python, tkinter, ttkbootstrap, tkintermapview

---

### Task 1: 添加状态变量和工具栏UI

**Files:**
- Modify: `gpx_editor/gui/main_window.py:40-52` (状态变量初始化)
- Modify: `gpx_editor/gui/main_window.py:175-181` (工具栏布局)

- [ ] **Step 1: 添加状态变量**

在 `__init__` 方法中（第 52 行 `self._track_point_markers` 之后）添加：

```python
        # 地图工具和选中状态
        self._map_tool = "hand"              # 当前工具: "hand" / "rect" / "lasso"
        self._selected_waypoints = set()     # 选中的航点索引集合
        self._selection_rect_id = None       # 矩形框选canvas对象ID
        self._selection_lasso_id = None      # 任意框选canvas对象ID
        self._selection_points = []          # 框选过程中的坐标点列表
        self._selection_start_x = 0          # 框选起点x
        self._selection_start_y = 0          # 框选起点y
```

- [ ] **Step 2: 添加工具栏UI**

在 `_create_main_layout` 方法中，地图组件创建之前（第 179 行 `# 地图组件 - 天地图` 之前），插入工具栏：

```python
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
```

- [ ] **Step 3: 运行程序验证工具栏显示**

Run: `python main.py`
预期：地图上方出现三个按钮（手型、矩形、任意）

- [ ] **Step 4: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 添加地图工具栏UI和选中状态变量"
```

---

### Task 2: 实现工具切换逻辑

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (新增 `_set_map_tool` 和 `_update_tool_buttons` 方法)

在 `_toggle_satellite` 方法之前（约第 438 行 `# ========== 地图 ==========` 之后），添加：

- [ ] **Step 1: 实现工具切换方法**

```python
    def _set_map_tool(self, tool):
        """切换地图工具"""
        self._clear_selection_graphics()
        self._map_tool = tool
        self._update_tool_buttons()
        if tool == "hand":
            self.map_widget.canvas.config(cursor="arrow")
        else:
            self.map_widget.canvas.config(cursor="crosshair")

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
```

- [ ] **Step 2: 运行程序验证工具切换**

Run: `python main.py`
操作：点击三个工具按钮
预期：
- 按钮高亮状态正确切换
- 鼠标光标在手型时为箭头，矩形和任意时为十字

- [ ] **Step 3: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现地图工具切换逻辑"
```

---

### Task 3: 实现Marker高亮/取消高亮

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (新增 `_highlight_marker` 和 `_unhighlight_marker` 方法)

- [ ] **Step 1: 实现marker高亮方法**

在 `_bind_marker_click` 方法之前（约第 653 行 `# ========== 航点marker交互 ==========` 之后），添加：

```python
    # 默认marker颜色
    _MARKER_COLOR_DEFAULT_CIRCLE = "#9B261E"
    _MARKER_COLOR_DEFAULT_OUTSIDE = "#C5542D"
    # 选中marker颜色
    _MARKER_COLOR_SELECTED_CIRCLE = "#E8430E"
    _MARKER_COLOR_SELECTED_OUTSIDE = "#FF6B35"

    def _highlight_marker(self, index):
        """高亮指定索引的marker"""
        if index < 0 or index >= len(self._map_markers):
            return
        marker = self._map_markers[index]
        # 修改颜色属性
        marker.marker_color_circle = self._MARKER_COLOR_SELECTED_CIRCLE
        marker.marker_color_outside = self._MARKER_COLOR_SELECTED_OUTSIDE
        # 重新绘制: 删除旧canvas对象，重建
        self.map_widget.canvas.delete(marker.polygon)
        self.map_widget.canvas.delete(marker.big_circle)
        self.map_widget.canvas.delete(marker.canvas_text)
        if hasattr(marker, 'canvas_icon') and marker.canvas_icon:
            self.map_widget.canvas.delete(marker.canvas_icon)
        if hasattr(marker, 'canvas_image') and marker.canvas_image:
            self.map_widget.canvas.delete(marker.canvas_image)
        marker.draw()
        # 重新绑定事件
        self._bind_marker_click(marker, index)

    def _unhighlight_marker(self, index):
        """取消指定索引marker的高亮"""
        if index < 0 or index >= len(self._map_markers):
            return
        marker = self._map_markers[index]
        marker.marker_color_circle = self._MARKER_COLOR_DEFAULT_CIRCLE
        marker.marker_color_outside = self._MARKER_COLOR_DEFAULT_OUTSIDE
        self.map_widget.canvas.delete(marker.polygon)
        self.map_widget.canvas.delete(marker.big_circle)
        self.map_widget.canvas.delete(marker.canvas_text)
        if hasattr(marker, 'canvas_icon') and marker.canvas_icon:
            self.map_widget.canvas.delete(marker.canvas_icon)
        if hasattr(marker, 'canvas_image') and marker.canvas_image:
            self.map_widget.canvas.delete(marker.canvas_image)
        marker.draw()
        self._bind_marker_click(marker, index)

    def _clear_all_selections(self):
        """清除所有选中状态"""
        for idx in list(self._selected_waypoints):
            self._unhighlight_marker(idx)
        self._selected_waypoints.clear()
        self.tree.selection_set()
        self.status_label.config(text="就绪")
        self._clear_selection_graphics()
```

- [ ] **Step 2: 运行程序验证marker重建无异常**

Run: `python main.py`
操作：打开一个GPX文件，确认地图上marker正常显示
预期：marker正常显示，无异常

- [ ] **Step 3: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现marker高亮和取消高亮方法"
```

---

### Task 4: 实现点击选中交互

**Files:**
- Modify: `gpx_editor/gui/main_window.py:675-678` (修改 `_on_marker_click`)
- Modify: `gpx_editor/gui/main_window.py:188-194` (修改鼠标事件绑定)

- [ ] **Step 1: 修改 `_on_marker_click` 方法**

替换现有的 `_on_marker_click` 方法（第 675-678 行）：

```python
    def _on_marker_click(self, index):
        """点击marker - 选中/取消选中航点"""
        if index in self._selected_waypoints:
            # 已选中则取消
            self._selected_waypoints.discard(index)
            self._unhighlight_marker(index)
            self.tree.selection_remove(f"wpt_{index}")
        else:
            # 未选中则选中
            self._selected_waypoints.add(index)
            self._highlight_marker(index)
            self.tree.selection_set(f"wpt_{index}")
            self.tree.see(f"wpt_{index}")
        self._update_selection_status()
```

- [ ] **Step 2: 修改鼠标事件绑定**

替换现有的鼠标事件绑定（第 188-194 行）为：

```python
        # 地图鼠标事件
        self.map_widget.canvas.bind("<Motion>", self._on_map_mouse_move)
        self.map_widget.canvas.bind("<Double-1>", self._on_map_double_click)
        # 统一的鼠标事件处理（工具栏模式）
        self.map_widget.canvas.bind("<ButtonPress-1>", self._on_tool_press, add=True)
        self.map_widget.canvas.bind("<B1-Motion>", self._on_tool_drag, add=True)
        self.map_widget.canvas.bind("<ButtonRelease-1>", self._on_tool_release, add=True)
```

- [ ] **Step 3: 实现统一的工具事件分发方法**

在 `_toggle_satellite` 方法之前添加：

```python
    def _on_tool_press(self, event):
        """工具模式下的鼠标按下"""
        if self._drag_mode:
            # 拖拽模式优先处理
            self._on_map_press(event)
            return
        if self._map_tool == "hand":
            # 手型模式: 由tkintermapview处理平移，点击空白取消选中
            # 延迟判断：在release时判断是否点击了空白
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
        if self._map_tool == "rect":
            # 绘制矩形框选
            if self._selection_rect_id:
                self.map_widget.canvas.delete(self._selection_rect_id)
            self._selection_rect_id = self.map_widget.canvas.create_rectangle(
                self._selection_start_x, self._selection_start_y,
                event.x, event.y,
                outline="#3399ff", width=2,
                fill="#3399ff", stipple="gray25"
            )
        elif self._map_tool == "lasso":
            # 收集路径点并绘制线条
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
        if self._map_tool == "hand":
            # 判断是否为点击（未移动）且未点中marker
            dx = abs(event.x - self._selection_start_x)
            dy = abs(event.y - self._selection_start_y)
            if dx < 5 and dy < 5:
                # 检查是否点击了marker（marker的tag_bind会先触发）
                # 如果点击了空白区域，清除选中
                self.root.after(10, self._check_clear_selection)
        elif self._map_tool == "rect":
            self._finish_rect_selection(event)
        elif self._map_tool == "lasso":
            self._finish_lasso_selection(event)

    def _check_clear_selection(self):
        """检查是否需要清除选中（点击空白区域时）"""
        # 如果在手型模式下，没有新的marker被点击，则清除选中
        # 这个方法通过延迟执行，让marker点击事件先处理
        pass  # 由 _on_marker_click 负责选中逻辑，此处不需要额外操作

    def _update_selection_status(self):
        """更新状态栏的选中信息"""
        count = len(self._selected_waypoints)
        if count == 0:
            self.status_label.config(text="就绪")
        elif count == 1:
            idx = next(iter(self._selected_waypoints))
            wpt = self.gpx_handler.get_waypoints()[idx]
            name = wpt.name or f"航点{idx+1}"
            self.status_label.config(
                text=f"已选中：{name} ({wpt.latitude:.6f}, {wpt.longitude:.6f})")
        else:
            self.status_label.config(text=f"已选中 {count} 个航点")
```

- [ ] **Step 4: 运行程序测试点击选中**

Run: `python main.py`
操作：打开GPX文件，用手型工具点击地图上的marker
预期：
- 点击marker后marker变色（红色/橙色高亮）
- 左侧树形列表对应行高亮
- 状态栏显示选中信息
- 再次点击同一marker取消选中

- [ ] **Step 5: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现地图点击选中航点交互"
```

---

### Task 5: 实现矩形框选

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (添加 `_finish_rect_selection` 方法)

- [ ] **Step 1: 实现矩形框选完成方法**

在 `_on_tool_release` 方法之后添加：

```python
    def _finish_rect_selection(self, event):
        """完成矩形框选"""
        x0, y0 = self._selection_start_x, self._selection_start_y
        x1, y1 = event.x, event.y
        # 确保左上角和右下角正确
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        # 清除框选图形
        self._clear_selection_graphics()

        # 忽略太小的框选（可能是误点击）
        if max_x - min_x < 5 and max_y - min_y < 5:
            return

        # 如果不按Ctrl，先清除已有选中
        ctrl_pressed = event.state & 0x4  # Ctrl键状态
        if not ctrl_pressed:
            self._clear_all_selections()

        # 遍历所有航点marker，检查是否在矩形范围内
        for i, marker in enumerate(self._map_markers):
            # 获取marker的canvas坐标
            canvas_pos = self._get_marker_canvas_pos(marker)
            if canvas_pos is None:
                continue
            cx, cy = canvas_pos
            if min_x <= cx <= max_x and min_y <= cy <= max_y:
                self._selected_waypoints.add(i)
                self._highlight_marker(i)
                self.tree.selection_add(f"wpt_{i}")

        self._update_selection_status()

    def _get_marker_canvas_pos(self, marker):
        """获取marker在canvas上的坐标"""
        try:
            canvas_pos = marker.get_canvas_pos(marker.position)
            return canvas_pos
        except Exception:
            return None
```

- [ ] **Step 2: 运行程序测试矩形框选**

Run: `python main.py`
操作：
1. 点击矩形工具按钮
2. 在地图上按住左键拖拽画矩形
3. 松开鼠标
预期：
- 拖拽过程中显示蓝色半透明矩形
- 松开后矩形内的marker全部高亮
- 树形列表对应行全部选中
- 状态栏显示"已选中 N 个航点"

- [ ] **Step 3: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现矩形框选航点功能"
```

---

### Task 6: 实现任意框选（Lasso）

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (添加 `_finish_lasso_selection` 和 `_point_in_polygon` 方法)

- [ ] **Step 1: 实现任意框选完成方法**

在 `_finish_rect_selection` 方法之后添加：

```python
    def _finish_lasso_selection(self, event):
        """完成任意框选"""
        self._selection_points.append((event.x, event.y))

        # 清除框选图形
        self._clear_selection_graphics()

        # 忽略太短的路径
        if len(self._selection_points) < 3:
            return

        # 如果不按Ctrl，先清除已有选中
        ctrl_pressed = event.state & 0x4
        if not ctrl_pressed:
            self._clear_all_selections()

        # 遍历所有航点marker，检查是否在多边形内
        polygon = self._selection_points
        for i, marker in enumerate(self._map_markers):
            canvas_pos = self._get_marker_canvas_pos(marker)
            if canvas_pos is None:
                continue
            cx, cy = canvas_pos
            if self._point_in_polygon(cx, cy, polygon):
                self._selected_waypoints.add(i)
                self._highlight_marker(i)
                self.tree.selection_add(f"wpt_{i}")

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
```

- [ ] **Step 2: 运行程序测试任意框选**

Run: `python main.py`
操作：
1. 点击任意工具按钮
2. 在地图上按住左键自由画多边形
3. 松开鼠标
预期：
- 拖拽过程中显示蓝色虚线线条
- 松开后多边形内的marker全部高亮
- 树形列表对应行全部选中

- [ ] **Step 3: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现任意框选航点功能"
```

---

### Task 7: 实现树形列表联动和全选/取消

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (修改 `_on_tree_select`，添加全选和Escape处理)

- [ ] **Step 1: 修改树形列表选中联动**

找到 `_on_tree_select` 方法（约第 407 行），在末尾添加地图marker高亮联动：

```python
    def _on_tree_select(self, event):
        """树形列表选中变更"""
        selected = self.tree.selection()
        if not selected:
            return

        # 同步地图marker高亮
        # 先清除所有marker高亮
        for idx in list(self._selected_waypoints):
            self._unhighlight_marker(idx)
        self._selected_waypoints.clear()

        # 高亮新选中的
        for item_id in selected:
            if item_id.startswith("wpt_"):
                idx = int(item_id.split("_")[1])
                self._selected_waypoints.add(idx)
                self._highlight_marker(idx)

        self._update_selection_status()

        # 更新状态栏（保留原有逻辑）
        if len(selected) == 1:
            iid = selected[0]
            if iid.startswith("wpt_"):
                index = int(iid.split("_")[1])
                wpt = self.gpx_handler.get_waypoints()[index]
                name = wpt.name or f"航点{index+1}"
                coord_text = CoordConverter.format_cgcs2000(wpt.latitude, wpt.longitude)
                self.status_label.config(text=f"选中: {name} | WGS84: {wpt.latitude:.6f}, {wpt.longitude:.6f} | {coord_text}")
```

注意：需要确认 `_on_tree_select` 的原始完整实现，上面只展示了需要添加的部分。实际修改时需要保留原有的状态栏更新逻辑，添加marker高亮同步。

- [ ] **Step 2: 添加Escape和Ctrl+A快捷键**

在 `_create_main_layout` 方法末尾（地图事件绑定之后）添加：

```python
        # 键盘快捷键
        self.bind("<Escape>", lambda e: self._clear_all_selections())
        self.bind("<Control-a>", lambda e: self._select_all_waypoints())
```

- [ ] **Step 3: 实现全选方法**

在 `_clear_all_selections` 方法之后添加：

```python
    def _select_all_waypoints(self):
        """全选所有航点"""
        self._clear_all_selections()
        waypoints = self.gpx_handler.get_waypoints()
        for i in range(len(waypoints)):
            self._selected_waypoints.add(i)
            self._highlight_marker(i)
            self.tree.selection_add(f"wpt_{i}")
        self._update_selection_status()
```

- [ ] **Step 4: 运行程序测试联动**

Run: `python main.py`
操作：
1. 在地图上框选几个航点，检查树形列表是否同步选中
2. 在树形列表中点击选中，检查地图marker是否高亮
3. 按Escape清除所有选中
4. 按Ctrl+A全选
预期：所有联动和快捷键正常工作

- [ ] **Step 5: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现树形列表联动和全选/取消快捷键"
```

---

### Task 8: 添加编辑菜单操作

**Files:**
- Modify: `gpx_editor/gui/main_window.py:90-99` (编辑菜单)
- Modify: `gpx_editor/gui/main_window.py:680-686` (marker右键菜单)

- [ ] **Step 1: 修改编辑菜单**

替换编辑菜单部分（第 90-99 行）：

```python
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
```

- [ ] **Step 2: 实现编辑和移动选中航点方法**

在 `_delete_selected` 方法附近添加：

```python
    def _edit_selected_waypoint(self):
        """编辑选中的航点（仅单选时可用）"""
        if len(self._selected_waypoints) != 1:
            messagebox.showinfo("提示", "请先选中一个航点")
            return
        idx = next(iter(self._selected_waypoints))
        self.edit_waypoint(idx)

    def _move_selected_waypoint(self):
        """移动选中的航点（仅单选时可用）"""
        if len(self._selected_waypoints) != 1:
            messagebox.showinfo("提示", "请先选中一个航点")
            return
        idx = next(iter(self._selected_waypoints))
        self._ctx_wpt_move_by_index(idx)
```

- [ ] **Step 3: 修改marker右键菜单**

替换 `_on_marker_right_click` 方法（第 680-686 行）：

```python
    def _on_marker_right_click(self, event, marker, index):
        """航点marker右键菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑航点", command=lambda: self.edit_waypoint(index))
        menu.add_command(label="移动航点...", command=lambda: self._ctx_wpt_move_by_index(index))
        menu.add_command(label="拖拽移动", command=lambda: self._enable_marker_drag(marker, index))
        menu.add_separator()
        menu.add_command(label="删除此航点", command=lambda: self._delete_waypoint_by_index(index))
        menu.post(event.x_root, event.y_root)
```

- [ ] **Step 4: 实现按索引删除航点方法**

```python
    def _delete_waypoint_by_index(self, index):
        """按索引删除航点"""
        wpt = self.gpx_handler.get_waypoints()[index]
        name = wpt.name or f"航点{index+1}"
        if messagebox.askyesno("确认删除", f"确定要删除航点 {name} 吗？"):
            self.undo_manager.push(self.gpx_handler.get_state())
            self.gpx_handler.delete_waypoint(index)
            self._selected_waypoints.discard(index)
            self._populate_tree()
            self._update_map()
            self._mark_modified()
            self.status_label.config(text=f"已删除航点: {name}")
```

- [ ] **Step 5: 运行程序测试编辑菜单**

Run: `python main.py`
操作：
1. 选中一个航点，点击"编辑"菜单 → "编辑航点"
2. 选中一个航点，点击"编辑"菜单 → "移动航点..."
3. 右键marker，检查新的右键菜单项
预期：所有菜单操作正常工作

- [ ] **Step 6: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 添加编辑菜单操作和右键菜单增强"
```

---

### Task 9: 修复手型模式下点击空白取消选中

**Files:**
- Modify: `gpx_editor/gui/main_window.py` (修改 `_check_clear_selection`)

- [ ] **Step 1: 实现空白区域点击取消选中**

替换 `_check_clear_selection` 方法：

```python
    def _check_clear_selection(self):
        """手型模式下点击空白区域时清除选中"""
        # 延迟执行，让marker点击事件先处理
        # 如果 _selected_waypoints 没有变化，说明点击了空白区域
        # 此处不做任何操作 — marker点击已经处理了选中
        # 空白区域点击需要通过检查鼠标位置是否在marker上来判断
        # 简化实现：手型模式下不自动清除，用户可通过Escape清除
        pass
```

实际上，由于marker的 `<Button-1>` 事件通过 `tag_bind` 绑定，点击marker时会触发 `_on_marker_click`，而点击空白区域不会触发。但tkintermapview自己的鼠标事件会消费左键点击用于平移。

更可靠的方案：在 `_on_marker_click` 中设置一个标志位，`_on_tool_release` 中检查这个标志位。

- [ ] **Step 2: 添加点击标记变量**

在 `__init__` 的状态变量中添加：

```python
        self._marker_clicked = False        # 标记是否点击了marker
```

- [ ] **Step 3: 修改 `_on_marker_click` 设置标志**

在 `_on_marker_click` 方法开头添加：

```python
        self._marker_clicked = True
```

- [ ] **Step 4: 修改 `_on_tool_release` 的hand模式处理**

替换hand模式的release逻辑：

```python
        if self._map_tool == "hand":
            dx = abs(event.x - self._selection_start_x)
            dy = abs(event.y - self._selection_start_y)
            if dx < 5 and dy < 5:
                if not self._marker_clicked:
                    # 点击了空白区域，清除选中
                    self._clear_all_selections()
            self._marker_clicked = False
```

- [ ] **Step 5: 运行程序测试**

Run: `python main.py`
操作：
1. 框选几个航点
2. 用手型工具点击地图空白区域
预期：所有选中被清除

- [ ] **Step 6: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "feat: 实现手型模式点击空白取消选中"
```
