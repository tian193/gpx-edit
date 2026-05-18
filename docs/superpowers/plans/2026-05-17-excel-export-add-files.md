# Excel导出对话框添加文件按钮 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在Excel导出对话框中添加"添加文件"和"添加文件夹"按钮，让用户可以导出多个GPX文件的航点。

**Architecture:** 在现有按钮栏左侧添加两个按钮，绑定到已有的 `_add_files()` 和 `_add_folder()` 方法。无架构变更。

**Tech Stack:** Python, tkinter, ttkbootstrap

---

### Task 1: 添加按钮并验证

**Files:**
- Modify: `gpx_editor/gui/excel_export_dialog.py:272-276`

- [ ] **Step 1: 修改按钮栏**

在 `_create_widgets()` 方法中，将第 272-276 行的按钮栏改为：

```python
        # 添加文件和全选按钮
        wp_btn_row = ttk.Frame(right_frame)
        wp_btn_row.pack(fill=X, pady=(0, 5))
        ttk.Button(wp_btn_row, text="添加文件", command=self._add_files, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(wp_btn_row, text="添加文件夹", command=self._add_folder, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(wp_btn_row, text="全选", command=self._select_all_waypoints, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(wp_btn_row, text="取消全选", command=self._deselect_all_waypoints, bootstyle=INFO).pack(side=LEFT, padx=2)
```

- [ ] **Step 2: 运行程序验证**

```bash
python main.py
```

手动测试：
1. 打开任意GPX文件
2. 点击"工具" → "导出航点到Excel"
3. 确认对话框中"选择航点"面板显示四个按钮：[添加文件] [添加文件夹] [全选] [取消全选]
4. 点击"添加文件"，选择一个.gpx文件，确认文件及其航点被添加到列表中
5. 点击"添加文件夹"，选择一个包含.gpx文件的文件夹，确认文件被添加

- [ ] **Step 3: 提交**

```bash
git add gpx_editor/gui/excel_export_dialog.py
git commit -m "feat: Excel导出对话框添加文件和添加文件夹按钮"
```
