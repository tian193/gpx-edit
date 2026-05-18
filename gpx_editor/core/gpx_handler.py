# -*- coding: utf-8 -*-
"""
GPX处理模块
功能: GPX文件读写和基础操作
"""

import gpxpy
import gpxpy.gpx
from datetime import datetime
from typing import List, Optional, Tuple


class GpxHandler:
    """GPX文件处理器"""

    def __init__(self):
        self.gpx = None
        self.filepath = None

    def new(self):
        """创建新的空白GPX"""
        self.gpx = gpxpy.gpx.GPX()
        self.gpx.name = "新建GPX文件"
        self.gpx.description = "由GPX编辑器创建"
        self.gpx.version = "1.1"
        self.filepath = None
        return self.gpx

    def load(self, filepath: str) -> gpxpy.gpx.GPX:
        """加载GPX文件，支持多种编码"""
        for encoding in ['utf-8', 'gbk', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    self.gpx = gpxpy.parse(f)
                self.filepath = filepath
                return self.gpx
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"无法解析文件: {filepath}")

    def save(self, filepath: Optional[str] = None):
        """保存GPX文件"""
        if self.gpx is None:
            raise ValueError("没有GPX数据可保存")

        save_path = filepath or self.filepath
        if save_path is None:
            raise ValueError("未指定保存路径")

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(self.gpx.to_xml())

        self.filepath = save_path

    def get_waypoints(self) -> List[gpxpy.gpx.GPXWaypoint]:
        """获取所有航点"""
        if self.gpx is None:
            return []
        return self.gpx.waypoints

    def get_tracks(self) -> List[gpxpy.gpx.GPXTrack]:
        """获取所有航迹"""
        if self.gpx is None:
            return []
        return self.gpx.tracks

    def add_waypoint(self, name: str, latitude: float, longitude: float,
                     elevation: Optional[float] = None,
                     description: Optional[str] = None) -> gpxpy.gpx.GPXWaypoint:
        """添加航点"""
        if self.gpx is None:
            self.new()

        waypoint = gpxpy.gpx.GPXWaypoint(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            name=name,
            description=description,
            time=datetime.now()
        )
        self.gpx.waypoints.append(waypoint)
        return waypoint

    def remove_waypoint(self, index: int):
        """删除航点"""
        if self.gpx and 0 <= index < len(self.gpx.waypoints):
            self.gpx.waypoints.pop(index)

    def add_track(self, name: str, points: List[Tuple[float, float, Optional[float]]]) -> gpxpy.gpx.GPXTrack:
        """添加航迹
        points: [(lat, lon, ele), ...]
        """
        if self.gpx is None:
            self.new()

        track = gpxpy.gpx.GPXTrack()
        track.name = name

        segment = gpxpy.gpx.GPXTrackSegment()
        for lat, lon, ele in points:
            point = gpxpy.gpx.GPXTrackPoint(
                latitude=lat,
                longitude=lon,
                elevation=ele
            )
            segment.points.append(point)

        track.segments.append(segment)
        self.gpx.tracks.append(track)
        return track

    def remove_track(self, index: int):
        """删除航迹"""
        if self.gpx and 0 <= index < len(self.gpx.tracks):
            self.gpx.tracks.pop(index)

    def get_track_points(self, track_index: int) -> List[gpxpy.gpx.GPXTrackPoint]:
        """获取航迹所有点列表（跨所有段）"""
        if self.gpx and 0 <= track_index < len(self.gpx.tracks):
            track = self.gpx.tracks[track_index]
            all_points = []
            for segment in track.segments:
                all_points.extend(segment.points)
            return all_points
        return []

    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """获取边界 (min_lat, min_lon, max_lat, max_lon)"""
        if self.gpx is None:
            return None

        bounds = self.gpx.get_bounds()
        if bounds:
            return (bounds.min_latitude, bounds.min_longitude,
                    bounds.max_latitude, bounds.max_longitude)
        return None
