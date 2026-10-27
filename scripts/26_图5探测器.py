# -*- coding: utf-8 -*-
"""26_图5探测器.py：因子探测 q 值横向条形图（三个因变量并排）"""
import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Microsoft YaHei"

SRC = Path(r"E:\GLM\非遗论文\02_数据\03_基础地理\探测器结果_v1.csv")
OUT = Path(r"E:\GLM\非遗论文\04_图表") / "图5_地理探测器q值_预览.png"

rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if r["因变量"] == "因子探测"]
# 上面筛不到——探测器结果_v1.csv 只存了交互表，因子表用重算读取方式：
# 直接从CSV结构判断：文件头为 因变量,因子对,q交互,q1,q2,类型 → 无因子行。
# 所以这里改为从脚本23的控制台结论重建（数字以脚本23输出为准，勿手改）：
data = {
    "村落密度": {"GDP密度": 0.019, "人口密度": 0.018, "路网密度": 0.023, "距省会距离": 0.006,
               "县域面积": 0.020, "民族自治地方": 0.004, "经度位置": 0.013, "纬度位置": 0.047,
               "平均海拔": 0.038, "地形起伏度": 0.030},
    "非遗密度A": {"GDP密度": 0.033, "人口密度": 0.033, "路网密度": 0.032, "距省会距离": 0.020,
               "县域面积": 0.032, "民族自治地方": 0.001, "经度位置": 0.004, "纬度位置": 0.001,
               "平均海拔": 0.013, "地形起伏度": 0.015},
    "非遗密度B": {"GDP密度": 0.039, "人口密度": 0.039, "路网密度": 0.038, "距省会距离": 0.022,
               "县域面积": 0.038, "民族自治地方": 0.001, "经度位置": 0.005, "纬度位置": 0.001,
               "平均海拔": 0.016, "地形起伏度": 0.018},
}

factors = list(next(iter(data.values())).keys())
y = np.arange(len(factors))
h = 0.26
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=200)
for k, (name, vals, color) in enumerate((
        ("村落密度", data["村落密度"], "#1f77b4"),
        ("非遗密度A（全量）", data["非遗密度A"], "#d62728"),
        ("非遗密度B（剔除全国性机构点位）", data["非遗密度B"], "#ff9896"))):
    ax.barh(y + (k - 1) * h, [vals[f] for f in factors], height=h, label=name, color=color)
ax.set_yticks(y)
ax.set_yticklabels(factors)
ax.invert_yaxis()
ax.set_xlabel("因子探测 q 值（越大解释力越强）")
ax.set_title("传统村落与非遗密度的地理探测器因子探测结果（预览图）", fontsize=13)
ax.legend(fontsize=9, loc="lower right")
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"已保存：{OUT}")
