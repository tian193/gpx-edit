# -*- coding: utf-8 -*-
"""
批量航点匹配模块
功能: 按位置匹配基线GPX航点，处理源文件
特性: 文本级正则操作，100%保留原始GPX格式（Garmin兼容）
"""

import os
import re
import math
import gpxpy
import gpxpy.gpx
from typing import List, Tuple, Optional, Callable, Dict, Set
from dataclasses import dataclass
from ..utils.helpers import haversine_distance


@dataclass
class DeleteOptions:
    """删除选项"""
    delete_unmatched_baseline: bool = False  # 删除未匹配的基线航点
    delete_unmatched_source: bool = False    # 删除未匹配的源航点
    delete_matched_baseline: bool = False    # 删除匹配的基线航点
    delete_matched_source: bool = False      # 删除匹配的源航点


@dataclass
class MatchResult:
    """单个文件匹配结果"""
    filename: str
    total_waypoints: int
    matched: int
    removed: int
    errors: List[str]


@dataclass
class BatchResult:
    """批量处理结果"""
    total_files: int
    processed_files: int
    failed_files: int
    total_matched: int
    total_removed: int
    file_results: List[MatchResult]


@dataclass
class WaypointPreview:
    """航点预览信息"""
    source_name: str
    source_lat: float
    source_lon: float
    matched_name: str
    distance: float
    status: str  # "保留" 或 "删除"


@dataclass
class FilePreview:
    """文件预览结果"""
    filename: str
    waypoints: List[WaypointPreview]
    matched: int
    removed: int


class BatchMatcher:
    """批量航点匹配器"""

    # 正则：匹配完整的 <wpt ...>...</wpt> 块（含换行和缩进）
    RE_WPT_BLOCK = re.compile(r'[ \t]*<wpt[^>]*>.*?</wpt>\s*\n?', re.DOTALL)

    # 正则：匹配 <wpt> 块内的 <name>...</name>
    RE_WPT_NAME = re.compile(r'(<wpt[^>]*>.*?<name>)(.*?)(</name>.*?</wpt>)', re.DOTALL)

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离（米），使用haversine公式"""
        return haversine_distance(lat1, lon1, lat2, lon2)

    @staticmethod
    def find_nearest_baseline(
        source_lat: float,
        source_lon: float,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint]
    ) -> Tuple[int, float]:
        """找到最近的基线航点，返回 (索引, 距离米)"""
        if not baseline_waypoints:
            return -1, float('inf')

        min_distance = float('inf')
        min_index = -1

        for i, wp in enumerate(baseline_waypoints):
            dist = BatchMatcher.calculate_distance(
                source_lat, source_lon,
                wp.latitude, wp.longitude
            )
            if dist < min_distance:
                min_distance = dist
                min_index = i

        return min_index, min_distance

    @staticmethod
    def load_baseline(filepath: str) -> List[gpxpy.gpx.GPXWaypoint]:
        """加载基线GPX文件的航点"""
        with open(filepath, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
        return gpx.waypoints

    @staticmethod
    def load_baseline_from_dir(dirpath: str, merge: bool = True) -> Dict[str, List[gpxpy.gpx.GPXWaypoint]]:
        """从文件夹加载基线GPX文件

        Args:
            dirpath: 基线文件目录
            merge: True=合并所有航点, False=逐个文件返回

        Returns:
            merge=True: {"_merged": [合并后的航点列表]}
            merge=False: {文件名: [该文件的航点列表]}
        """
        gpx_files = [f for f in os.listdir(dirpath) if f.lower().endswith('.gpx')]
        result = {}

        if merge:
            merged = []
            for filename in gpx_files:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                    merged.extend(gpx.waypoints)
                except Exception:
                    pass
            result["_merged"] = merged
        else:
            for filename in gpx_files:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                    result[filename] = gpx.waypoints
                except Exception:
                    result[filename] = []

        return result

    @staticmethod
    def get_source_files(source_path: str, is_dir: bool) -> List[str]:
        """获取源文件列表

        Args:
            source_path: 源文件路径或目录
            is_dir: 是否为目录

        Returns:
            文件路径列表
        """
        if is_dir:
            return [
                os.path.join(source_path, f)
                for f in os.listdir(source_path)
                if f.lower().endswith('.gpx')
            ]
        else:
            return [source_path] if source_path.lower().endswith('.gpx') else []

    @staticmethod
    def _parse_wpt_info(wpt_block: str) -> Tuple[str, float, float]:
        """从<wpt>文本块中提取name、lat、lon"""
        # 提取 lat 和 lon（同时支持双引号和单引号）
        lat_match = re.search(r'lat=["\']([^"\']+)["\']', wpt_block)
        lon_match = re.search(r'lon=["\']([^"\']+)["\']', wpt_block)
        name_match = re.search(r'<name>([^<]*)</name>', wpt_block)

        lat = float(lat_match.group(1)) if lat_match else 0.0
        lon = float(lon_match.group(1)) if lon_match else 0.0
        name = name_match.group(1) if name_match else ""

        return name, lat, lon

    @staticmethod
    def _build_match_map(
        file_text: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        threshold: float
    ) -> Tuple[dict, int, int, Set[str]]:
        """构建匹配映射

        返回:
            match_map: {源航点名: 基线航点名/空字符串} 或 {源航点名: False} 表示删除
            matched: 匹配数
            removed: 删除数
            matched_baseline_names: 被匹配到的基线航点名集合
        """
        _DELETE = False
        match_map = {}
        matched = 0
        removed = 0
        matched_baseline_names = set()

        for block_match in BatchMatcher.RE_WPT_BLOCK.finditer(file_text):
            block = block_match.group(0)
            src_name, src_lat, src_lon = BatchMatcher._parse_wpt_info(block)

            nearest_idx, distance = BatchMatcher.find_nearest_baseline(
                src_lat, src_lon, baseline_waypoints
            )

            if nearest_idx >= 0 and distance < threshold:
                baseline_name = baseline_waypoints[nearest_idx].name
                match_map[src_name] = baseline_name if baseline_name else src_name
                matched_baseline_names.add(baseline_name or src_name)
                matched += 1
            else:
                match_map[src_name] = _DELETE
                removed += 1

        return match_map, matched, removed, matched_baseline_names

    @staticmethod
    def _apply_text_changes(
        file_text: str,
        match_map: dict,
        prefix: str = "",
        delete_unmatched: bool = True,
        delete_matched: bool = False
    ) -> str:
        """在文本层面应用修改

        Args:
            file_text: 原始文件文本
            match_map: {源航点名: 基线航点名/空字符串} 或 {源航点名: False} 表示删除
            prefix: 航点名称前缀
            delete_unmatched: 是否删除未匹配的航点
            delete_matched: 是否删除匹配的航点

        Returns:
            修改后的文本
        """
        result = file_text

        # 第一步：删除航点块（从后往前删，避免位置偏移）
        blocks_to_remove = []
        for block_match in BatchMatcher.RE_WPT_BLOCK.finditer(result):
            block = block_match.group(0)
            src_name, _, _ = BatchMatcher._parse_wpt_info(block)
            if src_name in match_map:
                is_matched = match_map[src_name] is not False
                if (delete_unmatched and not is_matched) or (delete_matched and is_matched):
                    blocks_to_remove.append(block_match)

        # 从后往前删除
        for bm in reversed(blocks_to_remove):
            result = result[:bm.start()] + result[bm.end():]

        # 第二步：修改匹配航点的名称（仅当不删除匹配航点时）
        if not delete_matched:
            def rename_wpt(block_match):
                block = block_match.group(0)
                src_name, _, _ = BatchMatcher._parse_wpt_info(block)
                if src_name in match_map and match_map[src_name] is not False:
                    new_name = match_map[src_name]
                    if new_name:
                        if prefix:
                            new_name = prefix + new_name
                        block = re.sub(
                            r'(<name>)([^<]*)(</name>)',
                            r'\g<1>' + new_name + r'\3',
                            block
                        )
                return block

            result = BatchMatcher.RE_WPT_BLOCK.sub(rename_wpt, result)

        return result

    @staticmethod
    def process_single_file(
        source_path: str,
        output_path: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        threshold: float,
        prefix: str = ""
    ) -> MatchResult:
        """处理单个源文件（保留原始格式）

        Args:
            source_path: 源文件路径
            output_path: 输出文件路径
            baseline_waypoints: 基线航点列表
            threshold: 匹配距离阈值（米）
            prefix: 航点名称前缀（可选）

        Returns:
            MatchResult: 处理结果
        """
        filename = os.path.basename(source_path)
        result = MatchResult(
            filename=filename,
            total_waypoints=0,
            matched=0,
            removed=0,
            errors=[]
        )

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                file_text = f.read()

            match_map, matched, removed, _ = BatchMatcher._build_match_map(
                file_text, baseline_waypoints, threshold
            )

            result.total_waypoints = len(match_map)
            result.matched = matched
            result.removed = removed

            modified_text = BatchMatcher._apply_text_changes(
                file_text, match_map, prefix
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(modified_text)

        except Exception as e:
            result.errors.append(str(e))

        return result

    @staticmethod
    def apply_baseline_deletions(
        baseline_text: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        matched_baseline_names: Set[str],
        options: DeleteOptions
    ) -> str:
        """应用基线航点删除操作

        Args:
            baseline_text: 基线文件文本
            baseline_waypoints: 基线航点列表
            matched_baseline_names: 被匹配到的基线航点名集合
            options: 删除选项

        Returns:
            修改后的基线文本
        """
        if not options.delete_unmatched_baseline and not options.delete_matched_baseline:
            return baseline_text

        result = baseline_text
        blocks_to_remove = []

        for block_match in BatchMatcher.RE_WPT_BLOCK.finditer(result):
            block = block_match.group(0)
            name, _, _ = BatchMatcher._parse_wpt_info(block)
            is_matched = name in matched_baseline_names

            if (options.delete_unmatched_baseline and not is_matched) or \
               (options.delete_matched_baseline and is_matched):
                blocks_to_remove.append(block_match)

        for bm in reversed(blocks_to_remove):
            result = result[:bm.start()] + result[bm.end():]

        return result

    @staticmethod
    def process_single_file_with_options(
        source_path: str,
        output_path: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        threshold: float,
        prefix: str,
        options: DeleteOptions
    ) -> Tuple[MatchResult, Set[str]]:
        """处理单个源文件，支持删除选项

        Returns:
            (MatchResult, matched_baseline_names)
        """
        filename = os.path.basename(source_path)
        result = MatchResult(
            filename=filename,
            total_waypoints=0,
            matched=0,
            removed=0,
            errors=[]
        )
        matched_baseline_names = set()

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                file_text = f.read()

            match_map, matched, removed, matched_names = BatchMatcher._build_match_map(
                file_text, baseline_waypoints, threshold
            )
            matched_baseline_names = matched_names

            result.total_waypoints = len(match_map)
            result.matched = matched
            result.removed = removed

            modified_text = BatchMatcher._apply_text_changes(
                file_text, match_map, prefix,
                delete_unmatched=options.delete_unmatched_source,
                delete_matched=options.delete_matched_source
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(modified_text)

        except Exception as e:
            result.errors.append(str(e))

        return result, matched_baseline_names

    @staticmethod
    def batch_process(
        baseline_path: str,
        source_dir: str,
        output_dir: str,
        threshold: float,
        prefix: str = "",
        callback: Optional[Callable[[str, int, int], None]] = None
    ) -> BatchResult:
        """批量处理入口（兼容旧接口）"""
        options = DeleteOptions(delete_unmatched_source=True)
        return BatchMatcher.batch_process_with_options(
            baseline_path, True, source_dir, True, output_dir,
            threshold, prefix, options, callback
        )

    @staticmethod
    def batch_process_with_options(
        baseline_path: str,
        baseline_is_dir: bool,
        source_path: str,
        source_is_dir: bool,
        output_dir: str,
        threshold: float,
        prefix: str,
        options: DeleteOptions,
        callback: Optional[Callable[[str, int, int], None]] = None,
        baseline_merge: bool = True
    ) -> BatchResult:
        """批量处理入口（支持删除选项）

        Args:
            baseline_path: 基线GPX文件或目录路径
            baseline_is_dir: 基线是否为目录
            source_path: 源文件或目录路径
            source_is_dir: 源是否为目录
            output_dir: 输出目录
            threshold: 匹配距离阈值（米）
            prefix: 航点名称前缀
            options: 删除选项
            callback: 回调函数 (当前文件名, 当前索引, 总数)
            baseline_merge: 基线目录模式下是否合并航点

        Returns:
            BatchResult: 批量处理结果
        """
        batch_result = BatchResult(
            total_files=0,
            processed_files=0,
            failed_files=0,
            total_matched=0,
            total_removed=0,
            file_results=[]
        )

        # 加载基线航点
        if baseline_is_dir:
            baseline_dict = BatchMatcher.load_baseline_from_dir(baseline_path, baseline_merge)
        else:
            try:
                waypoints = BatchMatcher.load_baseline(baseline_path)
                baseline_dict = {os.path.basename(baseline_path): waypoints}
            except Exception as e:
                batch_result.file_results.append(
                    MatchResult("基线文件加载失败", 0, 0, 0, [str(e)])
                )
                return batch_result

        # 获取源文件列表
        source_files = BatchMatcher.get_source_files(source_path, source_is_dir)
        batch_result.total_files = len(source_files)

        os.makedirs(output_dir, exist_ok=True)

        # 处理每个源文件
        all_matched_baseline_names = set()  # 累积所有源文件匹配的基线航点名
        for i, src_file in enumerate(source_files):
            filename = os.path.basename(src_file)
            if callback:
                callback(filename, i + 1, len(source_files))

            output_path = os.path.join(output_dir, filename)

            # 选择基线航点
            if baseline_merge or not baseline_is_dir:
                baseline_waypoints = list(baseline_dict.values())[0]
            else:
                # 逐个匹配模式：使用所有基线航点
                baseline_waypoints = []
                for wp_list in baseline_dict.values():
                    baseline_waypoints.extend(wp_list)

            result, matched_names = BatchMatcher.process_single_file_with_options(
                src_file, output_path,
                baseline_waypoints, threshold, prefix, options
            )

            # 累积匹配的基线航点名
            all_matched_baseline_names.update(matched_names)

            batch_result.file_results.append(result)

            if result.errors:
                batch_result.failed_files += 1
            else:
                batch_result.processed_files += 1

            batch_result.total_matched += result.matched
            batch_result.total_removed += result.removed

        # 目录模式基线删除处理（累积所有源文件的匹配结果后统一处理）
        if (options.delete_unmatched_baseline or options.delete_matched_baseline) and baseline_is_dir:
            for bl_name, bl_waypoints in baseline_dict.items():
                try:
                    bl_path = os.path.join(baseline_path, bl_name)
                    with open(bl_path, 'r', encoding='utf-8') as f:
                        bl_text = f.read()
                    modified = BatchMatcher.apply_baseline_deletions(
                        bl_text, bl_waypoints, all_matched_baseline_names, options
                    )
                    bl_output = os.path.join(output_dir, f"baseline_{bl_name}")
                    with open(bl_output, 'w', encoding='utf-8') as f:
                        f.write(modified)
                except Exception:
                    pass

        # 单基线文件删除处理
        if (options.delete_unmatched_baseline or options.delete_matched_baseline) and not baseline_is_dir:
            try:
                with open(baseline_path, 'r', encoding='utf-8') as f:
                    bl_text = f.read()
                bl_waypoints = list(baseline_dict.values())[0]

                modified = BatchMatcher.apply_baseline_deletions(
                    bl_text, bl_waypoints, all_matched_baseline_names, options
                )
                bl_output = os.path.join(output_dir, os.path.basename(baseline_path))
                with open(bl_output, 'w', encoding='utf-8') as f:
                    f.write(modified)
            except Exception:
                pass

        return batch_result

    @staticmethod
    def preview_file(
        source_path: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        threshold: float
    ) -> FilePreview:
        """预览单个文件的匹配结果

        Args:
            source_path: 源文件路径
            baseline_waypoints: 基线航点列表
            threshold: 匹配距离阈值（米）

        Returns:
            FilePreview: 预览结果
        """
        filename = os.path.basename(source_path)
        waypoints = []
        matched = 0
        removed = 0

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)

            for wp in gpx.waypoints:
                nearest_idx, distance = BatchMatcher.find_nearest_baseline(
                    wp.latitude, wp.longitude, baseline_waypoints
                )

                if nearest_idx >= 0 and distance < threshold:
                    matched_baseline = baseline_waypoints[nearest_idx]
                    waypoints.append(WaypointPreview(
                        source_name=wp.name or "(无名)",
                        source_lat=wp.latitude,
                        source_lon=wp.longitude,
                        matched_name=matched_baseline.name,
                        distance=round(distance, 1),
                        status="保留"
                    ))
                    matched += 1
                else:
                    nearest_name = baseline_waypoints[nearest_idx].name if nearest_idx >= 0 else "无"
                    waypoints.append(WaypointPreview(
                        source_name=wp.name or "(无名)",
                        source_lat=wp.latitude,
                        source_lon=wp.longitude,
                        matched_name=nearest_name,
                        distance=round(distance, 1) if distance != float('inf') else 999999,
                        status="删除"
                    ))
                    removed += 1

        except Exception as e:
            pass

        return FilePreview(
            filename=filename,
            waypoints=waypoints,
            matched=matched,
            removed=removed
        )

    @staticmethod
    def preview_baseline_file(
        baseline_path: str,
        baseline_waypoints: List[gpxpy.gpx.GPXWaypoint],
        source_files: List[str],
        threshold: float,
        options: DeleteOptions
    ) -> FilePreview:
        """预览基线文件的匹配结果

        根据源文件匹配情况，标注基线航点的保留/删除状态。
        用于"删除匹配的基线文件"和"删除未匹配的基线文件"模式。

        Args:
            baseline_path: 基线文件路径
            baseline_waypoints: 基线航点列表
            source_files: 源文件路径列表
            threshold: 匹配距离阈值（米）
            options: 删除选项

        Returns:
            FilePreview: 预览结果
        """
        filename = os.path.basename(baseline_path)
        waypoints = []
        matched = 0
        removed = 0

        # 收集所有源文件中匹配到的基线航点名
        matched_baseline_names = set()
        for src_file in source_files:
            try:
                with open(src_file, 'r', encoding='utf-8') as f:
                    gpx = gpxpy.parse(f)
                for wp in gpx.waypoints:
                    nearest_idx, distance = BatchMatcher.find_nearest_baseline(
                        wp.latitude, wp.longitude, baseline_waypoints
                    )
                    if nearest_idx >= 0 and distance < threshold:
                        matched_baseline_names.add(baseline_waypoints[nearest_idx].name)
            except Exception:
                pass

        # 遍历基线航点，标注保留/删除状态
        for wp in baseline_waypoints:
            is_matched = wp.name in matched_baseline_names
            # 根据删除选项决定状态
            if options.delete_matched_baseline:
                status = "删除" if is_matched else "保留"
            elif options.delete_unmatched_baseline:
                status = "删除" if not is_matched else "保留"
            else:
                status = "保留"

            # 找到最近的源航点用于显示
            nearest_src_name = ""
            nearest_distance = 0
            for src_file in source_files:
                try:
                    with open(src_file, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                    for src_wp in gpx.waypoints:
                        dist = BatchMatcher.calculate_distance(
                            wp.latitude, wp.longitude,
                            src_wp.latitude, src_wp.longitude
                        )
                        if nearest_src_name == "" or dist < nearest_distance:
                            nearest_src_name = src_wp.name or "(无名)"
                            nearest_distance = dist
                except Exception:
                    pass

            waypoints.append(WaypointPreview(
                source_name=wp.name or "(无名)",
                source_lat=wp.latitude,
                source_lon=wp.longitude,
                matched_name=nearest_src_name,
                distance=round(nearest_distance, 1),
                status=status
            ))
            if status == "删除":
                removed += 1
            else:
                matched += 1

        return FilePreview(
            filename=filename,
            waypoints=waypoints,
            matched=matched,
            removed=removed
        )
