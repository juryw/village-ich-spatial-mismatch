# -*- coding: utf-8 -*-
"""
17_驱动因子与探测器v0.py
作用：1) 生成县域驱动因子表：民族自治县(0/1)、县域面积、距省会距离、中心经纬度
     2) 用地理探测器"因子探测+交互探测"公式跑一版 v0（Y=村落密度/非遗密度）
说明：q = 1 - SSW/SST（分层方差比）；交互探测用分层叠加法。
     DEM/人口/路网等因子数据到位后在因子表加列即可，探测器代码不用改。
"""
import json
import math
import time
import urllib.request
from pathlib import Path

import numpy as np
from scipy import stats
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

DATA = Path(r"E:\GLM\非遗论文\02_数据")
OUT = DATA / "03_基础地理" / "县域驱动因子表.csv"
PROJ = pyproj.Transformer.from_crs("EPSG:4326",
    "+proj=aea +lat_1=25 +lat_2=47 +lon_0=105 +datum=WGS84 +units=m", always_xy=True).transform

# ---------- 省会坐标（约值，用于距离量算，论文中注明取自国家基础地理信息） ----------
CAPITALS = {
    "北京市": (116.41, 39.90), "天津市": (117.20, 39.08), "上海市": (121.47, 31.23),
    "重庆市": (106.55, 29.56), "河北省": (114.51, 38.04), "山西省": (112.55, 37.87),
    "内蒙古自治区": (111.75, 40.84), "辽宁省": (123.43, 41.80), "吉林省": (125.32, 43.90),
    "黑龙江省": (126.53, 45.80), "江苏省": (118.78, 32.06), "浙江省": (120.16, 30.29),
    "安徽省": (117.28, 31.86), "福建省": (119.30, 26.08), "江西省": (115.86, 28.68),
    "山东省": (117.00, 36.67), "河南省": (113.63, 34.75), "湖北省": (114.31, 30.60),
    "湖南省": (112.94, 28.23), "广东省": (113.26, 23.13), "广西壮族自治区": (108.32, 22.82),
    "海南省": (110.35, 20.02), "四川省": (104.07, 30.67), "贵州省": (106.63, 26.65),
    "云南省": (102.83, 24.97), "西藏自治区": (91.11, 29.66), "陕西省": (108.94, 34.34),
    "甘肃省": (103.83, 36.06), "青海省": (101.78, 36.62), "宁夏回族自治区": (106.23, 38.49),
    "新疆维吾尔自治区": (87.62, 43.83),
}

def haversine(lon1, lat1, lon2, lat2):
    """球面距离（km）"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

# ---------- 1. 县级信息 ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
prov_geo = json.loads((DATA / "03_基础地理" / "中国_省级边界.geojson").read_text(encoding="utf-8"))
prov_name = {f["properties"]["adcode"]: f["properties"].get("name", "") for f in prov_geo["features"]}

# 市级名称（用于识别"自治州"成员县）：拉取各省级 _full 一次并缓存
cache = DATA / "03_基础地理" / "市级名称缓存.json"
if cache.exists():
    city_names = {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
else:
    city_names = {}
    for pcode in prov_name:
        try:
            req = urllib.request.Request(
                f"https://geo.datav.aliyun.com/areas_v3/bound/{pcode}_full.json",
                headers={"User-Agent": "Mozilla/5.0 (research use)"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                for feat in json.loads(resp.read().decode("utf-8"))["features"]:
                    city_names[int(feat["properties"]["adcode"])] = feat["properties"].get("name", "")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ! 省级 {pcode} 拉取失败：{e}")
    cache.write_text(json.dumps({str(k): v for k, v in city_names.items()}, ensure_ascii=False), encoding="utf-8")
print(f"市级名称 {len(city_names)} 条")

rows = []
for f in geo["features"]:
    p = f["properties"]
    if str(p["adcode"]).startswith(("81", "82")) or not f.get("geometry"):
        continue                                        # 跳过港澳与无几何
    route = p.get("acroutes") or []
    # acroutes 可能形如 [100000, 省code, 市code, 县code]，取其中属于省级的那一个
    prov_code = next((a for a in route if a in prov_name), None)
    pname = prov_name.get(prov_code, "")
    city = city_names.get(next((a for a in route if a in city_names), -1), "")
    center = p.get("center") or p.get("centroid") or [0, 0]
    is_ethnic = int(("自治县" in p.get("name", "")) or ("自治旗" in p.get("name", ""))
                    or ("自治州" in city))
    area = transform(PROJ, shape(f["geometry"])).area / 1e6
    cap = CAPITALS.get(pname)
    d_cap = haversine(center[0], center[1], *cap) if cap else None
    rows.append({"adcode": p["adcode"], "name": p.get("name", ""), "prov": pname,
                 "ethnic": is_ethnic, "area_km2": area,
                 "lon": center[0], "lat": center[1], "d_capital": d_cap,
                 "village": p.get("VILLAGE_N", 0), "ich": p.get("ICH_N", 0)})

print(f"县级因子行：{len(rows)}；民族自治县/州属县 {sum(r['ethnic'] for r in rows)} 个")

import csv
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"已保存：{OUT}")

# ---------- 2. 地理探测器 v0 ----------
Y_v = np.array([r["village"] / r["area_km2"] * 1000 for r in rows])   # 处/千km²
Y_i = np.array([r["ich"] / r["area_km2"] * 1000 for r in rows])

def quantile_classes(x, n=5):
    """连续因子按分位数分 n 类（地理探测器常规做法）"""
    edges = np.quantile(x, np.linspace(0, 1, n + 1)[1:-1])
    return np.searchsorted(edges, x, side="right")

X = {
    "民族自治地方(0/1)": np.array([r["ethnic"] for r in rows]),
    "县域面积": quantile_classes(np.array([r["area_km2"] for r in rows])),
    "距省会距离": quantile_classes(np.array([r["d_capital"] for r in rows])),
    "经度位置": quantile_classes(np.array([r["lon"] for r in rows])),
    "纬度位置": quantile_classes(np.array([r["lat"] for r in rows])),
}

def q_stat(y, x):
    """因子探测 q 值 + F 检验 p 值"""
    sst = ((y - y.mean()) ** 2).sum()
    ssw = 0.0
    for h in np.unique(x):
        yh = y[x == h]
        ssw += len(yh) * yh.var()
    q = 1 - ssw / sst
    L = len(np.unique(x))
    N = len(y)
    f = (ssw / (L - 1)) / ((sst - ssw) / (N - L)) if L > 1 and sst > ssw else np.inf
    p = 1 - stats.f.cdf(f, L - 1, N - L)
    return q, p

print("\n【因子探测 q 值】（v0，仅含可即时计算因子）")
for yn, y in (("村落密度", Y_v), ("非遗密度", Y_i)):
    line = f"  {yn}: "
    for xn, x in X.items():
        q, p = q_stat(y, x)
        line += f"{xn} q={q:.3f}{'***' if p<0.01 else '**' if p<0.05 else ''}｜"
    print(line)

print("\n【交互探测】（q(X1×X2)，与 q1+q2 及 max 比较判断增强/减弱）")
names = list(X)
for yn, y in (("村落密度", Y_v), ("非遗密度", Y_i)):
    print(f"  ◆ {yn}")
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            inter = X[names[a]] * 100 + X[names[b]]      # 分层叠加
            q_ab, _ = q_stat(y, inter)
            q_a, _ = q_stat(y, X[names[a]])
            q_b, _ = q_stat(y, X[names[b]])
            kind = ("非线性增强" if q_ab > q_a + q_b else
                    "双因子增强" if q_ab > max(q_a, q_b) else
                    "减弱/非线性减弱")
            print(f"    {names[a]} × {names[b]}：q={q_ab:.3f}（q1={q_a:.3f}, q2={q_b:.3f}）→ {kind}")
