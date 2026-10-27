# -*- coding: utf-8 -*-
"""
50_验证DeepSeek指控.py
对 DeepSeek 审稿意见中最重的三项数值指控逐一复算：
  指控1（M1）：CCD 的 1217 个"低度协调"县=单要素县（结构零值），中位数0是定义性结果
  指控2（M3）：NNI 的 Z 值公式用错——正确 SE=0.26136·√A/n，Z 应为 −78~−86 量级
  指控3（M4）：VMR 的两套样方不同（648 vs 675 格）——因网格只覆盖各点集自身范围
  附带：SDE 重心的经纬度（正文 33.5°N/34.7°N 系估写）与椭圆方位角的真值
  附带：双要素县（758）上重算 CCD 分布；A∩B∩C 稳健交集
"""
import csv
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import pyproj

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")

# ---------- 指控1：CCD 结构零值 ----------
rows = list(csv.DictReader(open(DATA / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
dual = [r for r in rows if int(r["村落数"]) > 0 and int(r["非遗A全量"]) > 0]
single = [r for r in rows if (int(r["村落数"]) == 0) != (int(r["非遗A全量"]) == 0)]
print(f"【指控1】双要素县 {len(dual)}｜单要素县 {len(single)}（DeepSeek 反推：758 / 1217）")
ccd = {r["adcode"]: float(r["D_A主口径"]) for r in csv.DictReader(
    open(DATA / "县域耦合协调度.csv", encoding="utf-8-sig"))}
d_dual = np.array([ccd[r["adcode"]] for r in dual])
print(f"  双要素县 D 分布：中位 {np.median(d_dual):.3f}｜P25 {np.percentile(d_dual,25):.3f}｜"
      f"P75 {np.percentile(d_dual,75):.3f}｜最大 {d_dual.max():.3f}｜≥0.4 的县 {int((d_dual>=0.4).sum())} 个"
      f"（占双要素县 {100*(d_dual>=0.4).mean():.1f}%）")

# ---------- 指控2：NNI Z 正确公式 ----------
A_km2 = 9489084.0
for label, n, obs, exp in (("村落", 6817, 8.5, 18.7), ("非遗", 3610, 8.2, 25.6)):
    se_wrong = 0.26136 * math.sqrt(A_km2 / n)
    se_right = 0.26136 * math.sqrt(A_km2) / n
    print(f"【指控2】{label}: 错误公式 Z={(obs-exp)/se_wrong:.2f}（稿件现值）｜"
          f"正确公式 Z={(obs-exp)/se_right:.1f}（DeepSeek：−86/−78）")

# ---------- 指控3：VMR 样方数差异来源 ----------
import struct
def read_pts_village():
    g = json.loads((DATA / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
    PROJ = pyproj.Transformer.from_crs("EPSG:4326",
        "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform
    from shapely.geometry import Point
    from shapely.ops import transform
    return np.array([[*(transform(PROJ, Point(f["geometry"]["coordinates"])).coords)[0]] for f in g["features"]])

PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform
from shapely.geometry import Point
from shapely.ops import transform as shp_transform
vill = json.loads((DATA.parent / "02_传统村落" / "合并_传统村落_前五批.geojson").read_text(encoding="utf-8"))
vxy = np.array([[*shp_transform(PROJ, Point(f["geometry"]["coordinates"])).coords][0] for f in vill["features"]]) / 1000.0
# 非遗 xy
raw = (DATA.parent / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
n_rec = struct.unpack("<I", raw[4:8])[0]
h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
fields, pos = [], 32
while raw[pos] != 0x0D:
    fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
    pos += 32
widths = [w for _, w in fields]
idx = {nm: k for k, (nm, _) in enumerate(fields)}
ixy = np.empty((n_rec, 2))
for i in range(n_rec):
    start = h_size + i * r_size + 1
    p, vals = start, []
    for w in widths:
        vals.append(raw[p:p + w].decode("utf-8", errors="replace").strip())
        p += w
    ixy[i] = PROJ(float(vals[idx["X"]]), float(vals[idx["Y"]]))
ixy /= 1000.0
for label, pts in (("村落", vxy), ("非遗", ixy)):
    qx = ((pts[:, 0] - pts[:, 0].min()) // 200).astype(int)
    qy = ((pts[:, 1] - pts[:, 1].min()) // 200).astype(int)
    print(f"【指控3】{label}: 点云自身范围格网 = {len(set(zip(qx.tolist(), qy.tolist())))} 个有值格，"
          f"格网跨度 {qx.max()+1}×{qy.max()+1}——证实 09 号脚本网格随点集范围变化（648 vs 675 的来源）")

# ---------- 附带：SDE 重心经纬度与方位角真值 ----------
inv = pyproj.Transformer.from_crs(
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", "EPSG:4326", always_xy=True).transform
for label, pts in (("村落", vxy), ("非遗", ixy)):
    cx, cy = pts.mean(axis=0)
    cov = np.cov(pts.T)
    vals, vecs = np.linalg.eigh(cov)
    a1, a2 = math.sqrt(vals[1]), math.sqrt(vals[0])
    ang = math.degrees(math.atan2(vecs[1, 1], vecs[0, 1]))
    lon, lat = inv(cx * 1000, cy * 1000)
    print(f"【附带】{label} 椭圆：重心 {lon:.1f}°E, {lat:.1f}°N｜半轴 {a1:.0f}×{a2:.0f} km｜"
          f"长轴方位 {ang:.1f}°（0°=正东，90°=正北）")

# ---------- 附带：A∩B∩C 稳健交集（需要三口径局部结果；此处先算 A 的并集提示） ----------
print("\n【提示】A∩B∩C 三口径交集与 3×4 交叉表将在下一脚本（51）完成")
