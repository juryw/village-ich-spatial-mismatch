# -*- coding: utf-8 -*-
"""
19_GDP逐县汇总.py
作用：把公里网格 GDP（2020，单位待验证）按县汇总：
     每县 GDP 总量（格网值求和）与 GDP 密度（格网值求均值），
     并跑一版加了经济因子的地理探测器。
原理：栅格化的县级编号 × 格网值 → np.bincount 分组求和/均值（分区统计）。
验证：全国总量应约等于 2020 年中国 GDP ≈ 101.6 万亿元（若单位为万元）。
"""
import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy import stats as sps
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform
import pyproj

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
OUT = DATA / "县域GDP_2020.csv"

# ---------- 1. 读栅格与县级边界，边界重投影到栅格坐标系 ----------
ras = rasterio.open(DATA / "gdp2020_1km.tif")
print(f"GDP 栅格：{ras.width}×{ras.height}，范围 {ras.bounds}")
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))

proj_to_ras = pyproj.Transformer.from_crs(
    "EPSG:4326", ras.crs.to_proj4(), always_xy=True).transform

adcodes, shapes = [], []
for f in geo["features"]:
    if not f.get("geometry"):
        continue
    adcodes.append(str(f["properties"]["adcode"]))
    shapes.append(mapping(shp_transform(proj_to_ras, shape(f["geometry"]))))
adcode_index = {code: k + 1 for k, code in enumerate(adcodes)}   # 0 留给"县外"

# ---------- 2. 栅格化县编号（像素中心落在哪个县） ----------
county_raster = rasterize(
    [(shapes[k], adcode_index[adcodes[k]]) for k in range(len(shapes))],
    out_shape=ras.shape, transform=ras.transform, fill=0, dtype="int32", all_touched=False)

band = ras.read(1).astype("float64")
band[band < 0] = np.nan                      # nodata 为 -3.4e38
valid = ~np.isnan(band)

# ---------- 3. 分组汇总 ----------
n = len(adcodes) + 1
flat_idx = county_raster.ravel()
flat_val = np.where(valid.ravel(), band.ravel(), 0.0)
gdp_sum = np.bincount(flat_idx, weights=flat_val, minlength=n)          # 总量（万元/km²×km²=万元）
cell_cnt = np.bincount(flat_idx, minlength=n)                            # 落在各县的像元数
valid_cnt = np.bincount(flat_idx, weights=valid.ravel().astype(float), minlength=n)
gdp_mean = np.divide(gdp_sum, valid_cnt, out=np.zeros(n), where=valid_cnt > 0)

national = np.nansum(band)
print(f"全国格网 GDP 合计：{national:,.0f}（单位若为万元 → {national / 1e8:,.1f} 万亿元；"
      f"2020 实际约 101.6 万亿元）")

rows = []
for k, code in enumerate(adcodes):
    rows.append({"adcode": code,
                 "GDP_万元": round(gdp_sum[k + 1], 1),
                 "GDP密度_万元每km2": round(gdp_mean[k + 1], 4),
                 "有效像元数": int(valid_cnt[k + 1])})
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"已保存：{OUT}")

name_map = {str(f["properties"]["adcode"]): f["properties"].get("name", "") for f in geo["features"]}
top = sorted(rows, key=lambda r: -r["GDP_万元"])[:8]
print("GDP 总量前 8 县（单位亿元）：",
      [(name_map.get(r["adcode"], "?"), round(r["GDP_万元"] / 1e4, 1)) for r in top])

# ---------- 4. 探测器升级预演：加入经济因子 ----------
drv = {r["adcode"]: r for r in csv.DictReader(open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
common = [r for r in rows if r["adcode"] in drv]
Y_v = np.array([float(drv[r["adcode"]]["village"]) / float(drv[r["adcode"]]["area_km2"]) * 1000
                for r in common])
Y_i = np.array([float(drv[r["adcode"]]["ich"]) / float(drv[r["adcode"]]["area_km2"]) * 1000
                for r in common])

def quantile_classes(x, m=5):
    edges = np.quantile(x, np.linspace(0, 1, m + 1)[1:-1])
    return np.searchsorted(edges, x, side="right")

X = {
    "GDP密度": quantile_classes(np.array([r["GDP密度_万元每km2"] for r in common])),
    "民族自治地方": np.array([float(drv[r["adcode"]]["ethnic"]) for r in common]),
    "距省会距离": quantile_classes(np.array([float(drv[r["adcode"]]["d_capital"]) for r in common])),
    "县域面积": quantile_classes(np.array([float(drv[r["adcode"]]["area_km2"]) for r in common])),
    "纬度位置": quantile_classes(np.array([float(drv[r["adcode"]]["lat"]) for r in common])),
}

def q_stat(y, x):
    sst = ((y - y.mean()) ** 2).sum()
    ssw = sum(len(y[x == h]) * y[x == h].var() for h in np.unique(x))
    return 1 - ssw / sst

print("\n【加入 GDP 后的因子探测 q 值（预演，人口/海拔/路网未进）】")
for yn, y in (("村落密度", Y_v), ("非遗密度", Y_i)):
    line = f"  {yn}: "
    for xn, x in X.items():
        line += f"{xn} {q_stat(y, x):.3f}｜"
    print(line)
