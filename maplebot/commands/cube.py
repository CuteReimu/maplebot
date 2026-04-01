"""魔方概率计算"""
import json
import logging
import os

from nonebot.adapters.onebot.v11 import MessageSegment

from maplebot.utils.charts import render_table

logger = logging.getLogger("maplebot.cube")

# ---------- 加载 cubeRates.json ----------
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
with open(os.path.join(_DATA_DIR, "cubeRates.json"), "r", encoding="utf-8") as _f:
    _cube_rates: dict = json.load(_f)

# ---------- 常量映射 ----------
_NAME_MAP: dict[str, tuple[str, int]] = {
    "戒指": ("accessory", 150), "项链": ("accessory", 150),
    "耳环": ("accessory", 150), "首饰": ("accessory", 150),
    "腰带": ("belt", 150), "副手": ("secondary", 140),
    "上衣": ("top", 150), "下衣": ("bottom", 150),
    "披风": ("cape", 200), "纹章": ("emblem", 100),
    "手套": ("gloves", 200), "帽子": ("hat", 150),
    "心脏": ("heart", 100), "套服": ("overall", 200),
    "鞋子": ("shoes", 200), "护肩": ("shoulder", 200),
    "武器": ("weapon", 200),
}

_STAT_MAP: dict[str, str] = {
    "percStat": "%s%%+属性", "lineStat": "%s条属性",
    "percAtt": "%s%%+攻", "lineAtt": "%s条攻",
    "percBoss": "%s%%+BD", "lineBoss": "%s条BD",
    "lineIed": "%s条无视", "lineCritDamage": "%s条爆伤",
    "lineMeso": "%s条钱", "lineDrop": "%s条爆",
    "lineMesoOrDrop": "%s条钱爆", "secCooldown": "%s秒CD",
    "lineAttOrBoss": "%s条攻或BD",
    "lineAttOrBossOrIed": "总计%s条有用属性",
    "lineBossOrIed": "%s条BD或无视",
}

# ---------- 选项列表 ----------
_DEFAULT_SEL = [
    "percStat+18", "percStat+21", "percStat+24",
    "percStat+27", "percStat+30", "percStat+33", "percStat+36",
]
_DEFAULT_SEL_160 = _DEFAULT_SEL + ["percStat+39"]

_ACCESSORY_SEL = _DEFAULT_SEL + [
    "lineMeso+1", "lineDrop+1", "lineMesoOrDrop+1",
    "lineMeso+2", "lineDrop+2", "lineMesoOrDrop+2",
    "lineMeso+3", "lineDrop+3",
    "lineMeso+1&lineStat+1", "lineDrop+1&lineStat+1", "lineMesoOrDrop+1&lineStat+1",
]
_ACCESSORY_SEL_160 = _DEFAULT_SEL_160 + [
    "lineMeso+1", "lineDrop+1", "lineMesoOrDrop+1",
    "lineMeso+2", "lineDrop+2", "lineMesoOrDrop+2",
    "lineMeso+3", "lineDrop+3",
    "lineMeso+1&lineStat+1", "lineDrop+1&lineStat+1", "lineMesoOrDrop+1&lineStat+1",
]

_HAT_SEL = _DEFAULT_SEL + [
    "secCooldown+2", "secCooldown+3", "secCooldown+4", "secCooldown+5", "secCooldown+6",
    "secCooldown+2&lineStat+2",
    "secCooldown+2&lineStat+1", "secCooldown+3&lineStat+1", "secCooldown+4&lineStat+1",
]
_HAT_SEL_160 = _DEFAULT_SEL_160 + [
    "secCooldown+2", "secCooldown+3", "secCooldown+4", "secCooldown+5", "secCooldown+6",
    "secCooldown+2&lineStat+2",
    "secCooldown+2&lineStat+1", "secCooldown+3&lineStat+1", "secCooldown+4&lineStat+1",
]

_GLOVE_SEL = _DEFAULT_SEL + [
    "lineCritDamage+1", "lineCritDamage+2", "lineCritDamage+3",
    "lineCritDamage+1&lineStat+1", "lineCritDamage+1&lineStat+2", "lineCritDamage+2&lineStat+1",
]
_GLOVE_SEL_160 = _DEFAULT_SEL_160 + [
    "lineCritDamage+1", "lineCritDamage+2", "lineCritDamage+3",
    "lineCritDamage+1&lineStat+1", "lineCritDamage+1&lineStat+2", "lineCritDamage+2&lineStat+1",
]

_WS_SEL = [
    "percAtt+18", "percAtt+21", "percAtt+24", "percAtt+30", "percAtt+33", "percAtt+36",
    "lineIed+1&percAtt+18", "lineIed+1&percAtt+21", "lineIed+1&percAtt+24",
    "lineAttOrBossOrIed+1", "lineAttOrBossOrIed+2", "lineAttOrBossOrIed+3",
    "lineAtt+1&lineAttOrBossOrIed+2", "lineAtt+1&lineAttOrBossOrIed+3", "lineAtt+2&lineAttOrBossOrIed+3",
    "lineAtt+1&lineBoss+1", "lineAtt+1&lineBoss+2", "lineAtt+2&lineBoss+1",
    "percAtt+21&percBoss+30", "percAtt+21&percBoss+35", "percAtt+21&percBoss+40",
    "percAtt+24&percBoss+30",
    "lineAttOrBoss+1", "lineAttOrBoss+2", "lineAttOrBoss+3",
]
_WS_SEL_160 = [
    "percAtt+20", "percAtt+23", "percAtt+26", "percAtt+33", "percAtt+36", "percAtt+39",
    "lineIed+1&percAtt+20", "lineIed+1&percAtt+23", "lineIed+1&percAtt+26",
    "lineAttOrBossOrIed+1", "lineAttOrBossOrIed+2", "lineAttOrBossOrIed+3",
    "lineAtt+1&lineAttOrBossOrIed+2", "lineAtt+1&lineAttOrBossOrIed+3", "lineAtt+2&lineAttOrBossOrIed+3",
    "lineAtt+1&lineBoss+1", "lineAtt+1&lineBoss+2", "lineAtt+2&lineBoss+1",
    "percAtt+23&percBoss+30", "percAtt+23&percBoss+35", "percAtt+23&percBoss+40",
    "percAtt+26&percBoss+30",
    "lineAttOrBoss+1", "lineAttOrBoss+2", "lineAttOrBoss+3",
]
_E_SEL = [
    "percAtt+18", "percAtt+21", "percAtt+24", "percAtt+30", "percAtt+33", "percAtt+36",
    "lineIed+1&percAtt+18", "lineIed+1&percAtt+21", "lineIed+1&percAtt+24",
    "lineAttOrBossOrIed+1", "lineAttOrBossOrIed+2", "lineAttOrBossOrIed+3",
    "lineAtt+1&lineAttOrBossOrIed+2", "lineAtt+1&lineAttOrBossOrIed+3", "lineAtt+2&lineAttOrBossOrIed+3",
]
_E_SEL_160 = [
    "percAtt+20", "percAtt+23", "percAtt+26", "percAtt+33", "percAtt+36", "percAtt+39",
    "lineIed+1&percAtt+20", "lineIed+1&percAtt+23", "lineIed+1&percAtt+26",
    "lineAttOrBossOrIed+1", "lineAttOrBossOrIed+2", "lineAttOrBossOrIed+3",
    "lineAtt+1&lineAttOrBossOrIed+2", "lineAtt+1&lineAttOrBossOrIed+3", "lineAtt+2&lineAttOrBossOrIed+3",
]

# ---------- 潜能类别常量 ----------
CAT_STR = "STR %"
CAT_DEX = "DEX %"
CAT_INT = "INT %"
CAT_LUK = "LUK %"
CAT_MAXHP = "Max HP %"
CAT_ALLSTAT = "All Stats %"
CAT_ATT = "ATT %"
CAT_MATT = "MATT %"
CAT_BOSS = "Boss Damage"
CAT_IED = "Ignore Enemy Defense %"
CAT_MESO = "Meso Amount %"
CAT_DROP = "Item Drop Rate %"
CAT_AUTOSTEAL = "Chance to auto steal %"
CAT_CRITDMG = "Critical Damage %"
CAT_CDR = "Skill Cooldown Reduction"
CAT_JUNK = "Junk"
CAT_DECENT = "Decent Skill"
CAT_INVINCIBLE_P = "Chance of being invincible for seconds when hit"
CAT_INVINCIBLE_T = "Increase invincibility time after being hit"
CAT_IGNOREDMG = "Chance to ignore % damage when hit"

_MAX_CATEGORY_COUNT = {
    CAT_DECENT: 1, CAT_INVINCIBLE_T: 1, CAT_IED: 3,
    CAT_BOSS: 3, CAT_DROP: 3, CAT_IGNOREDMG: 2, CAT_INVINCIBLE_P: 2,
}

_INPUT_CATEGORY_MAP = {
    "percStat": [CAT_STR, CAT_ALLSTAT],
    "lineStat": [CAT_STR, CAT_ALLSTAT],
    "percAtt": [CAT_ATT], "lineAtt": [CAT_ATT],
    "percBoss": [CAT_BOSS], "lineBoss": [CAT_BOSS],
    "lineIed": [CAT_IED], "lineCritDamage": [CAT_CRITDMG],
    "lineMeso": [CAT_MESO], "lineDrop": [CAT_DROP],
    "lineMesoOrDrop": [CAT_DROP, CAT_MESO],
    "secCooldown": [CAT_CDR], "lineAutoSteal": [CAT_AUTOSTEAL],
    "lineAttOrBoss": [CAT_ATT, CAT_BOSS],
    "lineAttOrBossOrIed": [CAT_ATT, CAT_BOSS, CAT_IED],
}

_TIER_RATES = {
    "occult": {0: 0.009901},
    "master": {0: 0.1184, 1: 0.0381},
    "meister": {0: 0.1163, 1: 0.0879, 2: 0.0459},
    "red": {0: 0.14, 1: 0.06, 2: 0.025},
    "black": {0: 0.17, 1: 0.11, 2: 0.05},
}

_CUBE_COST = {"red": 12_000_000, "black": 22_000_000, "master": 7_500_000}

_TIER_NAMES = {0: "rare", 1: "epic", 2: "unique", 3: "legendary"}


def _format_int64(i: int) -> str:
    if abs(i) < 1_000_000_000_000:
        return f"{i / 1_000_000_000:.2f}B"
    return f"{i / 1_000_000_000_000:.2f}T"


def _get_selection(name: str, item_level: int) -> list[str]:
    high = item_level >= 160
    if name == "emblem":
        return _E_SEL_160 if high else _E_SEL
    if name in ("weapon", "secondary"):
        return _WS_SEL_160 if high else _WS_SEL
    if name == "accessory":
        return _ACCESSORY_SEL_160 if high else _ACCESSORY_SEL
    if name == "hat":
        return _HAT_SEL_160 if high else _HAT_SEL
    if name == "gloves":
        return _GLOVE_SEL_160 if high else _GLOVE_SEL
    return _DEFAULT_SEL_160 if high else _DEFAULT_SEL


def _get_distr_quantile(p: float):
    mean = 1 / p
    return mean


def _get_tier_costs(current_tier: int, desire_tier: int, cube_type: str) -> float:
    total_mean = 0.0
    for i in range(current_tier, desire_tier):
        p = _TIER_RATES[cube_type].get(i, 0)
        if p > 0:
            total_mean += 1 / p
    return total_mean


def _get_reveal_cost_constant(item_level: int) -> float:
    if item_level < 30:
        return 0.0
    if item_level <= 70:
        return 0.5
    if item_level <= 120:
        return 2.5
    return 20.0


def _cubing_cost(cube_type: str, item_level: int, total_cube_count: float) -> float:
    cc = _CUBE_COST[cube_type]
    reveal = _get_reveal_cost_constant(item_level) * item_level * item_level
    return cc * total_cube_count + total_cube_count * reveal


def _translate_input(input_str: str) -> dict[str, int]:
    output: dict[str, int] = {}
    if not input_str:
        return output
    for val in input_str.split("&"):
        parts = val.split("+")
        if len(parts) == 2:
            output[parts[0]] = output.get(parts[0], 0) + int(parts[1])
    return output


def _get_useful_categories(prob_input: dict[str, int]) -> list[str]:
    useful: list[str] = []
    for field, cats in _INPUT_CATEGORY_MAP.items():
        if prob_input.get(field, 0) > 0:
            for c in cats:
                if c not in useful:
                    useful.append(c)
    return useful


def _convert_cube_data_for_level(cube_data: list[list], item_level: int) -> list[list]:
    if item_level < 160:
        return cube_data
    affected = {CAT_STR, CAT_LUK, CAT_DEX, CAT_INT, CAT_ALLSTAT, CAT_ATT, CAT_MATT}

    def adjust(line):
        ret = []
        for e in line:
            cat, val, rate = e[0], e[1], e[2]
            if cat in affected:
                val = val + 1
            ret.append([cat, val, rate])
        return ret

    return [adjust(cube_data[0]), adjust(cube_data[1]), adjust(cube_data[2])]


def _get_consolidated_rates(rates_list, useful_categories):
    consolidated = []
    junk_rate = 0.0
    junk_categories = []
    for e in rates_list:
        cat, val, rate = e[0], e[1], e[2]
        if cat in useful_categories or _MAX_CATEGORY_COUNT.get(cat, 0) > 0:
            consolidated.append(e)
        elif cat == CAT_JUNK:
            junk_rate += rate
            if isinstance(val, list):
                junk_categories.extend(val)
        else:
            junk_rate += rate
            junk_categories.append(f"{cat} ({val})")
    consolidated.append([CAT_JUNK, junk_categories, junk_rate])
    return consolidated


def _calculate_total(outcome, desired_category, calc_val=False):
    if calc_val:
        return sum(int(a[1]) for a in outcome if a[0] == desired_category)
    return sum(1 for a in outcome if a[0] == desired_category)


# 判断函数映射
def _outcome_match(outcome, prob_input: dict[str, int]) -> bool:
    for field, required in prob_input.items():
        if not _MATCH_FNS.get(field, lambda o, r: False)(outcome, required):
            return False
    return True


_MATCH_FNS = {
    "percStat": lambda o, r: _calculate_total(o, CAT_STR, True) + _calculate_total(o, CAT_ALLSTAT, True) >= r,
    "lineStat": lambda o, r: _calculate_total(o, CAT_STR, False) + _calculate_total(o, CAT_ALLSTAT, False) >= r,
    "percAtt": lambda o, r: _calculate_total(o, CAT_ATT, True) >= r,
    "lineAtt": lambda o, r: _calculate_total(o, CAT_ATT, False) >= r,
    "percBoss": lambda o, r: _calculate_total(o, CAT_BOSS, True) >= r,
    "lineBoss": lambda o, r: _calculate_total(o, CAT_BOSS, False) >= r,
    "lineIed": lambda o, r: _calculate_total(o, CAT_IED, False) >= r,
    "lineCritDamage": lambda o, r: _calculate_total(o, CAT_CRITDMG, False) >= r,
    "lineMeso": lambda o, r: _calculate_total(o, CAT_MESO, False) >= r,
    "lineDrop": lambda o, r: _calculate_total(o, CAT_DROP, False) >= r,
    "lineMesoOrDrop": lambda o, r: _calculate_total(o, CAT_MESO, False) + _calculate_total(o, CAT_DROP, False) >= r,
    "secCooldown": lambda o, r: _calculate_total(o, CAT_CDR, True) >= r,
    "lineAttOrBoss": lambda o, r: _calculate_total(o, CAT_ATT, False) + _calculate_total(o, CAT_BOSS, False) >= r,
    "lineAttOrBossOrIed": lambda o, r: (
        _calculate_total(o, CAT_ATT, False) +
        _calculate_total(o, CAT_BOSS, False) +
        _calculate_total(o, CAT_IED, False) >= r
    ),
    "lineBossOrIed": lambda o, r: _calculate_total(o, CAT_BOSS, False) + _calculate_total(o, CAT_IED, False) >= r,
}


def _get_adjusted_rate(current_line, previous_lines, current_pool):
    cat = current_line[0]
    rate = current_line[2]
    if not previous_lines:
        return rate
    prev_special = {}
    for a in previous_lines:
        c = a[0]
        if c in _MAX_CATEGORY_COUNT:
            prev_special[c] = prev_special.get(c, 0) + 1
    to_remove = []
    for sp_cat, count in prev_special.items():
        if count > _MAX_CATEGORY_COUNT[sp_cat]:
            return 0.0
        if sp_cat == cat and count + 1 > _MAX_CATEGORY_COUNT[sp_cat]:
            return 0.0
        if count == _MAX_CATEGORY_COUNT[sp_cat]:
            to_remove.append(sp_cat)
    adjusted_total = 100.0
    adjusted = False
    for a in current_pool:
        if a[0] in to_remove:
            adjusted_total -= a[2]
            adjusted = True
    if adjusted:
        return rate / adjusted_total * 100
    return rate


def _calculate_rate(outcome, filtered_rates):
    rates = [
        _get_adjusted_rate(outcome[0], [], filtered_rates[0]),
        _get_adjusted_rate(outcome[1], [outcome[0]], filtered_rates[1]),
        _get_adjusted_rate(outcome[2], [outcome[0], outcome[1]], filtered_rates[2]),
    ]
    chance = 100.0
    for r in rates:
        chance *= r / 100
    return chance


def _get_probability(desired_tier, prob_input, item_type, cube_type, item_level):
    tier = _TIER_NAMES[desired_tier]
    label = "ring" if item_type == "accessory" else ("heart" if item_type == "badge" else item_type)
    raw = [
        _cube_rates["lvl120to200"][label][cube_type][tier]["first_line"],
        _cube_rates["lvl120to200"][label][cube_type][tier]["second_line"],
        _cube_rates["lvl120to200"][label][cube_type][tier]["third_line"],
    ]
    cube_data = _convert_cube_data_for_level(raw, item_level)
    useful = _get_useful_categories(prob_input)
    consolidated = [
        _get_consolidated_rates(cube_data[0], useful),
        _get_consolidated_rates(cube_data[1], useful),
        _get_consolidated_rates(cube_data[2], useful),
    ]
    total_chance = 0.0
    for l1 in consolidated[0]:
        for l2 in consolidated[1]:
            for l3 in consolidated[2]:
                outcome = [l1, l2, l3]
                if _outcome_match(outcome, prob_input):
                    total_chance += _calculate_rate(outcome, consolidated)
    return total_chance / 100.0


def _run_calculator(item_type, cube_type, current_tier, item_level, desired_tier, desired_stat):
    any_stats = not desired_stat
    prob_input = _translate_input(desired_stat)
    p = 1.0
    if not any_stats:
        p = _get_probability(desired_tier, prob_input, item_type, cube_type, item_level)
    tier_up_mean = _get_tier_costs(current_tier, desired_tier, cube_type)
    stat_mean = 0.0
    if not any_stats and p > 0:
        stat_mean = 1 / p
    mean_float = stat_mean + tier_up_mean
    mean_cost = _cubing_cost(cube_type, item_level, mean_float)
    return round(mean_float), round(mean_cost)


def _format_stat_target(it: str) -> str:
    parts = it.split("&")
    result = ""
    for stat in parts:
        arr = stat.split("+")
        if len(arr) == 2 and arr[0] in _STAT_MAP:
            result += _STAT_MAP[arr[0]] % arr[1]
    return result


# ====================== 公开接口 ======================

def calculate_cube_all() -> list:
    """洗魔方（无参数）- 生成全部位概览表格"""
    # 筛选部位
    skip_names = {"weapon", "secondary", "emblem", "overall"}
    skip_labels = {"戒指", "项链", "耳环"}
    names: list[str] = []
    for s, (name, _) in _NAME_MAP.items():
        if name in skip_names or s in skip_labels:
            continue
        names.append(s)

    selections = _DEFAULT_SEL_160
    rows: list[list[str]] = []
    row_colors_map: list[list[str | None]] = []
    costs_for_sort: dict[str, int] = {}

    for s in names:
        item_name, item_level = _NAME_MAP[s]
        row = [f"{item_level}{s}"]
        colors_row: list[str | None] = []
        for it in selections:
            if item_level < 160 and it == "percStat+39":
                row.append("")
                colors_row.append(None)
                continue
            _, red_cost = _run_calculator(item_name, "red", 3, item_level, 3, it)
            _, black_cost = _run_calculator(item_name, "black", 3, item_level, 3, it)
            if red_cost <= black_cost:
                colors_row.append("#0084C760")  # 蓝(红魔方)
                cost = red_cost
            else:
                colors_row.append("#931598E0")  # 紫(黑魔方)
                cost = black_cost
            row.append(_format_int64(cost))
            if it == "percStat+27":
                costs_for_sort[s] = cost
        rows.append(row)
        row_colors_map.append(colors_row)

    # 排序
    indices = list(range(len(names)))
    indices.sort(key=lambda i: (_NAME_MAP[names[i]][1], costs_for_sort.get(names[i], 0)))
    rows = [rows[i] for i in indices]
    row_colors_map = [row_colors_map[i] for i in indices]

    header = ["部位"] + [_format_stat_target(it) for it in selections]

    # 构建 cell_colors（header 列不参与上色，从第 1 列开始）
    cell_colors: list[list[str | None]] = []
    for row_c in row_colors_map:
        cell_colors.append([None] + row_c)

    try:
        img = render_table(
            header=header, data=rows, width=770,
            cell_colors=cell_colors,
        )
        return [MessageSegment.image(f"base64://{img}")]
    except Exception as e:
        logger.error("生成表格失败: %s", e)
        return []


def calculate_cube(s: str) -> list:
    """洗魔方 <部位> [等级]"""
    parts = s.split(" ")
    label = parts[0]
    if label not in _NAME_MAP:
        return []
    item_name, item_level = _NAME_MAP[label]
    if len(parts) >= 2:
        try:
            lv = int(parts[1])
            if lv < 71:
                return ["不能低于71级"]
            if lv > 300:
                return ["不能高于300级"]
            item_level = lv
        except ValueError:
            return []

    label = label.lstrip("0123456789")
    selections = _get_selection(item_name, item_level)

    rows: list[list[str]] = []
    row_colors: list[list[str | None]] = []

    # 紫洗绿
    _, e_red = _run_calculator(item_name, "red", 1, item_level, 3, "")
    _, e_black = _run_calculator(item_name, "black", 1, item_level, 3, "")
    if e_red < e_black:
        row_colors.append([None, "#0084C760"])
        e_cost = e_red
    else:
        row_colors.append([None, "#931598E0"])
        e_cost = e_black
    rows.append(["紫洗绿", _format_int64(e_cost)])

    for it in selections:
        _, red_cost = _run_calculator(item_name, "red", 3, item_level, 3, it)
        _, black_cost = _run_calculator(item_name, "black", 3, item_level, 3, it)
        if red_cost <= black_cost:
            row_colors.append([None, "#0084C760"])
            cost = red_cost
        else:
            row_colors.append([None, "#931598E0"])
            cost = black_cost
        rows.append([_format_stat_target(it), _format_int64(cost)])

    try:
        img = render_table(
            header=[f"{item_level}级{label}", "（底色表示魔方颜色）"],
            data=rows, width=250, cell_colors=row_colors,
        )
        return [MessageSegment.image(f"base64://{img}")]
    except Exception as e:
        logger.error("生成表格失败: %s", e)
        return []
