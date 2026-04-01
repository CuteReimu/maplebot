"""图表生成模块"""
import base64
import io
import logging
import os
import sys

import matplotlib
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

matplotlib.use("Agg")

logger = logging.getLogger("maplebot.charts")

# ---------- 中文字体加载 ----------
_FONT_DIRS = {
    "darwin": "/Library/Fonts/",
    "linux": "/usr/share/fonts/",
    "win32": "C:\\Windows\\Fonts\\",
}
_font_dir = _FONT_DIRS.get(sys.platform, "")
_font_path = ""
if _font_dir and os.path.isdir(_font_dir):
    for root, _, files in os.walk(_font_dir):
        for f in files:
            if f.lower() == "simhei.ttf":
                _font_path = os.path.join(root, f)
                break
        if _font_path:
            break
if _font_path:
    fm.fontManager.addfont(_font_path)
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False


def _fig_to_base64(fig, pad_inches=None) -> str:
    """将 matplotlib figure 转为 base64 PNG"""
    buf = io.BytesIO()
    save_kwargs: dict = {"format": "png", "bbox_inches": "tight", "dpi": 120}
    if pad_inches is not None:
        save_kwargs["pad_inches"] = pad_inches
    fig.savefig(buf, **save_kwargs)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ====================== 表格渲染 ======================

def render_table(
    header: list[str],
    data: list[list[str]],
    width: int = 600,
    cell_colors: list[list[str | None]] | None = None,
    header_font_color: str = "#232323",
) -> str:
    """
    渲染表格为 base64 PNG 图片。

    cell_colors: 与 data 同形状的二维列表，每个元素为颜色字符串或 None。
    """
    n_cols = len(header)
    n_rows = len(data)
    col_width = width / (n_cols * 80)
    fig_w = max(col_width * n_cols, 4)
    fig_h = max(0.4 * (n_rows + 1), 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    table = ax.table(
        cellText=data,
        colLabels=header,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.3)

    # 表头样式
    for j in range(n_cols):
        cell = table[0, j]
        cell.set_text_props(color=header_font_color, weight="bold")
        cell.set_facecolor("#e6e6e6")

    # 单元格上色
    if cell_colors:
        for i, row_colors in enumerate(cell_colors):
            for j, color in enumerate(row_colors):
                if color:
                    table[i + 1, j].set_facecolor(color)

    return _fig_to_base64(fig, pad_inches=0)


# ====================== 饼图渲染 ======================

def render_pie(
    values: list[float],
    labels: list[str],
    title: str = "",
    unit: str = "",
) -> str:
    """渲染饼图为 base64 PNG 图片"""
    fig, ax = plt.subplots(figsize=(8, 6))

    def make_autopct(vals):
        def autopct(pct):
            idx = int(round(pct / 100.0 * sum(vals)))
            # 找到最接近的索引
            cumsum = 0
            for i, v in enumerate(vals):
                cumsum += v
                if cumsum / sum(vals) * 100 >= pct - 0.5:
                    idx = i
                    break
            return f"{vals[idx]:.1f}{unit}" if unit else f"{pct:.1f}%"
        return autopct

    if unit:
        ax.pie(values, labels=labels, autopct=make_autopct(values), startangle=90)
    else:
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)

    if title:
        ax.set_title(title)
    return _fig_to_base64(fig)


# ====================== 柱状图+折线图 ======================

def render_bar_line(
    bar_values: list[float],
    line_values: list[float],
    labels: list[str],
    bar_colors: list[str] | None = None,
    y_formatter=None,
    y2_formatter=None,
    y_max: float | None = None,
    y2_range: tuple[float, float] | None = None,
    y_ticks: list[float] | None = None,
    y2_ticks: list[float] | None = None,
) -> str:
    """渲染柱状图(左轴)+折线图(右轴)为 base64 PNG 图片"""
    bg = "#050816"
    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(bg)
    ax1.set_facecolor(bg)

    x = np.arange(len(labels))
    colors = bar_colors or ["#4d6bff"] * len(bar_values)
    ax1.bar(x, bar_values, color=colors, zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=60, fontsize=7.5)
    if y_max is not None:
        ax1.set_ylim(0, y_max)
    if y_ticks is not None:
        ax1.set_yticks(y_ticks)
    if y_formatter:
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(y_formatter))

    ax2 = ax1.twinx()
    ax2.plot(
        x, line_values, marker="o", linewidth=2, markersize=5,
        color="#9bff7a", zorder=4,
    )
    if y2_range:
        ax2.set_ylim(*y2_range)
    if y2_ticks is not None:
        ax2.set_yticks(y2_ticks)
    if y2_formatter:
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(y2_formatter))

    tick_color = "#a7adc4"
    for ax in (ax1, ax2):
        ax.tick_params(axis="both", colors=tick_color)
    ax1.grid(False)
    ax2.grid(False)
    ax1.yaxis.grid(True, linestyle="-", linewidth=0.6, color="#262b3e", alpha=0.9)
    for spine in ["top", "right", "left"]:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax1.spines["bottom"].set_color("#20253a")

    return _fig_to_base64(fig)
