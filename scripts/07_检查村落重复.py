# -*- coding: utf-8 -*-
"""07_检查村落重复.py：查合并表里的全名重复到底是哪几条"""
import csv
from collections import Counter

rows = list(csv.DictReader(open(
    r"E:\GLM\非遗论文\02_数据\02_传统村落\合并_传统村落_前五批.csv", encoding="utf-8-sig")))
names = [r["NameCN"] for r in rows]
print("总行数", len(names))
print("唯一全名", len(set(names)))

c = Counter(names)
for name, k in c.items():
    if k > 1:
        print(f"重复 {k} 次：{name}")
        for r in rows:
            if r["NameCN"] == name:
                print("   ", r["Batch"], r["X"], r["Y"], r["TownCN"])

c2 = Counter((r["DistrictCN"], r["VillageCN"]) for r in rows)
d2 = [(n, k) for n, k in c2.items() if k > 1]
print("县+村同名组合数：", len(d2))
for n, k in d2[:8]:
    print("  ", n, k)
