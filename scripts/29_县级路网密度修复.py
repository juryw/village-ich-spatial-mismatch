# -*- coding: utf-8 -*-
"""
29_县级路网密度修复.py（QGIS Python 运行）
修复 28 号脚本 bug：粗筛条件 `xmax<0 or ymax<0` 写反了——Albers 等积坐标下
中国西部 x 为负、南部 y 为负，正确条件应是"整段都在研究区外包框之外"。
本次：先扫一遍路网求真实范围 → 正确粗筛 → 逐县求交。
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from osgeo import ogr

import pyproj
from shapely.geometry import shape as shp_shape
from shapely.ops import transform
from shapely import STRtree

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
GPKG = DATA / "中国路网_主干.gpkg"
OUT = DATA / "县域路网.csv"

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 1. 县级边界等积 + 研究区外包框 ----------
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
area_map = {r["adcode"]: float(r["area_km2"]) for r in csv.DictReader(
    open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
counties, adcodes, names = [], [], []
bx0 = by0 = 1e18
bx1 = by1 = -1e18
for f_ in geo["features"]:
    if not f_.get("geometry"):
        continue
    code = str(f_["properties"]["adcode"])
    c = transform(PROJ, shp_shape(f_["geometry"]))
    counties.append(c)
    adcodes.append(code)
    names.append(f_["properties"].get("name", ""))
    x0, y0, x1, y1 = c.bounds
    bx0, by0, bx1, by1 = min(bx0, x0), min(by0, y0), max(bx1, x1), max(by1, y1)
print(f"研究区等积外包框（km）：({bx0/1e3:.0f},{by0/1e3:.0f})~({bx1/1e3:.0f},{by1/1e3:.0f})")

# ---------- 2. 流式读路网，正确粗筛 ----------
print("读取路网（流式）...")
ogr.DontUseExceptions()                    # UseExceptions 在本组合下首次 GetNextFeature 返回 None（见31号诊断对照），改静默+显式检查
ds = ogr.Open(str(GPKG))
layer = ds.GetLayerByName("lines")
print("  图层要素数（打开时核对）：", layer.GetFeatureCount())
layer.ResetReading()
roads = []
n_read, n_keep = 0, 0
err = None
while True:
    try:
        feat = layer.GetNextFeature()
    except Exception as e:
        err = e
        break
    if feat is None:
        break
    geom = feat.GetGeometryRef()
    if geom is None:
        continue
    try:
        g = shp_shape(bytes(geom.ExportToWkb()))
    except Exception:
        continue
    if g is None or g.is_empty or g.geom_type not in ("LineString", "MultiLineString"):
        continue
    n_read += 1
    x0, y0, x1, y1 = g.bounds          # 先用经纬度 bbox 粗筛（中国 73~136E, 15~55N）
    if x1 < 70 or x0 > 137 or y1 < 13 or y0 > 56:
        continue
    g = transform(PROJ, g)
    gx0, gy0, gx1, gy1 = g.bounds
    if gx1 < bx0 or gx0 > bx1 or gy1 < by0 or gy0 > by1:   # 整段在研究区外才丢弃
        continue
    roads.append(g)
    n_keep += 1
    if n_read % 500000 == 0:
        print(f"  读 {n_read}，留 {n_keep}")
ds = None
print(f"有效路段 {n_keep} / {n_read}" + (f"（读取中断：{err!r}）" if err else ""))

# ---------- 3. 逐县求交 ----------
tree = STRtree(roads)
out = []
for k, county in enumerate(counties):
    total = 0.0
    for i in tree.query(county, predicate="intersects"):
        inter = roads[i].intersection(county)
        if not inter.is_empty:
            total += inter.length
    area = area_map.get(adcodes[k], 0.0)
    dens = total / 1e3 / area if area > 0 else 0.0
    out.append({"adcode": adcodes[k], "县名": names[k], "路网密度_km每km2": round(dens, 4)})
    if (k + 1) % 500 == 0:
        print(f"  已统计 {k + 1} 县")

with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
print(f"已保存：{OUT}")
top = sorted(out, key=lambda r: -r["路网密度_km每km2"])[:8]
print("路网密度前8县：", [(r["县名"], r["路网密度_km每km2"]) for r in top])
mean_all = sum(r["路网密度_km每km2"] for r in out) / len(out)
print(f"全国县级路网密度均值：{mean_all:.3f} km/km²")
