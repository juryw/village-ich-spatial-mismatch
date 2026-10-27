# -*- coding: utf-8 -*-
"""
10_修复县级边界几何.py
背景：QGIS「统计多边形中的点数」报"9 个要素为无效几何图形"——
     边界数据里有少量多边形自相交（数据源/合并过程引入的小瑕疵）。
作用：用 shapely 库逐个检查县级多边形，找出无效的并自动修复
     （make_valid），输出"中国_县级边界_修复.geojson"供 QGIS 使用。
"""
import json
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.validation import explain_validity, make_valid

SRC = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理\中国_县级边界.geojson")
DST = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理\中国_县级边界_修复.geojson")

geo = json.loads(SRC.read_text(encoding="utf-8"))
fixed, broken = 0, []
out_features = []
for feat in geo["features"]:
    geom = feat.get("geometry")
    if not geom:
        out_features.append(feat)
        continue
    shp = shape(geom)
    if shp.is_valid:
        out_features.append(feat)
        continue
    reason = explain_validity(shp)
    repaired = make_valid(shp)
    # make_valid 可能产生 GeometryCollection，只保留面状部分
    if repaired.geom_type == "GeometryCollection":
        parts = [g for g in repaired.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not parts:
            broken.append((feat["properties"].get("name"), reason, "无法修复"))
            continue
        from shapely.ops import unary_union
        repaired = unary_union(parts)
    feat["geometry"] = mapping(repaired)
    out_features.append(feat)
    fixed += 1
    broken.append((feat["properties"].get("name"), reason, "已修复"))

DST.write_text(
    json.dumps({"type": "FeatureCollection", "features": out_features}, ensure_ascii=False),
    encoding="utf-8")

print(f"总要素 {len(geo['features'])} 个；修复 {fixed} 个无效几何")
for name, reason, status in broken:
    print(f"  {name}：{reason}（{status}）")
print(f"已保存：{DST}")
