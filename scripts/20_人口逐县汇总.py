# -*- coding: utf-8 -*-
"""
20_人口逐县汇总.py
作用：从 WorldPop 2020 全球 1km 人口栅格（30弧秒，EPSG:4326，像元值=人数）
     开窗读取中国范围，按县分区统计人口总量与密度。
验证：全国合计应接近 2020 年中国人口 ~14.1 亿（非约束模型可能有偏差，记录实际值）。
"""
import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
OUT = DATA / "县域人口_2020.csv"

ras = rasterio.open(DATA / "worldpop_ppp_2020_1km.tif")
print(f"全球栅格 {ras.width}×{ras.height}")

# ---------- 1. 中国范围开窗（留一点余量） ----------
bounds = (73, 14, 137, 55)
win = from_bounds(*bounds, transform=ras.transform)
win = win.round_offsets().round_lengths()
transform = ras.window_transform(win)
band = ras.read(1, window=win).astype("float64")
band[band < 0] = 0.0                      # nodata → 0（无人区）
print(f"中国窗口 {band.shape[1]}×{band.shape[0]}，全国格网合计 {band.sum() / 1e8:.2f} 亿人")

# ---------- 2. 栅格化县编号（栅格与边界同为 EPSG:4326，无需重投影） ----------
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
adcodes, shapes = [], []
for f in geo["features"]:
    if not f.get("geometry"):
        continue
    adcodes.append(str(f["properties"]["adcode"]))
    shapes.append(f["geometry"])
idx_of = {code: k + 1 for k, code in enumerate(adcodes)}    # 0 = 县外

county_raster = rasterize(
    [(shapes[k], idx_of[adcodes[k]]) for k in range(len(shapes))],
    out_shape=band.shape, transform=transform, fill=0, dtype="int32")

flat_idx = county_raster.ravel()
pop_sum = np.bincount(flat_idx, weights=band.ravel(), minlength=len(adcodes) + 1)
cell_cnt = np.bincount(flat_idx, minlength=len(adcodes) + 1)

# ---------- 3. 面积（从驱动因子表取，保持口径一致）+ 密度 ----------
area = {r["adcode"]: float(r["area_km2"]) for r in csv.DictReader(
    open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
name_map = {str(f["properties"]["adcode"]): f["properties"].get("name", "") for f in geo["features"]}

rows = []
for k, code in enumerate(adcodes):
    pop = pop_sum[k + 1]
    a = area.get(code, cell_cnt[k + 1] * ras.res[0] * 111 * 31)   # 面积缺失时用像元数近似
    rows.append({"adcode": code, "县名": name_map.get(code, ""),
                 "人口_人": int(round(pop)),
                 "人口密度_人每km2": round(pop / a, 2) if a > 0 else 0})

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"已保存：{OUT}")

total_in_counties = sum(r["人口_人"] for r in rows)
print(f"落入县级单元的人口合计：{total_in_counties / 1e8:.2f} 亿")
top = sorted(rows, key=lambda r: -r["人口_人"])[:8]
print("人口前 8 县：", [(r["县名"], f"{r['人口_人']/1e4:.0f}万") for r in top])
