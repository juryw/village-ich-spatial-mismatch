# -*- coding: utf-8 -*-
"""
34_导出Word初稿.py
作用：把 05_稿件/论文初稿_v1.md 排版为规范的中文学术稿件 Word（.docx）。
规则：题目黑体二号居中；一级标题黑体四号；二级/三级标题黑体小四；
     正文宋体小四、两端对齐、首行缩进2字符、1.5倍行距（投稿常用）；
     表格带全框线；参考文献五号、悬挂缩进。
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SRC = Path(r"E:\GLM\非遗论文\05_稿件\论文初稿_v1.md")
DST = Path(r"E:\GLM\非遗论文\05_稿件\论文初稿_v1.docx")

doc = Document()

# ---------- 页面与默认样式 ----------
for sec in doc.sections:
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.0)

style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(12)                      # 小四
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def set_font(run, cn_font="宋体", size=12, bold=False, color=None):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn_font)
    if color:
        run.font.color.rgb = color


def add_rich(par, text, cn_font="宋体", size=12, base_bold=False):
    """处理 **加粗** 与 <sup>上标</sup> 行内标记"""
    for part in re.split(r"(\*\*.+?\*\*|<sup>.+?</sup>)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            set_font(par.add_run(part[2:-2]), cn_font, size, True)
        elif part.startswith("<sup>") and part.endswith("</sup>"):
            run = par.add_run(part[5:-6])
            set_font(run, cn_font, size, False)
            run.font.superscript = True
        else:
            set_font(par.add_run(part), cn_font, size, base_bold)


def add_body(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.first_line_indent = Pt(24)             # 首行缩进 2 字符（小四）
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    add_rich(p, text)


def add_heading(text, level):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    sizes = {1: 16, 2: 14, 3: 12}             # 一级四号/二级小四/三级小四
    add_rich(p, text, "黑体", sizes.get(level, 12), base_bold=True)
    if level == 1:
        pf.space_before, pf.space_after = Pt(12), Pt(6)
    return p


def add_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(set(c) <= set("-: ") for c in r)]  # 去分隔行
    if not cells:
        return
    t = doc.add_table(rows=len(cells), cols=len(cells[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(cells):
        for j, val in enumerate(row):
            if j < len(t.rows[i].cells):
                cell = t.rows[i].cells[j]
                cell.text = ""
                p = cell.paragraphs[0]
                add_rich(p, val, "宋体", 10.5, base_bold=(i == 0))


# 图片映射：论文图号 → (文件名, 图题, 是否地图需加底图说明)
FIG_INFO = {
    "1": ("图0_数据速览_预览.png", "图 1 中国传统村落与国家级非物质文化遗产空间分布", True),
    "2": ("图2_核密度与标准差椭圆_预览.png", "图 2 传统村落与非遗的核密度及标准差椭圆", True),
    "3": ("图3_县域耦合协调度_预览.png", "图 3 县域传统村落与非遗耦合协调度分级", True),
    "4": ("图4_双变量LISA集聚图_预览.png", "图 4 双变量 LISA 集聚格局：清洗前后对比", True),
    "5": ("图5_地理探测器q值_预览.png", "图 5 地理探测器因子探测 q 值", False),
}
FIG_DIR = Path(r"E:\GLM\非遗论文\04_图表")

lines = SRC.read_text(encoding="utf-8").splitlines()
i = 0
while i < len(lines):
    line = lines[i].rstrip()
    if not line.strip():
        i += 1
        continue
    if line.startswith("|"):                  # 表格块
        block = []
        while i < len(lines) and lines[i].startswith("|"):
            block.append(lines[i])
            i += 1
        add_table(block)
        continue
    if line.strip().startswith("[[FIG:"):     # 图片标记 → 嵌图 + 图题
        fig_no = line.strip()[6:-2]
        fname, cap, is_map = FIG_INFO[fig_no]
        p_pic = doc.add_paragraph()
        p_pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_pic.add_run()
        run.add_picture(str(FIG_DIR / fname), width=Cm(15))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p_cap.add_run(cap), "黑体", 10.5, bold=False)
        if is_map:
            p_note = doc.add_paragraph()
            p_note.alignment = WD_ALIGN_PARAGRAPH.CENTER
            note = p_note.add_run("（底图为公开边界服务示意，投稿版替换为自然资源部标准地图底图）")
            set_font(note, "楷体", 9, color=RGBColor(0x60, 0x60, 0x60))
    elif line.startswith("# "):                 # 题目
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.space_before, pf.space_after = Pt(6), Pt(12)
        add_rich(p, line[2:], "黑体", 22, base_bold=True)
    elif line.startswith("## "):
        add_heading(line[3:], 1)
    elif line.startswith("### "):
        add_heading(line[4:], 2)
    elif line.startswith("> "):               # 说明块 → 楷体小字
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        add_rich(p, line[2:], "楷体", 10.5)
        for run in p.runs:
            run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    elif re.match(r"^\[\d+\]", line.strip()):  # 参考文献条目 → 悬挂缩进
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Pt(21)
        pf.first_line_indent = Pt(-21)        # 悬挂缩进
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        add_rich(p, line.strip(), "宋体", 10.5)
    elif line.strip().startswith(("- ", "✅", "✏️")) or re.match(r"^\d+\.\s", line.strip()):
        p = doc.add_paragraph()               # 列表项
        pf = p.paragraph_format
        pf.left_indent = Pt(12)
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        add_rich(p, line.strip().lstrip("- ").strip(), "宋体", 12)
    else:
        add_body(line)
    i += 1

doc.save(DST)
print(f"已保存：{DST}")
