# -*- coding: utf-8 -*-
"""
海拔剖面图组件
功能: 用 tkinter Canvas 绘制海拔随距离变化的折线图
"""

import tkinter as tk
from typing import List, Tuple, Optional


class ElevationChart(tk.Canvas):
    """海拔剖面图 Canvas 组件"""

    # 边距
    MARGIN_LEFT = 70
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 40

    # 颜色
    COLOR_BG = "#FFFFFF"
    COLOR_LINE = "#2ECC71"
    COLOR_AXIS = "#333333"
    COLOR_GRID = "#E0E0E0"
    COLOR_TEXT = "#555555"
    COLOR_HOVER = "#E74C3C"
    COLOR_FILL = "#E8F5E9"

    def __init__(self, parent, width=600, height=300, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=self.COLOR_BG, highlightthickness=0, **kwargs)

        self._data: List[Tuple[float, float, object]] = []  # (距离m, 海拔m, 时间)
        self._hover_line = None
        self._hover_text = None
        self._fill_polygon = None

        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Leave>", self._on_mouse_leave)
        self.bind("<Configure>", self._on_resize)

    def set_data(self, data: List[Tuple[float, float, object]]):
        """设置数据并重绘

        Args:
            data: [(累计距离m, 海拔m, 时间), ...]
        """
        self._data = data
        self._draw()

    def _draw(self):
        """绘制图表"""
        self.delete("all")
        if not self._data:
            self.create_text(
                self.winfo_width() // 2, self.winfo_height() // 2,
                text="无海拔数据", fill=self.COLOR_TEXT, font=("", 12)
            )
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 100 or h < 100:
            return

        # 计算绘图区域
        plot_left = self.MARGIN_LEFT
        plot_right = w - self.MARGIN_RIGHT
        plot_top = self.MARGIN_TOP
        plot_bottom = h - self.MARGIN_BOTTOM
        plot_w = plot_right - plot_left
        plot_h = plot_bottom - plot_top

        if plot_w <= 0 or plot_h <= 0:
            return

        # 数据范围
        distances = [d[0] for d in self._data]
        elevations = [d[1] for d in self._data]
        min_dist = min(distances)
        max_dist = max(distances)
        min_ele = min(elevations)
        max_ele = max(elevations)

        # 留一点边距
        ele_range = max_ele - min_ele
        if ele_range == 0:
            ele_range = 10
        min_ele -= ele_range * 0.05
        max_ele += ele_range * 0.05
        ele_range = max_ele - min_ele

        dist_range = max_dist - min_dist
        if dist_range == 0:
            dist_range = 100

        # 坐标转换函数
        def to_canvas_x(dist):
            return plot_left + (dist - min_dist) / dist_range * plot_w

        def to_canvas_y(ele):
            return plot_bottom - (ele - min_ele) / ele_range * plot_h

        # 绘制网格线和刻度
        self._draw_grid(plot_left, plot_right, plot_top, plot_bottom,
                        min_dist, max_dist, min_ele, max_ele,
                        to_canvas_x, to_canvas_y)

        # 绘制填充区域
        points = []
        for dist, ele, _ in self._data:
            points.append((to_canvas_x(dist), to_canvas_y(ele)))
        # 闭合填充区域
        fill_points = list(points)
        fill_points.append((to_canvas_x(max_dist), plot_bottom))
        fill_points.append((to_canvas_x(min_dist), plot_bottom))
        flat = [coord for p in fill_points for coord in p]
        if len(flat) >= 6:
            self.create_polygon(*flat, fill=self.COLOR_FILL, outline="")

        # 绘制折线
        if len(points) >= 2:
            flat_line = [coord for p in points for coord in p]
            self.create_line(*flat_line, fill=self.COLOR_LINE, width=2, smooth=True)

        # 绘制坐标轴
        self.create_line(plot_left, plot_top, plot_left, plot_bottom,
                         fill=self.COLOR_AXIS, width=1)
        self.create_line(plot_left, plot_bottom, plot_right, plot_bottom,
                         fill=self.COLOR_AXIS, width=1)

        # Y轴标签
        self.create_text(plot_left - 5, plot_top + plot_h // 2,
                         text="海拔 (m)", fill=self.COLOR_TEXT,
                         font=("", 9), anchor="e", angle=90)

        # X轴标签
        self.create_text(plot_left + plot_w // 2, plot_bottom + 30,
                         text="距离 (m)", fill=self.COLOR_TEXT,
                         font=("", 9), anchor="n")

        # 保存绘图参数供鼠标交互使用
        self._plot_params = {
            'plot_left': plot_left, 'plot_right': plot_right,
            'plot_top': plot_top, 'plot_bottom': plot_bottom,
            'plot_w': plot_w, 'plot_h': plot_h,
            'min_dist': min_dist, 'max_dist': max_dist,
            'min_ele': min_ele, 'max_ele': max_ele,
            'dist_range': dist_range, 'ele_range': ele_range,
            'to_canvas_x': to_canvas_x, 'to_canvas_y': to_canvas_y,
        }

    def _draw_grid(self, left, right, top, bottom,
                   min_dist, max_dist, min_ele, max_ele,
                   to_canvas_x, to_canvas_y):
        """绘制网格线和刻度"""
        plot_h = bottom - top
        plot_w = right - left

        # Y轴刻度（约5-8条网格线）
        ele_range = max_ele - min_ele
        step = self._nice_step(ele_range, 6)
        ele_start = (min_ele // step) * step
        ele = ele_start
        while ele <= max_ele:
            y = to_canvas_y(ele)
            if top <= y <= bottom:
                self.create_line(left, y, right, y,
                                 fill=self.COLOR_GRID, dash=(2, 4))
                self.create_text(left - 5, y, text=f"{ele:.0f}",
                                 fill=self.COLOR_TEXT, font=("", 8), anchor="e")
            ele += step

        # X轴刻度
        dist_range = max_dist - min_dist
        step = self._nice_step(dist_range, 6)
        dist_start = (min_dist // step) * step
        dist = dist_start
        while dist <= max_dist:
            x = to_canvas_x(dist)
            if left <= x <= right:
                self.create_line(x, top, x, bottom,
                                 fill=self.COLOR_GRID, dash=(2, 4))
                if dist >= 1000:
                    label = f"{dist / 1000:.1f}km"
                else:
                    label = f"{dist:.0f}m"
                self.create_text(x, bottom + 5, text=label,
                                 fill=self.COLOR_TEXT, font=("", 8), anchor="n")
            dist += step

    @staticmethod
    def _nice_step(range_val, target_ticks):
        """计算一个'好看'的刻度步长"""
        if range_val <= 0:
            return 1
        raw = range_val / target_ticks
        magnitude = 10 ** (int(f"{raw:.0e}".split("e")[1]) if raw > 0 else 0)
        for nice in [1, 2, 5, 10]:
            if nice * magnitude >= raw:
                return nice * magnitude
        return magnitude * 10

    def _on_mouse_move(self, event):
        """鼠标移动显示竖线和tooltip"""
        if not self._data or not hasattr(self, '_plot_params'):
            return

        p = self._plot_params
        x = event.x
        if x < p['plot_left'] or x > p['plot_right']:
            self._on_mouse_leave(event)
            return

        # 根据canvas x反算距离
        ratio = (x - p['plot_left']) / p['plot_w']
        dist = p['min_dist'] + ratio * p['dist_range']

        # 找到最近的数据点
        best_idx = 0
        best_diff = float('inf')
        for i, (d, _, _) in enumerate(self._data):
            diff = abs(d - dist)
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        d, ele, t = self._data[best_idx]
        cx = p['to_canvas_x'](d)
        cy = p['to_canvas_y'](ele)

        # 清除旧的hover元素
        self._clear_hover()

        # 绘制竖线
        self._hover_line = self.create_line(
            cx, p['plot_top'], cx, p['plot_bottom'],
            fill=self.COLOR_HOVER, dash=(3, 3), width=1
        )

        # 绘制高亮点
        r = 4
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=self.COLOR_HOVER, outline="white", width=1,
                         tags="hover")

        # 绘制tooltip
        dist_text = f"{d:.0f}m" if d < 1000 else f"{d / 1000:.2f}km"
        time_text = ""
        if t:
            time_text = t.strftime(" %H:%M:%S")
        tooltip = f"距离: {dist_text}\n海拔: {ele:.1f}m{time_text}"

        # tooltip背景
        tx = cx + 10
        ty = cy - 40
        if ty < p['plot_top']:
            ty = cy + 10
        if tx + 150 > p['plot_right']:
            tx = cx - 160

        self._hover_text = self.create_text(
            tx, ty, text=tooltip, fill=self.COLOR_TEXT,
            font=("", 9), anchor="nw", tags="hover"
        )

    def _on_mouse_leave(self, event):
        """鼠标离开清除hover"""
        self._clear_hover()

    def _clear_hover(self):
        """清除hover元素"""
        if self._hover_line:
            self.delete(self._hover_line)
            self._hover_line = None
        self.delete("hover")

    def _on_resize(self, event):
        """窗口大小变化时重绘"""
        self._draw()
