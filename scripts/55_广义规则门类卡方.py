# -*- coding: utf-8 -*-
"""55_广义规则门类卡方.py"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
obs = [292, 54, 207, 39, 113, 26, 32, 62, 121, 55]
tot_cat = [629, 492, 473, 431, 417, 356, 251, 213, 182, 166]
n = sum(obs)
exp = [t / sum(tot_cat) * n for t in tot_cat]
chi2 = sum((o - e) ** 2 / e for o, e in zip(obs, exp))
print(f"广义词规则（14词，n={n}）门类 χ² = {chi2:.2f}（df=9）")
