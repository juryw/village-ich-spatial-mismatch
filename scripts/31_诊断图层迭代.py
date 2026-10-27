# -*- coding: utf-8 -*-
"""
31_诊断图层迭代.py → 升级为路网密度主力脚本（在诊断脚本基础上追加完整统计）
已验证：本文件的读取路径（先投影、再 Open、UseExceptions、显式 GetNextFeature）可读到数据。
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from osgeo import ogr

import pyproj
import shapely
from shapely.geometry import shape as shp_shape   # GeoJSON 字典 → 几何（县界用）
from shapely.ops import transform
from shapely import STRtree

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
GPKG = DATA / "中国路网_主干.gpkg"
OUT = DATA / "县域路网.csv"

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 1. 县级边界等积 ----------
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
area_map = {r["adcode"]: float(r["area_km2"]) for r in csv.DictReader(
    open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
counties, adcodes, names = [], [], []
bx0 = by0 = 1e18; bx1 = by1 = -1e18
for f_ in geo["features"]:
    if not f_.get("geometry"):
        continue
    code = str(f_["properties"]["adcode"])
    c = transform(PROJ, shp_shape(f_["geometry"]))
    counties.append(c); adcodes.append(code); names.append(f_["properties"].get("name", ""))
    x0, y0, x1, y1 = c.bounds
    bx0, by0, bx1, by1 = min(bx0, x0), min(by0, y0), max(bx1, x1), max(by1, y1)
print(f"县级单元 {len(counties)} 个，研究区外包框（km）：({bx0/1e3:.0f},{by0/1e3:.0f})~({bx1/1e3:.0f},{by1/1e3:.0f})")

# ---------- 2. 读路网（与诊断一致的可读路径） ----------
ogr.UseExceptions()
ds = ogr.Open(str(GPKG))
layer = ds.GetLayerByName("lines")
print("要素数:", layer.GetFeatureCount())
layer.ResetReading()
roads = []
n_read, n_keep = 0, 0
while True:
    feat = layer.GetNextFeature()
    if feat is None:
        break
    n_read += 1
    geom = feat.GetGeometryRef()
    if geom is None:
        continue
    try:
        g = shapely.from_wkb(bytes(geom.ExportToWkb()))   # 注意：shape() 是 GeoJSON 字典函数，WKB 要用 from_wkb
    except Exception:
        continue
    if g is None or g.is_empty or g.geom_type not in ("LineString", "MultiLineString"):
        continue
    x0, y0, x1, y1 = g.bounds
    if x1 < 70 or x0 > 137 or y1 < 13 or y0 > 56:
        continue
    g = transform(PROJ, g)
    gx0, gy0, gx1, gy1 = g.bounds
    if gx1 < bx0 or gx0 > bx1 or gy1 < by0 or gy0 > by1:
        continue
    roads.append(g)
    n_keep += 1
    if n_read % 500000 == 0:
        print(f"  读 {n_read}，留 {n_keep}")
ds = None
print(f"有效路段 {n_keep} / {n_read}")

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
