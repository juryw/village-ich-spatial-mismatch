# -*- coding: utf-8 -*-
"""18_调试省会匹配.py：找出距省会距离为 None 的县，看看省名哪里对不上"""
import csv
from collections import Counter

rows = list(csv.DictReader(open(
    r"E:\GLM\非遗论文\02_数据\03_基础地理\县域驱动因子表.csv", encoding="utf-8-sig")))
bad = [r for r in rows if r["d_capital"] in ("", "None", None)]
print(f"缺失 {len(bad)} 条，省名分布：{Counter(r['prov'] for r in bad)}")
print(f"全部出现过的省名：{sorted({r['prov'] for r in rows})}")
