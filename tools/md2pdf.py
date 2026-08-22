#!/usr/bin/env python
# tools/md2pdf.py - 将中文 Markdown 报告转为 PDF（依赖 fpdf2 + 系统中文字体）
import sys
import re
from fpdf import FPDF

FONT = r"C:\Windows\Fonts\simhei.ttf"
SRC = sys.argv[1]
OUT = sys.argv[2]


GLYPH_MAP = {
    "\U0001f7e2": "[覆盖]",
    "\U0001f7e1": "[部分]",
    "\U0001f534": "[不覆盖]",
    "\u2705": "[OK]",
    "\u00b3": "3",
    "\u2022": "-",
}


def clean(t: str) -> str:
    for k, v in GLYPH_MAP.items():
        t = t.replace(k, v)
    return t.replace("**", "").strip()


pdf = FPDF(format="A4")
pdf.add_font("CN", "", FONT)
pdf.add_font("CN", "B", FONT)  # 黑体无独立 bold 变体，复用同文件避免报错
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margins(15, 15, 15)
pdf.add_page()
pdf.set_font("CN", "", 11)

LM = pdf.l_margin
lines = open(SRC, encoding="utf-8").read().splitlines()
n = len(lines)
i = 0
while i < n:
    line = lines[i]
    s = line.strip()
    if not s:
        pdf.ln(2)
        i += 1
        continue
    if s == "---":
        pdf.ln(3)
        i += 1
        continue
    # 表格：连续以 | 开头的行
    if s.startswith("|") and "|" in s[1:]:
        rows = []
        while i < n and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):  # 跳过分隔行
                i += 1
                continue
            rows.append(cells)
            i += 1
        if rows:
            pdf.set_x(LM)
            pdf.set_font("CN", "", 8.5)
            with pdf.table(width=180) as table:
                for r in rows:
                    row = table.row()
                    for c in r:
                        row.cell(clean(c))
            pdf.ln(2)
            pdf.set_font("CN", "", 11)
        continue
    # 引用块
    if s.startswith("> "):
        pdf.set_x(18)
        pdf.set_font("CN", "", 10)
        pdf.multi_cell(177, 5.5, clean(s[2:]), markdown=False,
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CN", "", 11)
        i += 1
        continue
    # 标题
    if s.startswith("### "):
        pdf.set_x(LM)
        pdf.set_font("CN", "B", 12)
        pdf.multi_cell(0, 7, clean(s[4:]), markdown=False,
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CN", "", 11)
        pdf.ln(1)
        i += 1
        continue
    if s.startswith("## "):
        pdf.set_x(LM)
        pdf.set_font("CN", "B", 14)
        pdf.multi_cell(0, 8, clean(s[3:]), markdown=False,
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CN", "", 11)
        pdf.ln(1)
        i += 1
        continue
    if s.startswith("# "):
        pdf.set_x(LM)
        pdf.set_font("CN", "B", 17)
        pdf.multi_cell(0, 10, clean(s[2:]), markdown=False,
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CN", "", 11)
        pdf.ln(2)
        i += 1
        continue
    # 列表
    if re.match(r"^[\-\*] ", s):
        pdf.set_x(20)
        pdf.set_font("CN", "", 10)
        pdf.multi_cell(170, 6, "- " + clean(s[2:]), markdown=False,
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CN", "", 11)
        i += 1
        continue
    # 普通段落
    pdf.set_x(LM)
    pdf.multi_cell(0, 6, clean(s), markdown=False,
                   new_x="LMARGIN", new_y="NEXT")
    i += 1

pdf.output(OUT)
print("PDF written:", OUT)
