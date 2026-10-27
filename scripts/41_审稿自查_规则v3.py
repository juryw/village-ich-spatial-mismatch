# -*- coding: utf-8 -*-
"""
41_审稿自查_规则v3.py
S2 的类别偏差根源：文艺院团"转企改制"后大量在地剧团叫"XX有限公司/演艺集团"，
被关键词误杀（396条非北上津的公司/集团）；而真正的"总部搬移"单位往往是
中国/国家/中华打头的全国性机构。测试规则 v3：
  剔除 = 单位名含 [中国/国家/中华/全国] 或 [协会/学会/研究会/研究院/研究所/促进会/联合会/大学/学院]
  （不再剔除 公司/集团/剧院/剧团/演艺 —— 那是在地转制院团与老字号企业）
"""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATA = Path(r"E:\GLM\非遗论文\02_数据")
KW_V3 = ["中国", "国家", "中华", "全国", "协会", "学会", "研究会", "研究院",
         "研究所", "促进会", "联合会", "大学", "学院"]
METRO = ("北京市", "上海市", "天津市")

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
                "unit": vals[idx["Unit_CN"]], "cat": vals[idx["CategoryCN"]]})

v3 = lambda r: any(k in r["unit"] for k in KW_V3)
removed = [r for r in ich if v3(r)]
overall = Counter(r["cat"] for r in ich)
rm = Counter(r["cat"] for r in removed)
print(f"v3 剔除 {len(removed)} 条（S2 为 1001）")
print("门类      v3被剔  总体  偏差倍数   （对照 S2 的偏差：技艺1.67/戏剧1.58/医药2.40）")
for cat, n_all in overall.most_common():
    n_rm = rm.get(cat, 0)
    print(f"{cat}: {n_rm:4d} {n_all:5d}   {n_rm/len(removed)/(n_all/3610):.2f}x")

metro_v3 = [r for r in removed if r["place"].startswith(METRO)]
print(f"\nv3 中申报地北上津的：{len(metro_v3)} 条（S1∩S2 曾为 104）")
print("非北上津被 v3 剔的样例（应为真总部型，前10条）：")
for r in [r for r in removed if not r["place"].startswith(METRO)][:10]:
    print(f"  {r['name']}｜{r['place']}｜{r['unit']}")
