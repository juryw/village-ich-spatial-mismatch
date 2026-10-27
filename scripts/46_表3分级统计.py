# -*- coding: utf-8 -*-
"""46_表3分级统计.py：按耦合协调度分级断点统计县数（表3数据）"""
import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rows = list(csv.DictReader(open(
    r"E:\GLM\非遗论文\02_数据\03_基础地理\县域耦合协调度.csv", encoding="utf-8-sig")))
BREAKS = [0, 0.10, 0.20, 0.30, 0.40, 1.01]
LABELS = ["低度耦合协调（D<0.10）", "较低（0.10≤D<0.20）", "中等（0.20≤D<0.30）",
          "较高（0.30≤D<0.40）", "高（D≥0.40）"]
counts = [0] * 5
for r in rows:
    d = float(r["D_A主口径"])
    for k in range(5):
        if BREAKS[k] <= d < BREAKS[k + 1]:
            counts[k] += 1
            break
total = sum(counts)
print(f"分析单元 {total} 个（应为1975）")
for lab, n in zip(LABELS, counts):
    print(f"  {lab}: {n} 县（{n/total*100:.1f}%）")
