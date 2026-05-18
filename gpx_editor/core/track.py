# -*- coding: utf-8 -*-
"""
航迹操作模块
功能: 航迹数据处理和操作
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..utils.helpers import haversine_distance


@dataclass
class TrackPoint:
    """航迹点数据"""
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    time: Optional[str] = None


@dataclass
class TrackData:
    """航迹数据"""
    name: str
    segments: List[List[TrackPoint]]

    @property
    def total_points(self) -> int:
        """总点数"""
        return sum(len(seg) for seg in self.segments)


class TrackManager:
    """航迹管理器"""

    @classmethod
    def haversine(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离(米)"""
        return haversine_distance(lat1, lon1, lat2, lon2)

    @classmethod
    def calculate_distance(cls, points: List[TrackPoint]) -> float:
        """计算航迹总距离(米)"""
        if len(points) < 2:
            return 0.0

        total = 0.0
        for i in range(1, len(points)):
            total += cls.haversine(
                points[i-1].latitude, points[i-1].longitude,
                points[i].latitude, points[i].longitude
            )
        return total

    @classmethod
    def calculate_elevation_gain(cls, points: List[TrackPoint]) -> float:
        """计算累计爬升(米)"""
        if len(points) < 2:
            return 0.0

        gain = 0.0
        for i in range(1, len(points)):
            if points[i].elevation is not None and points[i-1].elevation is not None:
                diff = points[i].elevation - points[i-1].elevation
                if diff > 0:
                    gain += diff
        return gain

    @classmethod
    def calculate_elevation_loss(cls, points: List[TrackPoint]) -> float:
        """计算累计下降(米)"""
        if len(points) < 2:
            return 0.0

        loss = 0.0
        for i in range(1, len(points)):
            if points[i].elevation is not None and points[i-1].elevation is not None:
                diff = points[i-1].elevation - points[i].elevation
                if diff > 0:
                    loss += diff
        return loss

    @staticmethod
    def simplify_douglas_peucker(points: List[TrackPoint], epsilon: float) -> List[TrackPoint]:
        """Douglas-Peucker算法简化航迹
        epsilon: 容差(米)
        """
        if len(points) <= 2:
            return points

        # 找到距离首尾连线最远的点
        dmax = 0
        index = 0

        start = points[0]
        end = points[-1]

        for i in range(1, len(points) - 1):
            d = TrackManager._point_to_line_distance(points[i], start, end)
            if d > dmax:
                dmax = d
                index = i

        # 如果最大距离大于容差，递归简化
        if dmax > epsilon:
            left = TrackManager.simplify_douglas_peucker(points[:index+1], epsilon)
            right = TrackManager.simplify_douglas_peucker(points[index:], epsilon)
            return left[:-1] + right
        else:
            return [start, end]

    @staticmethod
    def _point_to_line_distance(point: TrackPoint, line_start: TrackPoint, line_end: TrackPoint) -> float:
        """计算点到线段的距离(米)"""
        # 简化计算，使用投影距离
        A = point.latitude - line_start.latitude
        B = point.longitude - line_start.longitude
        C = line_end.latitude - line_start.latitude
        D = line_end.longitude - line_start.longitude

        dot = A * C + B * D
        len_sq = C * C + D * D

        if len_sq == 0:
            return TrackManager.haversine(
                point.latitude, point.longitude,
                line_start.latitude, line_start.longitude
            )

        param = dot / len_sq

        if param < 0:
            return TrackManager.haversine(
                point.latitude, point.longitude,
                line_start.latitude, line_start.longitude
            )
        elif param > 1:
            return TrackManager.haversine(
                point.latitude, point.longitude,
                line_end.latitude, line_end.longitude
            )
        else:
            return TrackManager.haversine(
                point.latitude, point.longitude,
                line_start.latitude + param * C,
                line_start.longitude + param * D
            )

    @staticmethod
    def remove_duplicates(points: List[TrackPoint], threshold: float = 0.0001) -> List[TrackPoint]:
        """去除重复点
        threshold: 坐标差值阈值
        """
        if not points:
            return points

        result = [points[0]]
        for i in range(1, len(points)):
            if (abs(points[i].latitude - points[i-1].latitude) > threshold or
                abs(points[i].longitude - points[i-1].longitude) > threshold):
                result.append(points[i])

        return result

    @staticmethod
    def merge_tracks(tracks: List[List[TrackPoint]]) -> List[TrackPoint]:
        """合并多条航迹"""
        result = []
        for track in tracks:
            result.extend(track)
        return result

    @staticmethod
    def split_track(points: List[TrackPoint], index: int) -> Tuple[List[TrackPoint], List[TrackPoint]]:
        """分割航迹"""
        if index < 0 or index >= len(points):
            return points, []
        return points[:index+1], points[index:]

    # === gpxpy对象直接操作方法 ===

    @staticmethod
    def simplify_gpx_track(track, epsilon: float):
        """简化gpxpy GPXTrack对象
        对每个段分别运行Douglas-Peucker算法
        """
        import gpxpy.gpx
        for segment in track.segments:
            if len(segment.points) <= 2:
                continue
            simplified = TrackManager.simplify_douglas_peucker(segment.points, epsilon)
            segment.points.clear()
            segment.points.extend(simplified)

    @staticmethod
    def merge_gpx_tracks(tracks, name: str = "合并航迹"):
        """合并多条gpxpy GPXTrack为一条
        返回新的GPXTrack对象
        """
        import gpxpy.gpx
        merged = gpxpy.gpx.GPXTrack()
        merged.name = name
        for track in tracks:
            for segment in track.segments:
                new_seg = gpxpy.gpx.GPXTrackSegment()
                new_seg.points.extend(segment.points)
                merged.segments.append(new_seg)
        return merged

    @staticmethod
    def split_gpx_track(track, segment_index: int, point_index: int):
        """在指定位置分割gpxpy GPXTrack
        返回两个新的GPXTrack对象
        """
        import gpxpy.gpx
        if segment_index < 0 or segment_index >= len(track.segments):
            return track, None

        seg = track.segments[segment_index]
        if point_index < 0 or point_index >= len(seg.points):
            return track, None

        # 前半部分
        track1 = gpxpy.gpx.GPXTrack()
        track1.name = (track.name or "航迹") + " (前段)"
        for i in range(segment_index):
            new_seg = gpxpy.gpx.GPXTrackSegment()
            new_seg.points.extend(track.segments[i].points)
            track1.segments.append(new_seg)
        # 当前段的前半部分
        seg1 = gpxpy.gpx.GPXTrackSegment()
        seg1.points.extend(seg.points[:point_index + 1])
        track1.segments.append(seg1)

        # 后半部分
        track2 = gpxpy.gpx.GPXTrack()
        track2.name = (track.name or "航迹") + " (后段)"
        # 当前段的后半部分
        seg2 = gpxpy.gpx.GPXTrackSegment()
        seg2.points.extend(seg.points[point_index:])
        track2.segments.append(seg2)
        for i in range(segment_index + 1, len(track.segments)):
            new_seg = gpxpy.gpx.GPXTrackSegment()
            new_seg.points.extend(track.segments[i].points)
            track2.segments.append(new_seg)

        return track1, track2

    @staticmethod
    def get_track_total_distance(track) -> float:
        """计算gpxpy GPXTrack的总距离(米)"""
        total = 0.0
        for segment in track.segments:
            total += TrackManager.calculate_distance(segment.points)
        return total

    @staticmethod
    def get_track_point_count(track) -> int:
        """获取gpxpy GPXTrack的总点数"""
        return sum(len(seg.points) for seg in track.segments)
