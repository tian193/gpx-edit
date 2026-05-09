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
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass


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
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

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
    def _parse_wpt_info(wpt_block: str) -> Tuple[str, float, float]:
        """从<wpt>文本块中提取name、lat、lon"""
        # 提取 lat 和 lon
        lat_match = re.search(r'lat="([^"]+)"', wpt_block)
        lon_match = re.search(r'lon="([^"]+)"', wpt_block)
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
    ) -> Tuple[dict, int, int]:
        """构建匹配映射

        返回:
            match_map: {源航点名: 基线航点名} 或 {源航点名: None} 表示删除
            matched: 匹配数
            removed: 删除数
        """
        match_map = {}
        matched = 0
        removed = 0

        for block_match in BatchMatcher.RE_WPT_BLOCK.finditer(file_text):
            block = block_match.group(0)
            src_name, src_lat, src_lon = BatchMatcher._parse_wpt_info(block)

            nearest_idx, distance = BatchMatcher.find_nearest_baseline(
                src_lat, src_lon, baseline_waypoints
            )

            if nearest_idx >= 0 and distance < threshold:
                # 匹配成功：映射到基线航点名
                match_map[src_name] = baseline_waypoints[nearest_idx].name
                matched += 1
            else:
                # 未匹配：标记删除
                match_map[src_name] = None
                removed += 1

        return match_map, matched, removed

    @staticmethod
    def _apply_text_changes(
        file_text: str,
        match_map: dict,
        prefix: str = ""
    ) -> str:
        """在文本层面应用修改

        Args:
            file_text: 原始文件文本
            match_map: {源航点名: 基线航点名/None}
            prefix: 航点名称前缀

        Returns:
            修改后的文本
        """
        result = file_text

        # 第一步：删除未匹配的航点块（从后往前删，避免位置偏移）
        blocks_to_remove = []
        for block_match in BatchMatcher.RE_WPT_BLOCK.finditer(result):
            block = block_match.group(0)
            src_name, _, _ = BatchMatcher._parse_wpt_info(block)
            if src_name in match_map and match_map[src_name] is None:
                blocks_to_remove.append(block_match)

        # 从后往前删除
        for bm in reversed(blocks_to_remove):
            result = result[:bm.start()] + result[bm.end():]

        # 第二步：修改匹配航点的名称
        def rename_wpt(block_match):
            block = block_match.group(0)
            src_name, _, _ = BatchMatcher._parse_wpt_info(block)
            if src_name in match_map and match_map[src_name] is not None:
                new_name = match_map[src_name]
                if prefix:
                    new_name = prefix + new_name
                # 只替换 <name> 标签内容
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
            # 读取原始文件文本
            with open(source_path, 'r', encoding='utf-8') as f:
                file_text = f.read()

            # 构建匹配映射
            match_map, matched, removed = BatchMatcher._build_match_map(
                file_text, baseline_waypoints, threshold
            )

            result.total_waypoints = len(match_map)
            result.matched = matched
            result.removed = removed

            # 应用文本修改
            modified_text = BatchMatcher._apply_text_changes(
                file_text, match_map, prefix
            )

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 写回文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(modified_text)

        except Exception as e:
            result.errors.append(str(e))

        return result

    @staticmethod
    def batch_process(
        baseline_path: str,
        source_dir: str,
        output_dir: str,
        threshold: float,
        prefix: str = "",
        callback: Optional[Callable[[str, int, int], None]] = None
    ) -> BatchResult:
        """批量处理入口

        Args:
            baseline_path: 基线GPX文件路径
            source_dir: 源文件目录
            output_dir: 输出目录
            threshold: 匹配距离阈值（米）
            prefix: 航点名称前缀（可选）
            callback: 回调函数 (当前文件名, 当前索引, 总数)

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
        try:
            baseline_waypoints = BatchMatcher.load_baseline(baseline_path)
        except Exception as e:
            batch_result.file_results.append(
                MatchResult("基线文件加载失败", 0, 0, 0, [str(e)])
            )
            return batch_result

        # 获取源目录下所有GPX文件
        gpx_files = [
            f for f in os.listdir(source_dir)
            if f.lower().endswith('.gpx')
        ]
        batch_result.total_files = len(gpx_files)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 处理每个文件
        for i, filename in enumerate(gpx_files):
            if callback:
                callback(filename, i + 1, len(gpx_files))

            source_path = os.path.join(source_dir, filename)
            output_path = os.path.join(output_dir, filename)

            result = BatchMatcher.process_single_file(
                source_path, output_path,
                baseline_waypoints, threshold, prefix
            )

            batch_result.file_results.append(result)

            if result.errors:
                batch_result.failed_files += 1
            else:
                batch_result.processed_files += 1

            batch_result.total_matched += result.matched
            batch_result.total_removed += result.removed

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
