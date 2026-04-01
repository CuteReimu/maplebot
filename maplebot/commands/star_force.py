"""升星模拟"""
import random

import numpy as np
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from maplebot.utils.charts import render_pie
from maplebot.utils.format_utils import format_int64

# ---------- 概率表 ----------
_RATES = [
    {  # 旧规
        0: [0.950, 0.050, 0.000, 0.000], 1: [0.900, 0.100, 0.000, 0.000],
        2: [0.850, 0.150, 0.000, 0.000], 3: [0.850, 0.150, 0.000, 0.000],
        4: [0.800, 0.200, 0.000, 0.000], 5: [0.750, 0.250, 0.000, 0.000],
        6: [0.700, 0.300, 0.000, 0.000], 7: [0.650, 0.350, 0.000, 0.000],
        8: [0.600, 0.400, 0.000, 0.000], 9: [0.550, 0.450, 0.000, 0.000],
        10: [0.500, 0.500, 0.000, 0.000], 11: [0.450, 0.550, 0.000, 0.000],
        12: [0.400, 0.600, 0.000, 0.000], 13: [0.350, 0.650, 0.000, 0.000],
        14: [0.300, 0.700, 0.000, 0.000],
        15: [0.300, 0.679, 0.000, 0.021], 16: [0.300, 0.000, 0.679, 0.021],
        17: [0.300, 0.000, 0.679, 0.021], 18: [0.300, 0.000, 0.672, 0.028],
        19: [0.300, 0.000, 0.672, 0.028], 20: [0.300, 0.630, 0.000, 0.070],
        21: [0.300, 0.000, 0.630, 0.070], 22: [0.030, 0.000, 0.776, 0.194],
        23: [0.020, 0.000, 0.686, 0.294], 24: [0.010, 0.000, 0.594, 0.396],
    },
    {  # 新规 (GMS)
        0: [0.950, 0.050, 0.000, 0.000], 1: [0.900, 0.100, 0.000, 0.000],
        2: [0.850, 0.150, 0.000, 0.000], 3: [0.850, 0.150, 0.000, 0.000],
        4: [0.800, 0.200, 0.000, 0.000], 5: [0.750, 0.250, 0.000, 0.000],
        6: [0.700, 0.300, 0.000, 0.000], 7: [0.650, 0.350, 0.000, 0.000],
        8: [0.600, 0.400, 0.000, 0.000], 9: [0.550, 0.450, 0.000, 0.000],
        10: [0.500, 0.500, 0.000, 0.000], 11: [0.450, 0.550, 0.000, 0.000],
        12: [0.400, 0.600, 0.000, 0.000], 13: [0.350, 0.650, 0.000, 0.000],
        14: [0.300, 0.700, 0.000, 0.000],
        15: [0.300, 0.679, 0.000, 0.021], 16: [0.300, 0.679, 0.000, 0.021],
        17: [0.150, 0.782, 0.000, 0.068], 18: [0.150, 0.782, 0.000, 0.068],
        19: [0.150, 0.765, 0.000, 0.085], 20: [0.300, 0.595, 0.000, 0.105],
        21: [0.150, 0.7225, 0.000, 0.1275], 22: [0.150, 0.680, 0.000, 0.170],
        23: [0.100, 0.720, 0.000, 0.180], 24: [0.100, 0.720, 0.000, 0.180],
        25: [0.100, 0.720, 0.000, 0.180], 26: [0.070, 0.744, 0.000, 0.186],
        27: [0.050, 0.760, 0.000, 0.190], 28: [0.030, 0.776, 0.000, 0.194],
        29: [0.010, 0.792, 0.000, 0.198],
    },
]

_STAR_CAP = {94: 5, 107: 8, 117: 10, 127: 15, 137: 20}
_STAR_COST_DIVISOR = {10: 40_000, 11: 22_000, 12: 15_000, 13: 11_000, 14: 7_500}


def _get_star_cap(eq_level: int, new_system: bool) -> int:
    cap = 30 if new_system else 25
    for max_lvl, star in _STAR_CAP.items():
        if eq_level <= max_lvl:
            cap = star
            break
    return cap


def _get_boom_star(cur_star: int, new_system: bool) -> int:
    if not new_system:
        return 12
    pairs = [(15, 12), (20, 15), (21, 17), (23, 19), (26, 20)]
    for threshold, result in reversed(pairs):
        if cur_star >= threshold:
            return result
    return 12


def _get_meso_cost(cur_star, eq_level, safe_guard=False, discount=False, new_system=False):
    multiplier = 1
    if discount:
        multiplier -= 0.3
    if safe_guard and not new_system:
        multiplier += 1
    elif safe_guard and new_system:
        multiplier += 2

    eq10 = eq_level // 10 * 10
    new_sf_mult = 1
    if new_system:
        new_sf_mult = {17: 4/3, 18: 20/7, 19: 40/9, 21: 8/5}.get(cur_star, 1)

    if cur_star < 10:
        meso_cost = 100 * round(eq10**3 * (cur_star + 1) / 2500 + 10)
    else:
        divisor = _STAR_COST_DIVISOR.get(cur_star, 20_000)
        meso_cost = 100 * round(new_sf_mult * eq10**3 * (cur_star + 1)**2.7 / divisor + 10)
    return round(meso_cost * multiplier)


def _get_max_star(new_kms: bool, item_level: int) -> int:
    if item_level < 95:
        return 5
    if item_level < 108:
        return 8
    if item_level < 118:
        return 10
    if item_level < 128:
        return 15
    if item_level < 138:
        return 20
    return 30 if new_kms else 25



# ---------- Markov 链计算 ----------
def _get_odds_and_inc(i, safe_guard, kms_new, _5_10_15, star_catch, boom_events):
    upgrade, fail_stay, fail_down, fail_break = _RATES[int(kms_new)][i]
    increment = 1
    if _5_10_15 and i in (5, 10, 15):
        return 1.0, 0.0, 0.0, 0.0, 1
    if star_catch:
        upgrade *= 1.05
        upgrade = min(upgrade, 1.0)
        mult = (1 - upgrade) / (1 - _RATES[int(kms_new)][i][0]) if _RATES[int(kms_new)][i][0] < 1.0 else 0
        fail_break *= mult
        fail_stay *= mult
        fail_down *= mult
    if boom_events and i <= 21:
        perk = fail_break * 0.3
        fail_break -= perk
        fail_stay += perk
    if kms_new:
        if safe_guard and i in (15, 16, 17):
            fail_stay += fail_break
            fail_break = 0.0
    else:
        if safe_guard and i in (15, 16):
            if i == 15:
                fail_stay += fail_break
            else:
                fail_down += fail_break
            fail_break = 0.0
    return upgrade, fail_stay, fail_down, fail_break, increment


def _calculate_markov(p, c, init_idx, absorb_count=1):
    n = p.shape[0]
    q = p[:-absorb_count, :-absorb_count]
    p_full = p[:-absorb_count, :]
    c_full = c[:-absorb_count, :]
    r = np.sum(p_full * c_full, axis=1)
    i = np.eye(n - absorb_count)
    g = np.linalg.solve(i - q, r)
    return g[init_idx]


def _calculate_no_boom_chance(p, init_idx):
    q = p[:-2, :-2]
    i = np.eye(q.shape[0])
    r = p[:-2, -2:]
    b_absorb = np.linalg.solve(i - q, r)
    return b_absorb[init_idx][1]


def _cal_sf(eq_level, init_star, end_star, safe_guard, star_catch,
            kms_new, discount, _5_10_15, boom_events):
    """Markov 链精确计算"""
    new_system = kms_new
    size = end_star * 2 + 1
    p_arr = np.zeros((size, size))
    weights_mat = np.zeros((size, size))
    no_boom_mat = np.zeros((size + 1, size + 1))
    boom_cost_mat = np.zeros((size, size))
    tap_cost_mat = np.zeros((size, size))
    p_arr[end_star * 2, end_star * 2] = 1

    for i in range(end_star):
        upgrade, fail_stay, fail_down, fail_break, inc = _get_odds_and_inc(
            i, safe_guard and (
                (not new_system and i in (15, 16)) or
                (new_system and i in (15, 16, 17))
            ), kms_new, _5_10_15, star_catch, boom_events)
        _sg = safe_guard and (
            (not new_system and i in (15, 16)) or
            (new_system and i in (15, 16, 17))
        )
        if not new_system and _5_10_15 and i == 15:
            _sg = False
        cost = _get_meso_cost(i, eq_level, _sg, discount, new_system)

        a = 2 * i
        # Upgrade
        b = 2 * i + 2 * inc
        p_arr[a, b] = upgrade
        weights_mat[a, b] = cost
        tap_cost_mat[a, b] = 1
        if i + inc == end_star:
            no_boom_mat[a, -1] = upgrade
        else:
            no_boom_mat[a, b] = upgrade

        # Stay
        p_arr[a, a] = fail_stay
        no_boom_mat[a, a] = fail_stay
        tap_cost_mat[a, a] = 1
        if fail_stay > 0:
            weights_mat[a, a] = cost

        # Down
        if i > 0 and fail_down > 0:
            if i in (16, 21):
                b_down = 2 * i - 2
            else:
                b_down = 2 * i - 1
            p_arr[a, b_down] = fail_down
            tap_cost_mat[a, b_down] = 1
            no_boom_mat[a, b_down] = fail_down
            weights_mat[a, b_down] = cost

        # Chance time (旧规 only, 16+ 且非 19/20)
        if i >= 16 and i not in (19, 20) and not new_system:
            b_up = 2 * i + 2 * inc
            ct_a = 2 * i + 1
            p_arr[ct_a, b_up] = upgrade
            no_boom_mat[ct_a, b_up] = upgrade
            tap_cost_mat[ct_a, b_up] = 1
            weights_mat[ct_a, b_up] = cost
            if fail_down > 0:
                lower_cost = _get_meso_cost(i - 1, eq_level, False, discount, new_system)
                p_arr[ct_a, 2 * i] = fail_down
                no_boom_mat[ct_a, 2 * i] = fail_down
                weights_mat[ct_a, 2 * i] = cost + lower_cost
                tap_cost_mat[ct_a, 2 * i] = 2
            if fail_break > 0:
                boom_star = _get_boom_star(i, new_system)
                p_arr[ct_a, 2 * boom_star] = fail_break
                no_boom_mat[ct_a, -2] += fail_break
                weights_mat[ct_a, 2 * boom_star] = cost
                tap_cost_mat[ct_a, 2 * boom_star] = 1
                boom_cost_mat[ct_a, 2 * boom_star] = 1

        # Boom
        if fail_break > 0:
            boom_star = _get_boom_star(i, new_system)
            p_arr[a, 2 * boom_star] = fail_break
            no_boom_mat[a, -2] = fail_break
            weights_mat[a, 2 * boom_star] = cost
            tap_cost_mat[a, 2 * boom_star] = 1
            boom_cost_mat[a, 2 * boom_star] = 1

    total_mean = _calculate_markov(p_arr, weights_mat, 2 * init_star)
    tap_mean = _calculate_markov(p_arr, tap_cost_mat, 2 * init_star)
    boom_mean = _calculate_markov(p_arr, boom_cost_mat, 2 * init_star)
    no_boom = _calculate_no_boom_chance(no_boom_mat, 2 * init_star)

    midway = []
    for mid in range(init_star + 1, end_star):
        sub_size = 2 * mid + 1
        mid_mean = _calculate_markov(
            p_arr[:sub_size, :sub_size],
            weights_mat[:sub_size, :sub_size],
            2 * init_star,
        )
        midway.append(mid_mean)

    return total_mean, boom_mean, no_boom, tap_mean, midway


# ---------- 升星模拟蒙特卡洛（用于爆炸次数统计）----------
def _perform_experiment(current_star, desired_star, new_kms, item_level,
                        boom_protect, thirty_off, five_ten_fifteen, boom_event):
    total_mesos = 0.0
    total_booms = 0
    decrease_count = 0
    star = current_star
    while star < desired_star:
        chance_time = not new_kms and decrease_count == 2
        rates = _RATES[int(new_kms)]
        up, stay, down, boom = rates[star]
        if five_ten_fifteen and star in (5, 10, 15):
            up, stay, down, boom = 1.0, 0.0, 0.0, 0.0
        if boom_event and star <= 21:
            perk = boom * 0.3
            boom -= perk
            stay += perk
        if boom_protect:
            if new_kms and star <= 17:
                if down > 0:
                    down += boom
                else:
                    stay += boom
                boom = 0
            elif not new_kms and star <= 16:
                if down > 0:
                    down += boom
                else:
                    stay += boom
                boom = 0
        # star catch
        up *= 1.05
        left = 1 - up
        if down == 0:
            stay_new = stay * left / (stay + boom) if (stay + boom) > 0 else 0
            boom = left - stay_new
            stay = stay_new
        else:
            down_new = down * left / (down + boom) if (down + boom) > 0 else 0
            boom = left - down_new
            down = down_new

        cost = _get_meso_cost(star, item_level,
                              boom_protect and not (five_ten_fifteen and star == 15)
                              and not chance_time and star in (15, 16),
                              thirty_off, new_kms)
        total_mesos += cost

        if chance_time:
            decrease_count = 0
            star += 1
        else:
            outcome = random.random()
            if outcome < up:
                decrease_count = 0
                star += 1
            elif outcome < up + stay:
                decrease_count = 0
            elif outcome < up + stay + down:
                decrease_count += 1
                star -= 1
            else:
                decrease_count = 0
                star = 12
                total_booms += 1
    return total_mesos, total_booms


# ====================== 公开接口 ======================

def _parse_flags(content: str) -> tuple[bool, bool, bool, bool]:
    """解析标志位：(bp保护, to七折, ftf必成, be减爆)"""
    bp = "保护" in content and "不保护" not in content
    to = "七折" in content or "超必" in content or "超爆" in content
    ftf = "必成" in content or "超必" in content
    be = "超爆" in content or "防爆" in content or "减爆" in content
    return bp, to, ftf, be


def _build_title(bp, to, ftf, be) -> str:
    parts: list[str] = []
    if to and ftf:
        parts.append("(超必)")
    elif to and be:
        parts.append("(超爆)")
    else:
        if to:
            parts.append("(七折)")
        if ftf:
            parts.append("(必成)")
        if be:
            parts.append("(减爆)")
    if bp:
        parts.append("(保护)")
    return "".join(parts)


def calculate_boom_count(content: str, new_kms: bool) -> list:
    """爆炸次数统计饼图"""
    bp, to, ftf, be = _parse_flags(content)

    title = ("新" if new_kms else "旧") + "0-22星爆炸次数"
    title += _build_title(bp, to, ftf, be)

    booms: dict[int, int] = {}
    for _ in range(1000):
        _, b = _perform_experiment(0, 22, new_kms, 200, bp, to, ftf, be)
        booms[b] = booms.get(b, 0) + 1

    values: list[float] = []
    labels: list[str] = []
    left = 1000
    for k in range(11):
        labels.append(f"{k}次")
        values.append(float(booms.get(k, 0)))
        left -= booms.get(k, 0)
    if left > 0:
        labels.append("超过10次")
        values.append(float(left))

    try:
        img = render_pie(values, labels, title)
        return [MessageSegment.image(f"base64://{img}")]
    except Exception as e:
        logger.error("render chart failed: %s", e)
        return []


def calculate_star_force(new_kms: bool, content: str) -> list:
    """模拟升星（精确 Markov 链计算）"""
    parts = content.split(" ")
    if len(parts) < 3:
        return []
    try:
        item_level = int(parts[0])
        cur = int(parts[1])
        des = int(parts[2])
    except ValueError:
        return ["参数格式不正确"]
    if item_level < 5 or item_level > 300:
        return ["装备等级不合理"]
    if cur < 0:
        return ["当前星数不合理"]
    if des <= cur:
        return ["目标星数必须大于当前星数"]
    max_star = _get_max_star(new_kms, item_level)
    if des > max_star:
        return [f"{item_level}级装备最多升到{max_star}星"]

    bp, to, ftf, be = _parse_flags(content)

    try:
        mesos, booms, no_boom, taps, midway = _cal_sf(
            item_level, cur, des, bp, True, new_kms, to, ftf, be,
        )
    except Exception as e:
        logger.error("计算失败: %s", e)
        return ["计算失败"]

    # 构建活动说明
    activity = []
    if to:
        activity.append("七折活动")
    if ftf:
        activity.append("5/10/15必成活动")
    if be:
        activity.append("减爆活动")
    act_str = ("在" + "和".join(activity) + "中") if activity else ""

    s = f"{act_str}模拟升星{item_level}级装备"
    if bp:
        s += "（点保护）"
    s += "（GMS新规）" if new_kms else "（GMS旧规）"
    s += f"\n{cur}-{des}星"
    s += (
        f"，平均花费了{format_int64(int(mesos))}金币"
        f"，平均炸了{booms:.2f}次"
        f"，平均点了{int(round(taps))}次"
        f"，有{no_boom * 100:.2f}%的概率一次都不炸"
    )

    # 画饼图
    pie_img_seg = None
    if des > cur + 1 and des > 12 and midway:
        all_values = midway + [mesos]
        pie_labels = []
        pie_values = []
        if des <= 17:
            if cur < 12:
                pie_labels.append(f"{cur}-12")
                pie_values.append(all_values[12 - cur - 1])
            for i in range(max(cur, 12), des):
                pie_labels.append(f"{i}-{i+1}")
                idx1 = i + 1 - cur - 1
                idx0 = i - cur - 1
                val = all_values[idx1] - (all_values[idx0] if idx0 >= 0 else 0)
                pie_values.append(val)
        else:
            if cur < 15:
                pie_labels.append(f"{cur}-15")
                pie_values.append(all_values[15 - cur - 1])
            for i in range(max(cur, 15), des):
                pie_labels.append(f"{i}-{i+1}")
                idx1 = i + 1 - cur - 1
                idx0 = i - cur - 1
                val = all_values[idx1] - (all_values[idx0] if idx0 >= 0 else 0)
                pie_values.append(val)

        if len(pie_values) > 1:
            max_v = max(pie_values) if pie_values else 1
            unit = "T" if max_v >= 1e12 else "B"
            divisor = 1e12 if unit == "T" else 1e9
            pie_values = [v / divisor for v in pie_values]
            try:
                img = render_pie(pie_values, pie_labels, unit=unit)
                pie_img_seg = MessageSegment.image(f"base64://{img}")
            except Exception as e:
                logger.error("render chart failed: %s", e)

    # 将文字和饼图合并为一条消息
    if pie_img_seg is not None:
        return [Message(MessageSegment.text(s) + pie_img_seg)]
    return [s]
