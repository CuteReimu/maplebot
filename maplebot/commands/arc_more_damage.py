"""ARC 神秘压制"""
import logging

from maplebot.utils.charts import render_table

logger = logging.getLogger("maplebot.arc")

_BOSS_ARC = [
    ("Lucid", 360),
    ("Will", 760),
    ("Gloom", 730),
    ("Hilla", 900),
    ("Darknell", 850),
    ("BlackMage", 1320),
]


def get_more_damage_arc() -> str | None:
    """生成 ARC 伤害表格，返回 base64 图片"""
    data = []
    for name, arc in _BOSS_ARC:
        data.append([
            name,
            str(arc),
            str(arc * 11 // 10),
            str(arc * 13 // 10),
            str(arc * 15 // 10),
        ])
    try:
        return render_table(
            header=["Boss", "100%", "110%", "130%", "150%"],
            data=data,
            width=480,
        )
    except Exception as e:
        logger.error("render chart failed: %s", e)
        return None
