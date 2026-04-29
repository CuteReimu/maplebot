import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from maplebot.utils.charts import _fig_to_base64

matplotlib.use("Agg")

# ==========================================
# 核心数学计算逻辑
# ==========================================
def calculate_atk_fd_increase(curr_atk, new_atk):
    """计算新增攻击力%带来的 FD 提升"""
    return new_atk / (1 + curr_atk)

def calculate_bonus_att(content: str) -> Message | str:
    """计算攻击收益并返回 (文本, 图片base64) 或错误提示文本"""
    try:
        parts = content.split()
        if len(parts) != 2:
            return "命令格式错误，请输入：\n攻击收益 当前面板攻击% 新增攻击%\n例如：攻击收益 150 30"
        current_atk_pct = float(parts[0]) / 100
        new_atk_pct = float(parts[1]) / 100
    except ValueError:
        return "参数错误，请输入数字。"

    fd_increase = calculate_atk_fd_increase(current_atk_pct, new_atk_pct)

    text_result = (
        f"当前攻击力: {current_atk_pct*100:.0f}%\n"
        f"新增攻击力: {new_atk_pct*100:.0f}%\n"
        f"最终伤害(FD)提升: {fd_increase*100:.2f}%"
    )

    # ==========================================
    # 动态计算 X 轴与 Y 轴的平滑缩放范围
    # ==========================================
    x_start = max(0.0, current_atk_pct - 0.50)
    x_end = x_start + 2.0
    y_max = max(5.0, fd_increase * 100 * 2.5)

    # ==========================================
    # 图表绘制
    # ==========================================
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig = plt.figure(figsize=(10, 6))

    curr_atk_values = np.linspace(x_start, x_end, 500)
    b_values = [0.09, 0.12, 0.21, 0.30]

    for b in b_values:
        fd_values = calculate_atk_fd_increase(curr_atk_values, b) * 100
        plt.plot(curr_atk_values * 100, fd_values, label=f'新增攻击力 {b*100:.0f}%', linewidth=2)

    plt.scatter([current_atk_pct * 100], [fd_increase * 100], color='blue', s=80, zorder=5)

    plt.vlines(x=current_atk_pct * 100, ymin=0, ymax=fd_increase * 100, colors='blue', linestyles='dashed', alpha=0.8)
    plt.hlines(y=fd_increase * 100, xmin=x_start * 100, xmax=current_atk_pct * 100, colors='blue', linestyles='dashed', alpha=0.8)

    plt.text(current_atk_pct * 100 + (x_end - x_start) * 0.02, fd_increase * 100 + (y_max * 0.03),
             f'当前攻击力: {current_atk_pct*100:.0f}%\n新增攻击力: {new_atk_pct*100:.0f}%\n新增FD: {fd_increase*100:.2f}%',
             color='blue', fontweight='bold', ha='left', va='bottom',
             bbox={"facecolor": 'white', "alpha": 0.7, "edgecolor": 'blue', "boxstyle": 'round,pad=0.5'})

    plt.title('新增攻击力百分比(%)对最终伤害(FD)的提升', fontsize=14)
    plt.xlabel('当前人物面板已有的附加攻击力 a (%)', fontsize=12)
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
        logger.error(f"Render bonus att chart failed: {e}")
        plt.close(fig)

    msg += text_result
    return msg
