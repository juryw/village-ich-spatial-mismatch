# -*- coding: utf-8 -*-
"""
24_修复海拔统计.py
问题：22 号脚本把 terrarium 瓦片的"无数据/透明"编码（≈-32768m）当真实高程，
     导致西部县平均海拔出现 -32619m 之类的荒谬值。
修复：像元有效性 = 高程 > -1000m 且 PNG alpha 有效（这里从拼接结果上直接用高程阈值），
     重新做分区统计；抽查已知县（拉萨城关≈3650m、玛多≈4250m、歙县≈300m、崇明≈4m）验证。
"""
import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
import pyproj

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")

ras = rasterio.open(DATA / "dem_china_z7_3857.tif")
mosaic = ras.read(1)
valid = mosaic > -1000.0                     # 陆地有效高程；海面附近的真实值 > -1000
print(f"有效像元占比：{valid.mean() * 100:.1f}%")

geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
to3857 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
adcodes, shapes = [], []
for f_ in geo["features"]:
    if f_.get("geometry"):
        adcodes.append(str(f_["properties"]["adcode"]))
        shapes.append(shp_transform(to3857, shape(f_["geometry"])))
idx_of = {c: k + 1 for k, c in enumerate(adcodes)}

mask = rasterize([(shapes[k], idx_of[adcodes[k]]) for k in range(len(shapes))],
                 out_shape=mosaic.shape, transform=ras.transform, fill=0, dtype="int32")
flat, val, ok = mask.ravel(), mosaic.ravel(), valid.ravel()
n = len(adcodes) + 1
cnt_all = np.bincount(flat, minlength=n)
cnt_ok = np.bincount(flat, weights=ok.astype(float), minlength=n)
s = np.bincount(flat, weights=np.where(ok, val, 0), minlength=n)
s2 = np.bincount(flat, weights=np.where(ok, val * val, 0), minlength=n)
mean = np.divide(s, cnt_ok, out=np.full(n, np.nan), where=cnt_ok > 0)
var = np.divide(s2, cnt_ok, out=np.full(n, np.nan), where=cnt_ok > 0) - mean ** 2

name_map = {str(f_["properties"]["adcode"]): f_["properties"].get("name", "") for f_ in geo["features"]}
with open(DATA / "县域海拔.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "平均海拔_m", "地形起伏度_m(像元std)", "有效像元占比"])
    for k, code in enumerate(adcodes):
        ratio = cnt_ok[k + 1] / cnt_all[k + 1] if cnt_all[k + 1] > 0 else 0
        w.writerow([code, name_map.get(code, ""),
                    round(float(mean[k + 1]), 1) if np.isfinite(mean[k + 1]) else "",
                    round(float(np.sqrt(max(var[k + 1], 0))), 1) if np.isfinite(var[k + 1]) else "",
                    f"{ratio:.2f}"])

# 抽查：找几个已知县
spot = {"城关区": None, "玛多县": None, "歙县": None, "崇明区": None, "日土县": None, "朝阳区": None}
for k, code in enumerate(adcodes):
    nm = name_map.get(code, "")
    if nm in spot:
        spot[nm] = mean[k + 1]
print("抽查（应约：拉萨城关3650 / 玛多4250 / 歙县300 / 崇明4 / 日土4500+ / 朝阳40）：")
for nm, v in spot.items():
    print(f"  {nm}: {v:.0f} m" if np.isfinite(v) else f"  {nm}: 无有效像元")
hi = sorted(((name_map.get(c, ""), mean[idx_of[c]]) for c in adcodes if np.isfinite(mean[idx_of[c]])),
            key=lambda t: -t[1])[:5]
print("平均海拔前5县：", [(n_, round(m_, 0)) for n_, m_ in hi])
bad = sum(1 for c in adcodes if not np.isfinite(mean[idx_of[c]]) or mean[idx_of[c]] < -500)
print(f"异常/缺失县：{bad} 个")
