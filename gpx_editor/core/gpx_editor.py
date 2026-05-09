# -*- coding: utf-8 -*-
"""
GPX属性编辑模块
功能: 解析、修改GPX文件属性，坐标移动
特性: 文本级正则操作，100%保留原始GPX格式
"""

import os
import re
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class WaypointInfo:
    """航点信息"""
    index: int
    name: str
    lat: float
    lon: float
    ele: Optional[float] = None
    time: Optional[str] = None
    comment: Optional[str] = None
    description: Optional[str] = None
    symbol: Optional[str] = None
    type: Optional[str] = None


@dataclass
class TrackInfo:
    """航迹信息"""
    index: int
    name: str
    description: Optional[str] = None
    comment: Optional[str] = None
    type: Optional[str] = None
    segment_count: int = 0
    point_count: int = 0


@dataclass
class FileInfo:
    """GPX文件信息"""
    filepath: str
    filename: str
    version: Optional[str] = None
    creator: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    waypoints: List[WaypointInfo] = field(default_factory=list)
    tracks: List[TrackInfo] = field(default_factory=list)


class GpxEditor:
    """GPX属性编辑器"""

    # 正则表达式
    RE_WPT_BLOCK = re.compile(r'[ \t]*<wpt[^>]*>.*?</wpt>\s*\n?', re.DOTALL)
    RE_TRK_BLOCK = re.compile(r'[ \t]*<trk>.*?</trk>\s*\n?', re.DOTALL)
    RE_TRKPT_BLOCK = re.compile(r'<trkpt[^>]*>.*?</trkpt>', re.DOTALL)

    @staticmethod
    def parse_file(filepath: str) -> FileInfo:
        """解析GPX文件，返回所有属性"""
        filename = os.path.basename(filepath)
        info = FileInfo(filepath=filepath, filename=filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析文件级属性
        version_match = re.search(r'<gpx[^>]*version="([^"]*)"', content)
        creator_match = re.search(r'<gpx[^>]*creator="([^"]*)"', content)
        if version_match:
            info.version = version_match.group(1)
        if creator_match:
            info.creator = creator_match.group(1)

        # 解析航点
        for i, block_match in enumerate(GpxEditor.RE_WPT_BLOCK.finditer(content)):
            block = block_match.group(0)
            wp = GpxEditor._parse_wpt_block(block, i)
            if wp:
                info.waypoints.append(wp)

        # 解析航迹
        for i, block_match in enumerate(GpxEditor.RE_TRK_BLOCK.finditer(content)):
            block = block_match.group(0)
            trk = GpxEditor._parse_trk_block(block, i)
            if trk:
                info.tracks.append(trk)

        return info

    @staticmethod
    def _parse_wpt_block(block: str, index: int) -> Optional[WaypointInfo]:
        """解析航点块"""
        lat_match = re.search(r'lat="([^"]+)"', block)
        lon_match = re.search(r'lon="([^"]+)"', block)
        if not lat_match or not lon_match:
            return None

        wp = WaypointInfo(
            index=index,
            name=GpxEditor._extract_tag(block, 'name'),
            lat=float(lat_match.group(1)),
            lon=float(lon_match.group(1))
        )

        ele = GpxEditor._extract_tag(block, 'ele')
        if ele:
            try:
                wp.elevation = float(ele)
            except ValueError:
                pass

        wp.time = GpxEditor._extract_tag(block, 'time')
        wp.comment = GpxEditor._extract_tag(block, 'cmt')
        wp.description = GpxEditor._extract_tag(block, 'desc')
        wp.symbol = GpxEditor._extract_tag(block, 'sym')
        wp.type = GpxEditor._extract_tag(block, 'type')

        return wp

    @staticmethod
    def _parse_trk_block(block: str, index: int) -> Optional[TrackInfo]:
        """解析航迹块"""
        trk = TrackInfo(
            index=index,
            name=GpxEditor._extract_tag(block, 'name'),
            description=GpxEditor._extract_tag(block, 'desc'),
            comment=GpxEditor._extract_tag(block, 'cmt'),
            type=GpxEditor._extract_tag(block, 'type')
        )

        # 统计航段和航迹点数量
        trk.seg_count = len(re.findall(r'<trkseg>', block))
        trk.point_count = len(re.findall(r'<trkpt', block))

        return trk

    @staticmethod
    def _extract_tag(text: str, tag: str) -> Optional[str]:
        """提取标签内容"""
        match = re.search(f'<{tag}>([^<]*)</{tag}>', text)
        return match.group(1) if match else None

    @staticmethod
    def modify_attribute(
        filepath: str,
        output_path: str,
        attr_type: str,
        attr_name: str,
        new_value: str,
        target: str = "all",
        target_name: str = ""
    ) -> Tuple[bool, str]:
        """修改属性（保留原始格式）

        Args:
            filepath: 源文件路径
            output_path: 输出文件路径
            attr_type: 'file', 'waypoint', 'track'
            attr_name: 属性名
            new_value: 新值
            target: 'all' 或 'named'
            target_name: 目标名称（当target='named'时使用）

        Returns:
            (成功, 消息)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if attr_type == 'file':
                content = GpxEditor._modify_file_attr(content, attr_name, new_value)
            elif attr_type == 'waypoint':
                content = GpxEditor._modify_wpt_attr(content, attr_name, new_value, target, target_name)
            elif attr_type == 'track':
                content = GpxEditor._modify_trk_attr(content, attr_name, new_value, target, target_name)
            else:
                return False, f"未知属性类型: {attr_type}"

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, "修改成功"

        except Exception as e:
            return False, f"修改失败: {str(e)}"

    @staticmethod
    def _modify_file_attr(content: str, attr_name: str, new_value: str) -> str:
        """修改文件级属性"""
        if attr_name == 'creator':
            content = re.sub(r'(<gpx[^>]*creator=")[^"]*(")', r'\g<1>' + new_value + r'\2', content)
        elif attr_name == 'version':
            content = re.sub(r'(<gpx[^>]*version=")[^"]*(")', r'\g<1>' + new_value + r'\2', content)
        elif attr_name == 'name':
            # metadata中的name
            if '<metadata>' in content:
                content = re.sub(
                    r'(<metadata>.*?<name>)([^<]*)(</name>)',
                    r'\g<1>' + new_value + r'\3',
                    content, count=1, flags=re.DOTALL
                )
        elif attr_name == 'description':
            if '<metadata>' in content:
                content = re.sub(
                    r'(<metadata>.*?<desc>)([^<]*)(</desc>)',
                    r'\g<1>' + new_value + r'\3',
                    content, count=1, flags=re.DOTALL
                )
        return content

    @staticmethod
    def _modify_wpt_attr(content: str, attr_name: str, new_value: str, target: str, target_name: str) -> str:
        """修改航点属性"""
        def replace_in_wpt(match):
            block = match.group(0)

            # 如果是按名称查找，检查航点名称
            if target == 'named' and target_name:
                block_name = GpxEditor._extract_tag(block, 'name')
                if block_name != target_name:
                    return block

            # 修改属性
            if attr_name == 'name':
                block = re.sub(r'(<name>)([^<]*)(</name>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'ele':
                block = re.sub(r'(<ele>)([^<]*)(</ele>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'time':
                block = re.sub(r'(<time>)([^<]*)(</time>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'cmt':
                block = re.sub(r'(<cmt>)([^<]*)(</cmt>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'desc':
                block = re.sub(r'(<desc>)([^<]*)(</desc>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'sym':
                block = re.sub(r'(<sym>)([^<]*)(</sym>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'type':
                block = re.sub(r'(<type>)([^<]*)(</type>)', r'\g<1>' + new_value + r'\3', block)

            return block

        return GpxEditor.RE_WPT_BLOCK.sub(replace_in_wpt, content)

    @staticmethod
    def _modify_trk_attr(content: str, attr_name: str, new_value: str, target: str, target_name: str) -> str:
        """修改航迹属性"""
        def replace_in_trk(match):
            block = match.group(0)

            # 如果是按名称查找，检查航迹名称
            if target == 'named' and target_name:
                block_name = GpxEditor._extract_tag(block, 'name')
                if block_name != target_name:
                    return block

            # 修改属性
            if attr_name == 'name':
                block = re.sub(r'(<name>)([^<]*)(</name>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'desc':
                block = re.sub(r'(<desc>)([^<]*)(</desc>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'cmt':
                block = re.sub(r'(<cmt>)([^<]*)(</cmt>)', r'\g<1>' + new_value + r'\3', block)
            elif attr_name == 'type':
                block = re.sub(r'(<type>)([^<]*)(</type>)', r'\g<1>' + new_value + r'\3', block)

            return block

        return GpxEditor.RE_TRK_BLOCK.sub(replace_in_trk, content)

    @staticmethod
    def offset_coordinates(lat: float, lon: float, x_meters: float, y_meters: float) -> Tuple[float, float]:
        """坐标偏移计算

        Args:
            lat: 纬度
            lon: 经度
            x_meters: X偏移（正=东，负=西）
            y_meters: Y偏移（正=北，负=南）

        Returns:
            (新纬度, 新经度)
        """
        lat_offset = y_meters / 111000.0
        lon_offset = x_meters / (111000.0 * math.cos(math.radians(lat)))
        return lat + lat_offset, lon + lon_offset

    @staticmethod
    def offset_file(
        filepath: str,
        output_path: str,
        x_meters: float,
        y_meters: float,
        target: str = "all"
    ) -> Tuple[bool, str]:
        """坐标偏移（保留原始格式）

        Args:
            filepath: 源文件路径
            output_path: 输出文件路径
            x_meters: X偏移（正=东，负=西）
            y_meters: Y偏移（正=北，负=南）
            target: 'all', 'waypoint', 'track'

        Returns:
            (成功, 消息)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if target in ('all', 'waypoint'):
                content = GpxEditor._offset_wpt(content, x_meters, y_meters)

            if target in ('all', 'track'):
                content = GpxEditor._offset_trkpt(content, x_meters, y_meters)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, "偏移成功"

        except Exception as e:
            return False, f"偏移失败: {str(e)}"

    @staticmethod
    def _offset_wpt(content: str, x_meters: float, y_meters: float) -> str:
        """偏移航点坐标"""
        def offset_wpt_block(match):
            block = match.group(0)

            lat_match = re.search(r'lat="([^"]+)"', block)
            lon_match = re.search(r'lon="([^"]+)"', block)

            if lat_match and lon_match:
                lat = float(lat_match.group(1))
                lon = float(lon_match.group(1))
                new_lat, new_lon = GpxEditor.offset_coordinates(lat, lon, x_meters, y_meters)
                block = block.replace(f'lat="{lat}"', f'lat="{new_lat}"')
                block = block.replace(f'lon="{lon}"', f'lon="{new_lon}"')

            return block

        return GpxEditor.RE_WPT_BLOCK.sub(offset_wpt_block, content)

    @staticmethod
    def _offset_trkpt(content: str, x_meters: float, y_meters: float) -> str:
        """偏移航迹点坐标"""
        def offset_trkpt_block(match):
            block = match.group(0)

            lat_match = re.search(r'lat="([^"]+)"', block)
            lon_match = re.search(r'lon="([^"]+)"', block)

            if lat_match and lon_match:
                lat = float(lat_match.group(1))
                lon = float(lon_match.group(1))
                new_lat, new_lon = GpxEditor.offset_coordinates(lat, lon, x_meters, y_meters)
                block = block.replace(f'lat="{lat}"', f'lat="{new_lat}"')
                block = block.replace(f'lon="{lon}"', f'lon="{new_lon}"')

            return block

        return GpxEditor.RE_TRKPT_BLOCK.sub(offset_trkpt_block, content)
