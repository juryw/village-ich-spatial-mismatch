# -*- coding: utf-8 -*-
"""
53_选7_示范区命中率检验.py
DeepSeek 选-7/结-7：把本文的稳健核心与 2023 年集中连片保护利用示范县名单求交集，
     报告命中率、基准率、命中县与遗漏县——政策主张由"建议"升级为"验证"。
口径：稳健核心 = B(v3) 与 C(严格) 两种清洗规则下局部 LISA 类型相同的县（44 号定义）。
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(42)
import numpy as np
from shapely.geometry import shape
from shapely import STRtree
import libpysal
from esda.moran import Moran_Local_BV

DATA = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理")
NAMES = {0: "不显著", 1: "高—高", 2: "低—高", 3: "低—低", 4: "高—低"}

# ---------- 1. 读 2023 示范县名单（省+县） ----------
demo_raw = Path(r"E:\GLM\非遗论文\01_选题与文献\示范区名单_2023_提取.txt").read_text(encoding="utf-8").splitlines()
demo = []
import re
for line in demo_raw:
    if "．" not in line:
        continue
    body = line.split("．", 1)[1].strip()
    PROVS = ["黑龙江省","辽宁省","河北省","山西省","内蒙古自治区","吉林省","江苏省","浙江省","安徽省",
             "福建省","江西省","山东省","河南省","湖北省","湖南省","广东省","广西壮族自治区","海南省",
             "重庆市","四川省","贵州省","云南省","西藏自治区","陕西省","甘肃省","青海省","宁夏回族自治区",
             "新疆维吾尔自治区","北京市","天津市","上海市","台湾省","香港","澳门"]
    prov = next((pv for pv in PROVS if body.startswith(pv)), "")
    rest = body[len(prov):] if prov else body
    # 剥掉地级市/州/盟前缀，取最后的县级名
    m = re.match(r"^(.*?(?:自治州|地区|盟|市))(.+)$", rest)
    county = m.group(2) if m else rest
    demo.append((prov, county, body))
print(f"2023 示范县：{len(demo)} 个")

# ---------- 2. 我们的县表（adcode、县名、省份、村落数、非遗） ----------
drv = {r["adcode"]: r for r in csv.DictReader(open(DATA / "县域驱动因子表.csv", encoding="utf-8-sig"))}
sens = {r["adcode"]: r for r in csv.DictReader(open(DATA / "县域统计_敏感性对比.csv", encoding="utf-8-sig"))}
geo = json.loads((DATA / "中国_县级边界_统计.geojson").read_text(encoding="utf-8"))
feats = [f for f in geo["features"] if f.get("geometry") and str(f["properties"]["adcode"]) < "810000"]
info = {}
for f in feats:
    code = str(f["properties"]["adcode"])
    p = f["properties"]
    route = p.get("acroutes") or []
    prov_code = next((a for a in route if 110000 <= a <= 820000 and a not in (710000, 810000, 820000) and a >= 110000 and (a % 10000 == 0)), None)
    info[code] = {"name": p.get("name", ""), "v": p.get("VILLAGE_N", 0)}

# 省份：用驱动因子表
for code in info:
    d = drv.get(code, {})
    info[code]["prov"] = d.get("prov", "")
    s = sens.get(code, {})
    info[code]["A"] = int(s.get("非遗A全量", 0))
    info[code]["B"] = int(s.get("非遗B剔除后", 0))
    info[code]["C"] = int(s.get("非遗C严格(S1∪S2)", 0))

# ---------- 3. B 与 C 的局部 LISA（重建权重） ----------
vc = np.array([info[str(f["properties"]["adcode"])]["v"] for f in feats], dtype=float)
codes = [str(f["properties"]["adcode"]) for f in feats]
ib = np.array([info[c]["B"] for c in codes], dtype=float)
ic = np.array([info[c]["C"] for c in codes], dtype=float)
geoms = [shape(f["geometry"]).buffer(0) for f in feats]
tree = STRtree(geoms)
pairs = tree.query(geoms, predicate="touches")
neighbors = {k: set() for k in range(len(geoms))}
for a, b in zip(pairs[0], pairs[1]):
    if a != b:
        neighbors[int(a)].add(int(b))
w = libpysal.weights.W(neighbors, silence_warnings=True)

def local_types(x, y):
    l = Moran_Local_BV(x, y, w, permutations=199)
    out = np.zeros(len(x), dtype=int)
    for qq in (1, 2, 3, 4):
        out[(l.q == qq) & (l.p_sim <= 0.05)] = qq
    return out

tb = local_types(vc, ib)
tc = local_types(vc, ic)
robust = {codes[k]: (int(tb[k]), int(tc[k])) for k in range(len(codes))}

# ---------- 4. 匹配示范县 ----------
matches = []
for prov, county, body in demo:
    cand = [c for c in codes if info[c]["name"] == county
            and (info[c]["prov"] == prov or prov in ("北京市", "天津市", "上海市", "重庆市"))]
    matches.append((prov, county, cand))

print("\n=== 逐县匹配与分类 ===")
hit_core = 0
rows_out = []
for prov, county, cand in matches:
    if not cand:
        rows_out.append((prov, county, "未匹配", "-", "-"))
        print(f"  ✗ {prov}{county}：未匹配到县级单元")
        continue
    code = cand[0]
    qb, qc_ = robust[code]
    same = qb == qc_ and qb != 0
    tag = f"B:{NAMES.get(qb,'?')}/C:{NAMES.get(qc_,'?')}"
    robust_type = NAMES[qb] if same and qb != 0 else ""
    if same and qb in (1, 4):
        hit_core += 1
    rows_out.append((prov, county, info[code]["name"], tag, robust_type))
    mark = "★" if robust_type else "  "
    print(f"  {mark} {prov}{county} → {info[code]['name']}｜{tag}｜{'【'+robust_type+'】' if robust_type else ''}")

# ---------- 5. 命中率统计 ----------
n_demo = len(matches)
in_hh_robust = sum(1 for prov, county, cand in matches if cand and robust[cand[0]][0] == 1 and robust[cand[0]][1] == 1)
in_hl_robust = sum(1 for prov, county, cand in matches if cand and robust[cand[0]][0] == 4 and robust[cand[0]][1] == 4)
n_robust_hh = sum(1 for c in robust if robust[c][0] == 1 and robust[c][1] == 1)
n_robust_hl = sum(1 for c in robust if robust[c][0] == 4 and robust[c][1] == 4)
print(f"\n=== 命中率 ===")
print(f"示范县 {n_demo} 个；落入稳健高—高 {in_hh_robust} 个（基准率 {100*n_robust_hh/2848:.1f}%，示范县命中率 {100*in_hh_robust/n_demo:.1f}%）")
print(f"落入稳健高—低 {in_hl_robust} 个（基准率 {100*n_robust_hl/2848:.1f}%，命中率 {100*in_hl_robust/n_demo:.1f}%）")
import scipy.stats as st
table = [[in_hh_robust, n_demo - in_hh_robust], [n_robust_hh - in_hh_robust, 2848 - n_robust_hh - (n_demo - in_hh_robust)]]
odds, pv = st.fisher_exact(table)
print(f"稳健高—高 富集 Fisher 精确检验：OR={odds:.2f}，p={pv:.3f}")

# 稳健核心中未申报的县（下一批建议对象）
demo_codes = {c for prov, county, cand in matches for c in cand}
hh_robust_codes = [c for c in robust if robust[c][0] == 1 and robust[c][1] == 1]
not_demo = [name_map_c for c in hh_robust_codes if c not in demo_codes
            for name_map_c in [next(f["properties"]["name"] for f in feats if str(f["properties"]["adcode"]) == c)]]
print(f"\n稳健高—高 60 县中未列入 2023 示范的 {len(not_demo)} 县（下一批申报建议对象）：")
print("、".join(not_demo))
