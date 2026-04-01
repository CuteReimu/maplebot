"""等级经验计算"""
from nonebot.log import logger

from maplebot.utils.charts import render_table
from maplebot.utils.config import level_exp_data



def _format_exp(exp: int | float) -> str:
    exp = float(exp)
    if exp < 1_000:
        return f"{exp:g}"
    if exp < 1_000_000:
        return f"{exp / 1_000:.2f}K"
    if exp < 1_000_000_000:
        return f"{exp / 1_000_000:.2f}M"
    if exp < 1_000_000_000_000:
        return f"{exp / 1_000_000_000:.2f}B"
    if exp < 1_000_000_000_000_000:
        return f"{exp / 1_000_000_000_000:.2f}T"
    return f"{exp / 1_000_000_000_000_000:.2f}Q"


def calculate_exp_between_level(start: int, end: int) -> str | None:
    """计算从 start 级到 end 级需要的总经验"""
    if start < 1 or end > 300 or start >= end:
        return None
    total_exp = 0
    for i in range(start, end):
        total_exp += int(level_exp_data.get(f"data.{i}", 0) or 0)
    s = _format_exp(total_exp)
    return f"从{start}级到{end}级需要经验：{s}"


def calculate_level_exp() -> str | None:
    """生成 201~300 级的经验表格图片"""
    cur: list[str] = []
    acc: list[str] = []
    accumulate = 0
    for i in range(201, 301):
        v = int(level_exp_data.get(f"data.{i}", 0) or 0)
        cur.append(_format_exp(v))
        acc.append(_format_exp(accumulate))
        accumulate += v

    # 4 列并排：201-225, 226-250, 251-275, 276-300
    header = ["当前等级", "升级经验", "累计经验"] * 4
    data: list[list[str]] = []
    for i in range(25):
        row: list[str] = []
        for j in range(4):
            level = 201 + i + j * 25
            idx = level - 201
            row.extend([str(level), cur[idx], acc[idx]])
        data.append(row)

    # 为每隔3列(等级列)加灰色背景
    n_cols = len(header)
    n_rows = len(data)
    cell_colors: list[list[str | None]] = []
    for i in range(n_rows):
        row_colors: list[str | None] = []
        for j in range(n_cols):
            if j % 3 == 0:
                row_colors.append("#b4b4b480")
            else:
                row_colors.append(None)
        cell_colors.append(row_colors)

    try:
        return render_table(
            header=header,
            data=data,
            width=1100,
            cell_colors=cell_colors,
        )
    except Exception as e:
        logger.error("render chart failed: %s", e)
        return None


def calculate_exp_damage(s: str) -> str | None:
    """等级压制计算"""
    try:
        i = int(s)
    except ValueError:
        return None

    if i >= 5:
        return "你比怪物等级高5级以上时，终伤+20%"
    if i > 0:
        return f"你比怪物等级高{i}级时，终伤+{i * 2 + 10}%"
    if i == 0:
        return "你和怪物等级相等时，终伤+10%"
    if i == -1:
        return "你比怪物等级低1级时，终伤+5%"
    if i == -2:
        return "你比怪物等级低2级时，终伤不变"
    if i == -3:
        return "你比怪物等级低3级时，终伤-5%"
    if i > -40:
        return f"你比怪物等级低{-i}级时，终伤{2.5 * i:g}%"
    return "你比怪物等级低40级以上时，终伤-100%"
