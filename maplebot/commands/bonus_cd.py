import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from maplebot.utils.charts import _fig_to_base64

matplotlib.use("Agg")

# 基础暴击伤害加成（无爆伤属性时，暴击为普通伤害的 1.35 倍，即额外 +35%）
_BASE_CRIT_BONUS = 0.35

# ==========================================
# 核心数学计算逻辑
# ==========================================
def calculate_cd_fd_increase(curr_cd, new_cd):
    """计算新增爆伤%带来的 FD 提升（爆伤为独立乘区，纯加算）

    curr_cd: 当前爆伤百分比（小数，如 0.50 表示 50%）
    new_cd:  新增爆伤百分比（小数）

    已有爆伤乘区 = 1 + 0.35 + curr_cd
    新增后乘区   = 1 + 0.35 + curr_cd + new_cd
    FD 提升      = new_cd / (1 + 0.35 + curr_cd)
    """
    return new_cd / (1 + _BASE_CRIT_BONUS + curr_cd)


def calculate_bonus_cd(content: str) -> Message | str:
    """计算爆伤收益并返回图片+文本或错误提示文本"""
    try:
        parts = content.split()
        if len(parts) != 2:
            return "命令格式错误，请输入：\n爆伤收益 当前爆伤% 新增爆伤%\n例如：爆伤收益 80 10"
        current_cd_pct = float(parts[0]) / 100
        new_cd_pct = float(parts[1]) / 100
    except ValueError:
        return "参数错误，请输入数字。"

    fd_increase = calculate_cd_fd_increase(current_cd_pct, new_cd_pct)

    text_result = (
        f"当前爆伤: {current_cd_pct*100:.0f}%\n"
        f"新增爆伤: {new_cd_pct*100:.0f}%\n"
        f"最终伤害(FD)提升: {fd_increase*100:.2f}%"
    )

    # ==========================================
    # 动态计算 X 轴与 Y 轴的平滑缩放范围
    # ==========================================
    x_start = max(0.0, current_cd_pct - 0.50)
    x_end = x_start + 2.0
    y_max = max(5.0, fd_increase * 100 * 2.5)

    # ==========================================
    # 图表绘制
    # ==========================================
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig = plt.figure(figsize=(10, 6))

    curr_cd_values = np.linspace(x_start, x_end, 500)
    b_values = [0.05, 0.08, 0.10, 0.16]

    for b in b_values:
        fd_values = calculate_cd_fd_increase(curr_cd_values, b) * 100
        plt.plot(curr_cd_values * 100, fd_values, label=f'新增爆伤 {b*100:.0f}%', linewidth=2)

    plt.scatter([current_cd_pct * 100], [fd_increase * 100], color='blue', s=80, zorder=5)

    plt.vlines(x=current_cd_pct * 100, ymin=0, ymax=fd_increase * 100, colors='blue', linestyles='dashed', alpha=0.8)
    plt.hlines(y=fd_increase * 100, xmin=x_start * 100, xmax=current_cd_pct * 100, colors='blue', linestyles='dashed', alpha=0.8)

    plt.text(current_cd_pct * 100 + (x_end - x_start) * 0.02, fd_increase * 100 + (y_max * 0.03),
             f'当前爆伤: {current_cd_pct*100:.0f}%\n新增爆伤: {new_cd_pct*100:.0f}%\n新增FD: {fd_increase*100:.2f}%',
             color='blue', fontweight='bold', ha='left', va='bottom',
             bbox={"facecolor": 'white', "alpha": 0.7, "edgecolor": 'blue', "boxstyle": 'round,pad=0.5'})

    plt.title('新增爆伤百分比(%)对最终伤害(FD)的提升', fontsize=14)
    plt.xlabel('当前人物面板已有的爆伤 (%)', fontsize=12)
    plt.ylabel('最终伤害提升 FD (%)', fontsize=12)

    plt.xlim(x_start * 100, x_end * 100)
    plt.ylim(0, y_max)

    plt.legend(fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    msg = Message()
    try:
        b64 = _fig_to_base64(fig)
        msg += MessageSegment.image(f"base64://{b64}")
    except Exception as e:
        logger.error(f"Render bonus cd chart failed: {e}")
        plt.close(fig)

    msg += text_result
    return msg
