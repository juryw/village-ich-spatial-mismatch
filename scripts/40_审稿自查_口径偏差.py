# -*- coding: utf-8 -*-
"""
40_审稿自查_口径偏差.py
审稿人视角自查一：S2 规则是否存在系统性类别偏差？
  —— 传统技艺/医药类非遗常由在地的老字号企业保护（如泸州老窖股份有限公司），
     名字含"公司/集团"会被 S2 误删，而它们恰恰是"点画对了地方"的。
自查内容：被 S2 剔除的 1001 条的门类分布 vs 总体分布；
  其中"申报地不在北上津"且单位含公司/集团 的在地企业误删数量与样例。
"""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"E:\GLM\非遗论文\02_数据")
ORG_KEYWORDS = ["协会", "学会", "研究会", "促进会", "联合会", "公司", "集团",
                "剧院", "剧团", "演艺", "大学", "学院", "研究所", "研究院"]
METRO = ("北京市", "上海市", "天津市")

raw = (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2021.dbf").read_bytes() if False else \
      (DATA / "01_非遗名录" / "IhChina_2006-2021" / "IhChina_2006-2021.dbf").read_bytes()
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
                "unit": vals[idx["Unit_CN"]], "cat": vals[idx["CategoryCN"]]})

s2 = lambda r: any(k in r["unit"] for k in ORG_KEYWORDS)
removed = [r for r in ich if s2(r)]
overall = Counter(r["cat"] for r in ich)
rm = Counter(r["cat"] for r in removed)
print("门类      被剔  总体  被剔占比  总体占比  偏差倍数")
for cat, n_all in overall.most_common():
    n_rm = rm.get(cat, 0)
    pr, pa = n_rm / 1001, n_all / 3610
    print(f"{cat}: {n_rm:4d} {n_all:5d}   {pr*100:5.1f}%   {pa*100:5.1f}%   {pr/pa:.2f}x")

# 在地企业误删：单位含公司/集团 且 申报地不含"地区/州/盟"？——更直接的判据：
# 申报地是地级市或县级（非北上津）且单位含"公司/集团"
inplace_co = [r for r in removed if "公司" in r["unit"] or "集团" in r["unit"]]
not_metro_co = [r for r in inplace_co if not r["place"].startswith(METRO)]
print(f"\n被剔条目中单位含'公司/集团'：{len(inplace_co)} 条；其中申报地非北上津：{len(not_metro_co)} 条（大概率在地企业）")
print("样例（前15条）：")
for r in not_metro_co[:15]:
    print(f"  {r['name']}｜{r['place']}｜{r['unit']}")
