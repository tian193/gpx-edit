# 卫星图层切换修复设计

## 问题描述

切换卫星图层后，地图变为空白/灰色，瓦片无法加载。

## 根因分析

`_toggle_satellite` 方法在切换到卫星模式时，同时设置卫星底图（`img`）和注记叠加层（`cia`）。问题可能来自：

1. `set_overlay_tile_server(cia_url)` 叠加注记层失败，干扰底图渲染
2. 天地图 `img` 图层瓦片加载超时
3. HTTP协议在网络环境中被拦截

## 修复方案

分步排查，逐步验证：

### 第一步：隔离叠加层问题

在 `_toggle_satellite` 中，先注释掉 `set_overlay_tile_server` 调用，单独测试卫星底图加载。

- 若底图正常加载 → 问题在叠加层
- 若底图仍然空白 → 问题在底图URL或协议

### 第二步：改用HTTPS协议

将 `TiandituTileProvider.TILE_URLS` 中所有 `http://` 改为 `https://`。

涉及文件：`gpx_editor/core/coord_converter.py` 第 130-134 行

### 第三步：恢复叠加层

确认底图正常后，恢复 `set_overlay_tile_server` 调用。

### 附加：清理死代码

删除 `main_window.py` 第 39 行未使用的 `self._satellite_overlay = False` 变量。

## 涉及文件

- `gpx_editor/core/coord_converter.py` — URL协议修改
- `gpx_editor/gui/main_window.py` — 切换逻辑调试、死代码清理
