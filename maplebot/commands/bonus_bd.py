from __future__ import annotations

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
def calculate_dmg_fd(curr_total, new_val):
    """计算新增 伤害/B伤% 带来的 FD 提升 (公式：b / (1 + a))"""
    return new_val / (1 + curr_total)

def calculate_bonus_bd(content: str) -> Message | str:
    """计算 BOSS 伤害收益并返回 (文本, 图片base64) 或错误提示文本"""
    try:
        parts = content.split()
        if len(parts) != 3:
            return "命令格式错误，请输入：\nBOSS伤害收益 当前面板伤害% 当前面板B伤% 新增伤害/B伤%\n例如：BOSS伤害收益 120 350 40"
        current_dmg_pct = float(parts[0]) / 100
        current_bd_pct = float(parts[1]) / 100
        new_add_pct = float(parts[2]) / 100
    except ValueError:
        return "参数错误，请输入数字。"

    # 将普通伤害和B伤合并为一个总乘区参数
    current_total_pct = current_dmg_pct + current_bd_pct
    fd_increase = calculate_dmg_fd(current_total_pct, new_add_pct)

    text_result = (
        "=" * 40 + "\n"
        f"当前面板伤害%: {current_dmg_pct*100:.2f}%\n"
        f"当前面板B伤%: {current_bd_pct*100:.2f}%\n"
        f"当前[总伤害+B伤]合计: {current_total_pct*100:.2f}%\n"
        f"新增伤害/B伤%词条: {new_add_pct*100:.2f}%\n"
        f"最终伤害(FD)提升: {fd_increase*100:.2f}%\n"
        + "=" * 40
    )

    # ==========================================
    # 动态计算 X 轴与 Y 轴的平滑缩放范围
    # ==========================================
    x_start = max(0.0, current_total_pct - 2.0)
    x_end = current_total_pct + 4.0
    y_max = max(5.0, fd_increase * 100 * 2.5)

    # ==========================================
    # 图表绘制
    # ==========================================
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig = plt.figure(figsize=(10, 6))

    curr_total_values = np.linspace(x_start, x_end, 500)
    b_values = [0.20, 0.30, 0.35, 0.40]

    for b in b_values:
        fd_values = calculate_dmg_fd(curr_total_values, b) * 100
        plt.plot(curr_total_values * 100, fd_values, label=f'新增词条 {b*100:.0f}%', linewidth=2)

    plt.scatter([current_total_pct * 100], [fd_increase * 100], color='green', s=80, zorder=5)

    plt.vlines(x=current_total_pct * 100, ymin=0, ymax=fd_increase * 100, colors='green', linestyles='dashed', alpha=0.8)
    plt.hlines(y=fd_increase * 100, xmin=x_start * 100, xmax=current_total_pct * 100, colors='green', linestyles='dashed', alpha=0.8)

    plt.text(current_total_pct * 100 + (x_end - x_start) * 0.02, fd_increase * 100 + (y_max * 0.03),
             f'当前[伤害+B伤]: {current_total_pct*100:.0f}%\n新增伤害/B伤: {new_add_pct*100:.0f}%\n新增FD: {fd_increase*100:.2f}%',
             color='green', fontweight='bold', ha='left', va='bottom',
             bbox={"facecolor": 'white', "alpha": 0.7, "edgecolor": 'green', "boxstyle": 'round,pad=0.5'})

    plt.title('新增伤害/Boss伤害(%)对最终伤害(FD)的提升', fontsize=14)
    plt.xlabel('当前人物面板已有 [伤害% + Boss伤害%] (a%)', fontsize=12)
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
        logger.error(f"Render bonus bd chart failed: {e}")
        plt.close(fig)

    msg += text_result
    return msg
