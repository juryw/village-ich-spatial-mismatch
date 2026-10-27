# -*- coding: utf-8 -*-
"""
25_重建海拔.py
问题根源：matplotlib 读 PNG 返回 0~1 浮点色值，22 号脚本直接当 0~255 用，
         全图高程都被算成 -32768 附近。瓦片已缓存本地，重新解码拼接即可。
修复：色值 ×255 后按 terrarium 公式解码；有效性 = 高程 > -1000m。
"""
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
import pyproj

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
TILE_DIR = DATA / "dem_tiles"
Z, N = 7, 256
x0, x1, y0, y1 = 89, 112, 40, 58

# ---------- 1. 重新解码拼接（×255） ----------
mosaic = np.zeros(((y1 - y0 + 1) * N, (x1 - x0 + 1) * N), dtype=np.float32)
for ty in range(y0, y1 + 1):
    for tx in range(x0, x1 + 1):
        img = plt.imread(TILE_DIR / f"{Z}_{tx}_{ty}.png")[..., :3]
        if img.dtype != np.uint8:                       # matplotlib PNG → 0~1 浮点
            img = np.round(img * 255).astype(np.float32)
        else:
            img = img.astype(np.float32)
        elev = img[..., 0] * 256 + img[..., 1] + img[..., 2] / 256 - 32768
        mosaic[(ty - y0) * N:(ty - y0 + 1) * N, (tx - x0) * N:(tx - x0 + 1) * N] = elev

valid = mosaic > -1000.0
print(f"有效像元占比：{valid.mean() * 100:.1f}%")
print(f"高程范围：{mosaic[valid].min():.0f} ~ {mosaic[valid].max():.0f} m")

res = 40075016.6856 / (2 ** Z * N)
top = 40075016.6856 / 2 - y0 * N * res
transform = from_origin(-20037508.34 + x0 * N * res, top, res, res)
with rasterio.open(DATA / "dem_china_z7_3857.tif", "w", driver="GTiff",
                   height=mosaic.shape[0], width=mosaic.shape[1], count=1,
                   dtype="float32", crs="EPSG:3857", transform=transform, compress="lzw") as dst:
    dst.write(mosaic, 1)
print("GeoTIFF 已重建")

# ---------- 2. 逐县分区统计（带有效性掩膜） ----------
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
to3857 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
adcodes, shapes = [], []
for f_ in geo["features"]:
    if f_.get("geometry"):
        adcodes.append(str(f_["properties"]["adcode"]))
        shapes.append(shp_transform(to3857, shape(f_["geometry"])))
idx_of = {c: k + 1 for k, c in enumerate(adcodes)}

mask = rasterize([(shapes[k], idx_of[adcodes[k]]) for k in range(len(shapes))],
                 out_shape=mosaic.shape, transform=transform, fill=0, dtype="int32")
flat, val, ok = mask.ravel(), mosaic.ravel(), valid.ravel()
n = len(adcodes) + 1
cnt_all = np.bincount(flat, minlength=n)
cnt_ok = np.bincount(flat, weights=ok.astype(float), minlength=n)
s = np.bincount(flat, weights=np.where(ok, val, 0.0), minlength=n)
s2 = np.bincount(flat, weights=np.where(ok, val * val, 0.0), minlength=n)
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

spot_names = {"城关区": None, "玛多县": None, "歙县": None, "崇明区": None, "日土县": None, "朝阳区": None}
for k, code in enumerate(adcodes):
    nm = name_map.get(code, "")
    if nm in spot_names:
        spot_names[nm] = mean[k + 1]
print("抽查（拉萨城关≈3650 / 玛多≈4250 / 歙县≈300 / 崇明≈4 / 日土≈4500 / 朝阳≈40）：")
for nm, v in spot_names.items():
    print(f"  {nm}: {v:.0f} m" if np.isfinite(v) else f"  {nm}: 无效")
hi = sorted(((name_map.get(c, ""), mean[idx_of[c]]) for c in adcodes if np.isfinite(mean[idx_of[c]])),
            key=lambda t: -t[1])[:5]
print("平均海拔前5县：", [(n_, round(m_, 0)) for n_, m_ in hi])
