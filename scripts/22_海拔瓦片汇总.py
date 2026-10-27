# -*- coding: utf-8 -*-
"""
22_海拔瓦片汇总.py
作用：从 AWS 公开高程瓦片（terrarium 编码，zoom=7，约1km分辨率，免认证）
     下载并拼接中国范围高程，逐县计算平均海拔与起伏度（像元标准差）。
原理：terrarium 瓦片高程 = R*256 + G + B/256 - 32768（米）；
     瓦片为 Web Mercator (EPSG:3857) 网格，县界重投影后做分区统计。
"""
import csv
import json
import time
import urllib.request
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
TILE_DIR.mkdir(exist_ok=True)
OUT_TIF = DATA / "dem_china_z7_3857.tif"
OUT_CSV = DATA / "县域海拔.csv"
Z = 7
N = 256

# ---------- 1. 中国范围对应的瓦片号（x: 经度，y: 纬度，y=0 在北） ----------
def lon2x(lon):
    return int((lon + 180) / 360 * 2 ** Z)

def lat2y(lat):
    import math
    rad = math.radians(lat)
    return int((1 - math.asinh(math.tan(rad)) / math.pi) / 2 * 2 ** Z)

x0, x1 = lon2x(73), lon2x(136)
y0, y1 = lat2y(55), lat2y(14)          # y0<y1（越往北越小）
print(f"瓦片范围 x {x0}~{x1}，y {y0}~{y1}，共 {(x1 - x0 + 1) * (y1 - y0 + 1)} 张")

mosaic = np.zeros(((y1 - y0 + 1) * N, (x1 - x0 + 1) * N), dtype=np.float32)
fail = 0
for ty in range(y0, y1 + 1):
    for tx in range(x0, x1 + 1):
        f = TILE_DIR / f"{Z}_{tx}_{ty}.png"
        if not f.exists():
            try:
                req = urllib.request.Request(
                    f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{tx}/{ty}.png",
                    headers={"User-Agent": "Mozilla/5.0 (research use)"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    f.write_bytes(resp.read())
                time.sleep(0.03)
            except Exception as e:
                print(f"  ! {tx},{ty} 失败: {e}")
                fail += 1
        try:
            img = plt.imread(f)[..., :3].astype(np.float32)
            elev = img[..., 0] * 256 + img[..., 1] + img[..., 2] / 256 - 32768
        except Exception:
            fail += 1
            continue
        r0, c0 = (ty - y0) * N, (tx - x0) * N
        mosaic[r0:r0 + N, c0:c0 + N] = elev
print(f"瓦片处理完成，失败 {fail} 张")

# ---------- 2. 存成 GeoTIFF（EPSG:3857） ----------
res = 40075016.6856 / (2 ** Z * N)     # 每像元米数
top = 40075016.6856 / 2 - y0 * N * res
transform = from_origin(-20037508.34 + x0 * N * res, top, res, res)
with rasterio.open(OUT_TIF, "w", driver="GTiff", height=mosaic.shape[0],
                   width=mosaic.shape[1], count=1, dtype="float32", crs="EPSG:3857",
                   transform=transform, compress="lzw") as dst:
    dst.write(mosaic, 1)
print(f"已保存：{OUT_TIF}")

# ---------- 3. 逐县分区统计 ----------
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
flat = mask.ravel()
val = mosaic.ravel()
n = len(adcodes) + 1
cnt = np.bincount(flat, minlength=n)
s = np.bincount(flat, weights=val, minlength=n)
s2 = np.bincount(flat, weights=val * val, minlength=n)
mean = np.divide(s, cnt, out=np.full(n, np.nan), where=cnt > 0)
var = np.divide(s2, cnt, out=np.full(n, np.nan), where=cnt > 0) - mean ** 2

name_map = {str(f_["properties"]["adcode"]): f_["properties"].get("name", "") for f_ in geo["features"]}
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "平均海拔_m", "地形起伏度_m(像元std)"])
    for k, code in enumerate(adcodes):
        w.writerow([code, name_map.get(code, ""),
                    round(float(mean[k + 1]), 1), round(float(np.sqrt(max(var[k + 1], 0))), 1)])
print(f"已保存：{OUT_CSV}")
hi = sorted(((name_map.get(c, ""), mean[idx_of[c]]) for c in adcodes if not np.isnan(mean[idx_of[c]])),
            key=lambda t: -t[1])[:5]
print("平均海拔前5县：", [(n_, round(m_, 0)) for n_, m_ in hi])
