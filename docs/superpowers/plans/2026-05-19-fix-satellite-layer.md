# 卫星图层切换修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复卫星图层切换后地图变空白的问题

**Architecture:** 分步排查：先去掉叠加层隔离问题，再改HTTPS协议，最后清理死代码

**Tech Stack:** Python, tkintermapview, 天地图WMTS瓦片服务

---

### Task 1: 去掉叠加层，隔离问题

**Files:**
- Modify: `gpx_editor/gui/main_window.py:439-457`

- [ ] **Step 1: 注释掉叠加层调用**

在 `_toggle_satellite` 方法中，注释掉 `set_overlay_tile_server` 调用，单独测试卫星底图是否能加载。

```python
def _toggle_satellite(self):
    """切换卫星图层"""
    if not self._tianditu_key:
        messagebox.showinfo("提示", "请先配置天地图API Key")
        return

    if self._current_map_layer == "road":
        img_url = TiandituTileProvider.get_satellite_url(self._tianditu_key)
        # 暂时不设置叠加层，先测试底图能否加载
        # cia_url = TiandituTileProvider.get_annotation_url(self._tianditu_key)
        self.map_widget.set_tile_server(img_url, max_zoom=18)
        # self.map_widget.set_overlay_tile_server(cia_url)
        self._current_map_layer = "satellite"
        self.status_label.config(text="已开启卫星图层（调试模式：无叠加层）")
    else:
        road_url = TiandituTileProvider.get_road_url(self._tianditu_key)
        self.map_widget.set_tile_server(road_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(None)
        self._current_map_layer = "road"
        self.status_label.config(text="已关闭卫星图层")
```

- [ ] **Step 2: 运行程序测试**

Run: `python main.py`
操作：视图 → 卫星图层
预期：
- 若地图正常显示卫星图 → 问题在叠加层（进入Task 3恢复叠加层并修复）
- 若地图仍然空白 → 问题在底图URL/协议（进入Task 2改HTTPS）

- [ ] **Step 3: 根据测试结果决定下一步**

如果底图正常加载，跳到Task 3。如果仍然空白，继续Task 2。

---

### Task 2: 改用HTTPS协议

**Files:**
- Modify: `gpx_editor/core/coord_converter.py:130-134`
- Modify: `tests/test_coord_converter.py:53-58`

- [ ] **Step 1: 编写测试验证HTTPS协议**

在 `tests/test_coord_converter.py` 的 `TestTiandituTileProvider` 类中添加测试：

```python
def test_tile_urls_use_https(self):
    """测试所有瓦片URL使用HTTPS协议"""
    for layer in ["vec", "img", "cia"]:
        url = TiandituTileProvider.get_tile_url(layer, "testkey")
        assert url.startswith("https://"), f"{layer}图层URL应使用HTTPS协议"
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `pytest tests/test_coord_converter.py::TestTiandituTileProvider::test_tile_urls_use_https -v`
Expected: FAIL（当前URL使用HTTP）

- [ ] **Step 3: 修改URL协议为HTTPS**

修改 `gpx_editor/core/coord_converter.py` 第 130-134 行，将所有 `http://` 改为 `https://`：

```python
TILE_URLS = {
    "vec": "https://t0.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
    "img": "https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
    "cia": "https://t0.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_coord_converter.py -v`
Expected: ALL PASS

- [ ] **Step 5: 运行程序验证卫星图层**

Run: `python main.py`
操作：视图 → 卫星图层
预期：卫星底图正常加载

- [ ] **Step 6: Commit**

```bash
git add gpx_editor/core/coord_converter.py tests/test_coord_converter.py
git commit -m "fix: 天地图瓦片URL改用HTTPS协议，修复卫星图层加载失败"
```

---

### Task 3: 恢复叠加层

**Files:**
- Modify: `gpx_editor/gui/main_window.py:439-457`

前提：Task 1 或 Task 2 已确认卫星底图能正常加载。

- [ ] **Step 1: 恢复叠加层调用**

取消 `_toggle_satellite` 中的注释，恢复叠加层：

```python
def _toggle_satellite(self):
    """切换卫星图层"""
    if not self._tianditu_key:
        messagebox.showinfo("提示", "请先配置天地图API Key")
        return

    if self._current_map_layer == "road":
        img_url = TiandituTileProvider.get_satellite_url(self._tianditu_key)
        cia_url = TiandituTileProvider.get_annotation_url(self._tianditu_key)
        self.map_widget.set_tile_server(img_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(cia_url)
        self._current_map_layer = "satellite"
        self.status_label.config(text="已开启卫星图层")
    else:
        road_url = TiandituTileProvider.get_road_url(self._tianditu_key)
        self.map_widget.set_tile_server(road_url, max_zoom=18)
        self.map_widget.set_overlay_tile_server(None)
        self._current_map_layer = "road"
        self.status_label.config(text="已关闭卫星图层")
```

- [ ] **Step 2: 运行程序测试叠加层**

Run: `python main.py`
操作：视图 → 卫星图层
预期：
- 若卫星图+标注正常显示 → 修复完成
- 若叠加层导致空白 → 注释掉叠加层调用，只保留底图切换（不叠加标注）

- [ ] **Step 3: 如果叠加层有问题，去掉叠加层**

如果叠加层导致问题，最终版本不设置 `set_overlay_tile_server`：

```python
if self._current_map_layer == "road":
    img_url = TiandituTileProvider.get_satellite_url(self._tianditu_key)
    self.map_widget.set_tile_server(img_url, max_zoom=18)
    self._current_map_layer = "satellite"
    self.status_label.config(text="已开启卫星图层")
```

- [ ] **Step 4: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "fix: 恢复卫星图层叠加层（或去掉叠加层）"
```

---

### Task 4: 清理死代码

**Files:**
- Modify: `gpx_editor/gui/main_window.py:39`

- [ ] **Step 1: 删除未使用的变量**

删除第 39 行 `self._satellite_overlay = False`，该变量在代码中从未被读取或修改。

- [ ] **Step 2: 运行测试确认无回归**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add gpx_editor/gui/main_window.py
git commit -m "refactor: 删除未使用的_satellite_overlay变量"
```
