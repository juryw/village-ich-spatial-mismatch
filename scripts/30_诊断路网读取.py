# -*- coding: utf-8 -*-
"""30_诊断路网读取.py：三步定位——图层要素数、单要素WKB类型、shapely解析"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from osgeo import ogr

GPKG = r"E:\GLM\非遗论文\02_数据\03_基础地理\中国路网_主干.gpkg"
ogr.UseExceptions()
ds = ogr.Open(GPKG)
print("驱动:", ds.GetDriver().GetName())
layer = ds.GetLayerByName("lines")
print("要素数:", layer.GetFeatureCount())
layer.ResetReading()
for i in range(3):
    feat = layer.GetNextFeature()
    if feat is None:
        print(f"第{i}个: None")
        continue
    geom = feat.GetGeometryRef()
    print(f"第{i}个: geom类型={geom.GetGeometryName()}, "
          f"wkb字节数={len(geom.ExportToWkb())}, name={feat.GetField('name')!r}")
    import shapely
    g = shapely.from_wkb(bytes(geom.ExportToWkb()))
    print("  shapely解析:", g.geom_type, g.bounds)
ds = None
