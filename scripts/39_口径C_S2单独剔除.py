# -*- coding: utf-8 -*-
"""
39_口径C_S2单独剔除.py
背景：用户指出 S1 全剔北上津过于武断（京剧/泥人张等真本地户被连坐）。
本脚本计算"C 口径"：只按 S2（保护单位机构关键词）剔除，不使用地域标准，
     并对比 A（全量）/ B（S1∪S2）/ C（仅S2）三种口径下的关键数字。
同时列出 S1-only（在北上津但单位名不带机构词）的点，供导师面谈讨论。
"""
import csv
import json
import math
import struct
from pathlib import Path

DATA = Path(r"E:\GLM\非遗论文\02_数据")
ORG_KEYWORDS = ["协会", "学会", "研究会", "促进会", "联合会", "公司", "集团",
                "剧院", "剧团", "演艺", "大学", "学院", "研究所", "研究院"]
METRO = ("北京市", "上海市", "天津市")

# ---------- 读非遗 DBF ----------
raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
n_rec = struct.unpack("<I", raw[4:8])[0]
h_size, r_size = struct.unpack("<H", raw[8:10])[0], struct.unpack("<H", raw[10:12])[0]
fields, pos = [], 32
while raw[pos] != 0x0D:
    fields.append((raw[pos:pos + 11].split(b"\x00")[0].decode("ascii"), raw[pos + 16]))
    pos += 32
widths = [w for _, w in fields]
idx = {nm: k for k, (nm, _) in enumerate(fields)}
ich = []
for i in range(n_rec):
    start = h_size + i * r_size + 1
    p, vals = start, []
    for w in widths:
        vals.append(raw[p:p + w].decode("utf-8", errors="replace").strip())
        p += w
    ich.append({"name": vals[idx["Name_CN"]], "place": vals[idx["Place_CN"]],
                "unit": vals[idx["Unit_CN"]], "cat": vals[idx["CategoryCN"]],
                "x": float(vals[idx["X"]]), "y": float(vals[idx["Y"]] )})

s1 = lambda r: r["place"].startswith(METRO)
s2 = lambda r: any(k in r["unit"] for k in ORG_KEYWORDS)

only_s1 = [r for r in ich if s1(r) and not s2(r)]          # 口径C会保留的北上津点
print(f"S1-only（北上津但单位名非机构型，口径C保留）：{len(only_s1)} 条")
from collections import Counter
cat = Counter(r["cat"] for r in only_s1)
print("  其门类分布：", dict(cat.most_common()))
print("  样例（前12条）：")
for r in only_s1[:12]:
    print(f"    {r['name']}｜{r['place']}｜{r['unit']}")

# ---------- 归县（与09一致：修复版边界+网格索引） ----------
geo = json.loads((DATA / "03_基础地理" / "中国_县级边界_修复.geojson").read_text(encoding="utf-8"))
counties = []
for f_ in geo["features"]:
    g = f_.get("geometry")
    if not g:
        continue
    parts = [g["coordinates"][0]] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
    xs = [x for part in parts for x, _ in part]
    ys = [y for part in parts for _, y in part]
    counties.append({"adcode": str(f_["properties"]["adcode"]), "name": f_["properties"].get("name", ""),
                     "parts": parts, "bbox": (min(xs), min(ys), max(xs), max(ys)),
                     "cx": (min(xs) + max(xs)) / 2, "cy": (min(ys) + max(ys)) / 2,
                     "C": 0})
GRID = {}
for i, c in enumerate(counties):
    x0, y0, x1, y1 = c["bbox"]
    for gx in range(math.floor(x0), math.floor(x1) + 1):
        for gy in range(math.floor(y0), math.floor(y1) + 1):
            GRID.setdefault((gx, gy), []).append(i)

def pip(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x1 + (y - y1) * (x2 - x1) / (y2 - y1) > x:
            inside = not inside
    return inside

def assign(x, y):
    for i in GRID.get((math.floor(x), math.floor(y)), []):
        if any(pip(x, y, part) for part in counties[i]["parts"]):
            return i
    best, bd = None, 1e9
    for i in GRID.get((math.floor(x), math.floor(y)), []):
        d = (counties[i]["cx"] - x) ** 2 + (counties[i]["cy"] - y) ** 2
        if d < bd:
            best, bd = i, d
    return best

for r in ich:
    if s2(r):                          # 口径C：只剔 S2
        continue
    i = assign(r["x"], r["y"])
    if i is not None:
        counties[i]["C"] += 1

_prev_rows = list(csv.DictReader(open(DATA / "03_基础地理" / "县域统计_敏感性对比.csv", encoding="utf-8-sig")))
_b_key = "非遗B剔除后(仅S2)" if "非遗B剔除后(仅S2)" in _prev_rows[0] else "非遗B剔除后"
_c_key = "非遗C严格(S1∪S2)" if "非遗C严格(S1∪S2)" in _prev_rows[0] else _b_key
prev = {r["adcode"]: (int(r["村落数"]), int(r["非遗A全量"]), int(r[_c_key])) for r in _prev_rows}

# ---------- 三口径相关系数 ----------
def pearson(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den

village = [prev.get(c["adcode"], (0, 0, 0))[0] for c in counties]
A = [prev.get(c["adcode"], (0, 0, 0))[1] for c in counties]
B = [prev.get(c["adcode"], (0, 0, 0))[2] for c in counties]
Cc = [c["C"] for c in counties]
print(f"\n村落-非遗相关：A 全量 r={pearson(village, A):.3f}｜B S1∪S2 r={pearson(village, B):.3f}｜C 仅S2 r={pearson(village, Cc):.3f}")
print(f"C 口径保留 {sum(Cc)} / 3610（剔除 {sum(1 for r in ich if s2(r))} 条，全部因机构关键词）")
print("C 口径非遗前10县：", [(c["name"], c["C"]) for c in sorted(counties, key=lambda c: -c['C'])[:10]])
print("北京朝阳区：", [(c["name"], c["C"]) for c in counties if c["adcode"] == "110105"])

# ---------- 更新敏感性对比 CSV：B 列改为主口径（仅S2），新增 C 严格列（S1∪S2） ----------
OUT = DATA / "03_基础地理" / "县域统计_敏感性对比.csv"
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["adcode", "县名", "村落数", "非遗A全量", "非遗B剔除后(仅S2)", "非遗C严格(S1∪S2)"])
    for c in counties:
        v, a, c_strict = prev.get(c["adcode"], (0, 0, 0))
        w.writerow([c["adcode"], c["name"], v, a, c["C"], c_strict])
print(f"\n敏感性对比表已更新：B=仅S2（新主口径），C=S1∪S2（严格下界）→ {OUT}")

# ---------- 同步更新剔除清单 ----------
with open(DATA / "01_非遗名录" / "敏感性_剔除点位清单.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["项目名称", "申报地区", "保护单位", "触发规则"])
    for r in sorted(ich, key=lambda r: (not s2(r), r["place"])):
        if s2(r) or s1(r):
            rule = "S2机构" if s2(r) else "S1地域"
            w.writerow([r["name"], r["place"], r["unit"], rule])
print(f"剔除清单已更新（B 主口径剔除 {sum(1 for r in ich if s2(r))} 条标 S2；C 严格口径多剔的 {len(only_s1)} 条标 S1，供对照）→ 敏感性_剔除点位清单.csv")
