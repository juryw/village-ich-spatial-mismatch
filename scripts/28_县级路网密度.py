# -*- coding: utf-8 -*-
"""
28_县级路网密度.py（用 QGIS 自带 Python 运行：E:\\QGIS\\bin\\python-qgis.bat 本文件）
作用：主干路网 GPKG（234万段）→ 与县级边界求交 → 每县路网长度/面积 = 密度(km/km²)。
原理：osgeo.ogr 流式读路段（等积投影坐标由 pyproj 现算），shapely STRtree 空间索引加速。
输出：县域路网.csv
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from osgeo import ogr

import pyproj
from shapely.geometry import shape as shp_shape, LineString
from shapely.ops import transform
from shapely import STRtree

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
GPKG = DATA / "中国路网_主干.gpkg"
OUT = DATA / "县域路网.csv"

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 1. 县级边界（等积） ----------
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
area_map = {r["adcode"]: float(r["area_km2"]) for r in csv.DictReader(
    open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
counties, adcodes, names = [], [], []
for f_ in geo["features"]:
    if not f_.get("geometry"):
        continue
    code = str(f_["properties"]["adcode"])
    adcodes.append(code)
    names.append(f_["properties"].get("name", ""))
    counties.append(transform(PROJ, shp_shape(f_["geometry"])))
print(f"县级单元 {len(counties)} 个")

# ---------- 2. 流式读路网 → 等积 → 只保留粗筛后的段 ----------
print("读取路网（流式，约几分钟）...")
ogr.RegisterAll()
ds = ogr.Open(str(GPKG))
layer = ds.GetLayerByName("lines")
roads = []
n_read = 0
for feat in layer:
    geom = feat.GetGeometryRef()
    if geom is None:
        continue
    wkb = geom.ExportToWkb()
    try:
        g = shp_shape(wkb)
    except Exception:
        continue
    if g is None or g.is_empty or g.geom_type not in ("LineString", "MultiLineString"):
        continue
    g = transform(PROJ, g)
    xmin, ymin, xmax, ymax = g.bounds
    if xmax < 0 or ymax < 0:          # 粗筛：不可能落在中国范围
        continue
    roads.append(g)
    n_read += 1
    if n_read % 500000 == 0:
        print(f"  已处理 {n_read} 段")
ds = None
print(f"有效路段 {len(roads)} 条")

# ---------- 3. STRtree 逐县求交 ----------
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
