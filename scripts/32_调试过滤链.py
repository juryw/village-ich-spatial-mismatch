# -*- coding: utf-8 -*-
"""32_调试过滤链.py：前20条路段逐级打印过滤值，定位拦截点"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from osgeo import ogr

import pyproj
from shapely.geometry import shape as shp_shape
from shapely.ops import transform

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

ogr.UseExceptions()
ds = ogr.Open(r"E:\GLM\非遗论文\02_数据\03_基础地理\中国路网_主干.gpkg")
layer = ds.GetLayerByName("lines")
layer.ResetReading()

bx0, by0, bx1, by1 = -2.625e6, 4.08e5, 2.208e6, 5.922e6   # 31号算出的研究区等积外包框（米）

for i in range(20):
    feat = layer.GetNextFeature()
    geom = feat.GetGeometryRef()
    g = shp_shape(bytes(geom.ExportToWkb()))
    deg = g.bounds
    if g.geom_type not in ("LineString", "MultiLineString"):
        print(f"{i}: 类型拦截 {g.geom_type}")
        continue
    if deg[2] < 70 or deg[0] > 137 or deg[3] < 13 or deg[1] > 56:
        print(f"{i}: 经纬度拦截 bounds={deg}")
        continue
    ga = transform(PROJ, g)
    ab = ga.bounds
    verdict = "保留" if not (ab[2] < bx0 or ab[0] > bx1 or ab[3] < by0 or ab[1] > by1) else "外包框拦截"
    print(f"{i}: deg={tuple(round(v,3) for v in deg)} → aea={tuple(round(v/1e3,1) for v in ab)}km → {verdict}")
