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
def calc_damage_multiplier(m_df, h_idf):
    """计算当前造成的伤害比例 (1 - 怪物减伤)"""
    return 1 - m_df * (1 - h_idf)

def calculate_fd_increase(m_df, h_idf, n_idf):
    """计算新增无视带来的 FD 提升"""
    old_dmg = calc_damage_multiplier(m_df, h_idf)
    # 新减伤 = 怪物防御 * (1 - 面板无视) * (1 - 新增无视)
    new_dmg = 1 - m_df * (1 - h_idf) * (1 - n_idf)
    return (new_dmg - old_dmg) / old_dmg

def calculate_bonus_idf(content: str) -> Message | str:
    """计算无视收益并返回 (文本, 图片base64) 或错误提示文本"""
    try:
        parts = content.split()
        if len(parts) != 3:
            return "命令格式错误，请输入：\n无视收益 怪物防御% 当前面板无视% 新增无视%\n例如：无视收益 300 97 30"
        monster_df = float(parts[0]) / 100
        hero_idf = float(parts[1]) / 100
        new_idf = float(parts[2]) / 100
    except ValueError:
        return "参数错误，请输入数字。"

    # 过滤掉无法破防的初始状态
    if calc_damage_multiplier(monster_df, hero_idf) <= 0:
        return "当前无视过低，无法对该怪物造成伤害（不破防）。"

    fd_increase = calculate_fd_increase(monster_df, hero_idf, new_idf)

    text_result = (
        f"怪物防御: {monster_df * 100:.0f}%\n"
        f"当前面板无视 (hero_idf): {hero_idf * 100:.2f}%\n"
        f"新增无视词条 (new_idf): {new_idf * 100:.2f}%\n"
        f"最终伤害(FD)提升: {fd_increase * 100:.2f}%"
    )

    # ==========================================
    # 动态计算 X 轴与 Y 轴的平滑缩放范围
    # ==========================================
    # 寻找伤害恰好大于0的下限 (即不破防临界点): 1 - m_df * (1 - h_idf) = 0
    min_required_idf = 1 - 1 / monster_df

    # 设定 X 轴起点：取 "输入值-15%" 和 "破防下限+1%" 之间的最大值
    x_start = max(min_required_idf + 0.01, hero_idf - 0.15)
    x_end = 1.0  # X 轴终点固定为100%

    y_max = max(5.0, fd_increase * 100 * 3)

    # ==========================================
    # 图表绘制
    # ==========================================
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    fig = plt.figure(figsize=(10, 6))

    hero_idf_values = np.linspace(x_start, x_end, 500)
    b_values = [0.1, 0.2, 0.3, 0.4]

    # 循环绘制多条对比曲线
    for b in b_values:
        # 过滤掉无法破防的区间，避免计算异常
        valid_mask = calc_damage_multiplier(monster_df, hero_idf_values) > 0
        valid_idf = hero_idf_values[valid_mask]

        fd_values = calculate_fd_increase(monster_df, valid_idf, b) * 100
        plt.plot(valid_idf * 100, fd_values, label=f'新增无视 {b * 100:.0f}%', linewidth=2)

    plt.scatter([hero_idf * 100], [fd_increase * 100], color='red', s=80, zorder=5)

    plt.vlines(x=hero_idf * 100, ymin=0, ymax=fd_increase * 100, colors='red', linestyles='dashed', alpha=0.8)
    plt.hlines(y=fd_increase * 100, xmin=x_start * 100, xmax=hero_idf * 100, colors='red', linestyles='dashed', alpha=0.8)

    plt.text(hero_idf * 100 - 0.5, fd_increase * 100 + (y_max * 0.03),
             f'面板无视: {hero_idf * 100}%\n新增FD: {fd_increase * 100:.2f}%',
             color='red', fontweight='bold', ha='right', va='bottom',
             bbox={"facecolor": 'white', "alpha": 0.7, "edgecolor": 'red', "boxstyle": 'round,pad=0.5'})

    plt.title(f'【怪物防御: {monster_df * 100:.0f}%】 新增无视防御对最终伤害(FD)的提升', fontsize=14)
    plt.xlabel('当前人物面板无视 hero_idf (%)', fontsize=12)
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
        logger.error(f"Render bonus idf chart failed: {e}")
        plt.close(fig)

    msg += text_result
    return msg
