# -*- coding: utf-8 -*-
"""
坐标转换模块测试
"""

import pytest
from gpx_editor.core.coord_converter import CoordConverter


class TestCoordConverter:
    """坐标转换器测试"""

    def test_get_zone_number(self):
        """测试带号计算"""
        # 经度116° → 20带
        assert CoordConverter.get_zone_number(116.654321) == 20
        # 经度117° → 20带
        assert CoordConverter.get_zone_number(117.0) == 20
        # 经度120° → 21带
        assert CoordConverter.get_zone_number(120.0) == 21

    def test_wgs84_to_cgcs2000(self):
        """测试WGS84转CGCS2000投影坐标"""
        # 北京天安门附近: 纬度39.9042, 经度116.4074
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(39.9042, 116.4074)
        assert zone == 20
        # X（东向）应该在 400000-500000 范围
        assert 400000 < x < 500000
        # Y（北向）应该在 4400000-4500000 范围
        assert 4400000 < y < 4500000

    def test_cgcs2000_to_wgs84(self):
        """测试CGCS2000投影坐标转WGS84"""
        # 先转过去再转回来，验证往返一致性
        lat_orig, lon_orig = 39.9042, 116.4074
        x, y, zone = CoordConverter.wgs84_to_cgcs2000(lat_orig, lon_orig)
        lat_back, lon_back = CoordConverter.cgcs2000_to_wgs84(x, y, zone)
        # 精度到小数点后6位（约0.1米）
        assert abs(lat_orig - lat_back) < 0.000001
        assert abs(lon_orig - lon_back) < 0.000001

    def test_format_cgcs2000(self):
        """测试格式化输出"""
        result = CoordConverter.format_cgcs2000(39.9042, 116.4074)
        assert "20带" in result
        assert "X=" in result
        assert "Y=" in result
