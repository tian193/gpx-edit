# -*- coding: utf-8 -*-
"""
坐标转换模块
功能: WGS84↔CGCS2000投影坐标转换、天地图瓦片URL生成
"""

import math
from typing import Tuple


class CoordConverter:
    """坐标转换器"""

    @staticmethod
    def get_zone_number(longitude: float) -> int:
        """计算6度带带号"""
        return int(math.floor(longitude / 6)) + 1

    @staticmethod
    def get_central_meridian(zone_number: int) -> float:
        """计算中央经线"""
        return zone_number * 6 - 3

    @staticmethod
    def wgs84_to_cgcs2000(latitude: float, longitude: float) -> Tuple[float, float, int]:
        """WGS84经纬度转CGCS2000投影坐标"""
        try:
            from pyproj import Transformer
            zone = CoordConverter.get_zone_number(longitude)
            central_meridian = CoordConverter.get_central_meridian(zone)
            proj_string = (
                f"+proj=tmerc +lat_0=0 +lon_0={central_meridian} +k=1 +x_0=500000 +y_0=0 "
                f"+ellps=GRS80 +units=m +no_defs"
            )
            transformer = Transformer.from_crs("EPSG:4326", proj_string, always_xy=True)
            x, y = transformer.transform(longitude, latitude)
            return x, y, zone
        except ImportError:
            return CoordConverter._wgs84_to_cgcs2000_fallback(latitude, longitude)

    @staticmethod
    def cgcs2000_to_wgs84(x: float, y: float, zone: int) -> Tuple[float, float]:
        """CGCS2000投影坐标转WGS84经纬度"""
        try:
            from pyproj import Transformer
            central_meridian = CoordConverter.get_central_meridian(zone)
            proj_string = (
                f"+proj=tmerc +lat_0=0 +lon_0={central_meridian} +k=1 +x_0=500000 +y_0=0 "
                f"+ellps=GRS80 +units=m +no_defs"
            )
            transformer = Transformer.from_crs(proj_string, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            return lat, lon
        except ImportError:
            return CoordConverter._cgcs2000_to_wgs84_fallback(x, y, zone)

    @staticmethod
    def _wgs84_to_cgcs2000_fallback(latitude: float, longitude: float) -> Tuple[float, float, int]:
        """备用坐标转换（不依赖pyproj）"""
        zone = CoordConverter.get_zone_number(longitude)
        central_meridian = CoordConverter.get_central_meridian(zone)

        a = 6378137.0
        f = 1 / 298.257222101
        e2 = 2 * f - f * f
        ep2 = e2 / (1 - e2)

        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)
        lon0_rad = math.radians(central_meridian)

        N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
        t = math.tan(lat_rad)
        eta2 = ep2 * math.cos(lat_rad) ** 2

        l = lon_rad - lon0_rad

        x = N * math.cos(lat_rad) * l + \
            N * math.cos(lat_rad) ** 3 * t * (1 - t ** 2 + eta2) * l ** 3 / 6

        A0 = 1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256
        A2 = 3 / 8 * (e2 + e2 ** 2 / 4 + 15 * e2 ** 3 / 128)
        A4 = 15 / 256 * (e2 ** 2 + 3 * e2 ** 3 / 4)
        A6 = 35 * e2 ** 3 / 3072

        X = a * (A0 * lat_rad - A2 * math.sin(2 * lat_rad) + A4 * math.sin(4 * lat_rad) - A6 * math.sin(6 * lat_rad))

        y = X + N * math.sin(lat_rad) * math.cos(lat_rad) * l ** 2 / 2 + \
            N * math.sin(lat_rad) * math.cos(lat_rad) ** 3 * (5 - t ** 2 + 9 * eta2 + 4 * eta2 ** 2) * l ** 4 / 24

        x_final = x + 500000

        return x_final, y, zone

    @staticmethod
    def _cgcs2000_to_wgs84_fallback(x: float, y: float, zone: int) -> Tuple[float, float]:
        """备用反算（不依赖pyproj）"""
        x_adj = x - 500000

        a = 6378137.0
        f = 1 / 298.257222101
        e2 = 2 * f - f * f

        lat = y / a
        for _ in range(10):
            lat_new = (y + a * e2 * math.sin(lat) * math.cos(lat)) / a
            if abs(lat_new - lat) < 1e-12:
                break
            lat = lat_new

        lat_deg = math.degrees(lat)

        central_meridian = CoordConverter.get_central_meridian(zone)
        N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lon = central_meridian + math.degrees(x_adj / (N * math.cos(lat)))

        return lat_deg, lon

    @staticmethod
    def format_cgcs2000(latitude: float, longitude: float) -> str:
        """格式化输出CGCS2000坐标"""
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(latitude, longitude)
        return f"{zone}带 X={x:.3f} Y={y:.3f}"


class TiandituTileProvider:
    """天地图瓦片服务提供器"""

    TILE_URLS = {
        "vec": "http://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
        "img": "http://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
        "cia": "http://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk={tk}",
    }

    @staticmethod
    def get_tile_url(layer: str, api_key: str) -> str:
        if layer not in TiandituTileProvider.TILE_URLS:
            raise ValueError(f"不支持的图层类型: {layer}")
        url = TiandituTileProvider.TILE_URLS[layer]
        url = url.replace("{tk}", api_key)
        return url

    @staticmethod
    def get_road_url(api_key: str) -> str:
        return TiandituTileProvider.get_tile_url("vec", api_key)

    @staticmethod
    def get_satellite_url(api_key: str) -> str:
        return TiandituTileProvider.get_tile_url("img", api_key)

    @staticmethod
    def get_annotation_url(api_key: str) -> str:
        return TiandituTileProvider.get_tile_url("cia", api_key)
