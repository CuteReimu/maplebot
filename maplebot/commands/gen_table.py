"""通用表格生成"""
import logging

from maplebot.utils.charts import render_table

logger = logging.getLogger("maplebot.gen_table")


def gen_table(s: str) -> str | None:
    """
    解析用户输入的 CSV 文本并生成表格图片。

    支持 w=数字 前缀指定宽度，如: "w=800 A,B,C\\n1,2,3"
    """
    width = 600
    if s.startswith("w="):
        idx = s.find(" ")
        if idx >= 0:
            try:
                width = int(s[2:idx])
            except ValueError:
                pass
            s = s[idx:].strip()

    lines = s.strip().split("\n")
    if not lines:
        return None

    header = [cell.strip() for cell in lines[0].split(",")]
    data = []
    for line in lines[1:]:
        line = line.strip()
        if line:
            data.append([cell.strip() for cell in line.split(",")])

    if not data:
        return None

    try:
        return render_table(header=header, data=data, width=width)
    except Exception as e:
        logger.error("render chart failed: %s", e)
        return None

