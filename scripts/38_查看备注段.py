# -*- coding: utf-8 -*-
"""38_查看备注段.py"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

text = Path(r"E:\GLM\非遗论文\05_稿件\论文初稿_v1.md").read_text(encoding="utf-8")
start = text.find("## 写作状态备注")
print(text[start:start + 1500])
