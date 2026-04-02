"""角色查询"""
import base64
import datetime
import io
import json
import math
import os

import httpx
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from maplebot.commands.file_utils import _file_lock
from maplebot.utils.class_name import translate_class_name, translate_class_id
from maplebot.utils.config import level_exp_data

# ---------- 文件路径 ----------
_PLAYER_DATA_DIR = "player_data"
_PLAYER_NAME_FILE = "player_name.json"
os.makedirs(_PLAYER_DATA_DIR, exist_ok=True)


async def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        async with _file_lock:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


async def _save_json(path: str, data):
    tmp = path + ".tmp"
    async with _file_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp, path)


async def _load_player_names() -> dict[str, str]:
    return await _load_json(_PLAYER_NAME_FILE, {})


async def _save_player_names(names: dict[str, str]):
    await _save_json(_PLAYER_NAME_FILE, names)



# ---------- 经验处理工具 ----------
def _get_processed_y(exps, lvls, lvl_single, lvl_culm):
    exp_diffs = [0]
    lvl_decimals = [exps[0] / lvl_single.get(str(lvls[0]), 1) + lvls[0]]
    for i in range(1, len(exps)):
        exp_prev = lvl_culm.get(str(lvls[i - 1]), 0) + exps[i - 1]
        exp_curr = lvl_culm.get(str(lvls[i]), 0) + exps[i]
        exp_diffs.append(exp_curr - exp_prev)
        denom = lvl_single.get(str(lvls[i]), 1) or 1
        lvl_decimals.append(exps[i] / denom + lvls[i])
    return exp_diffs, lvl_decimals


def _format_series_data(times, exps, lvls):
    series_max = 14
    last_day = times[-1]
    days = [last_day - datetime.timedelta(days=i) for i in range(series_max)][::-1]
    dated_exps = []
    dated_lvls = []
    prev_lvl = None
    default_exp = None
    for day in days:
        if day not in times:
            dated_exps.append(default_exp)
            dated_lvls.append(prev_lvl)
        else:
            idx = times.index(day)
            dated_exps.append(exps[idx])
            dated_lvls.append(lvls[idx])
            prev_lvl = lvls[idx]
            default_exp = 0
    day_labels = [d.strftime("%m-%d") for d in days]
    return day_labels, dated_exps, dated_lvls


def _days_to_level(dated_exps, current_exp, current_lvl, lvl_single):
    filtered = [v for v in dated_exps if v is not None]
    denom = lvl_single.get(str(current_lvl))
    if not denom:
        return 10000, 0.0
    pct = round(current_exp / denom * 100, 1)
    if not filtered:
        return 10000, pct
    avg = sum(filtered) / len(filtered)
    needed = denom - current_exp
    if avg > 100:
        return min(round(needed / avg), 10000), pct
    return 10000, pct


# ---------- 图表绘制 ----------
def _draw_chart(days, dated_exps, dated_lvls) -> str:
    """绘制经验图表，返回 base64"""
    t = 1e12
    bar_values = []
    colors = []
    raw_exps = []
    for val in dated_exps:
        if val is None or val == 0:
            bar_values.append(0)
            colors.append("#4d6bff")
            raw_exps.append(0)
        else:
            v = val / t
            raw_exps.append(val)
            if v > 10:
                bar_values.append(10)
                colors.append("#ff6b6b")
            elif v < 0.2:
                bar_values.append(0.2)
                colors.append("#ffd93b")
            else:
                bar_values.append(v)
                colors.append("#4d6bff")

    line_values = [v if v is not None else 0 for v in dated_lvls]

    # 溢出标注：render_bar_line 不支持逐点文字标注，此处保留原始绘图逻辑
    matplotlib.use("Agg")

    x = np.arange(len(days))
    bg = "#050816"
    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(bg)
    ax1.set_facecolor(bg)

    ax1.bar(x, bar_values, color=colors, zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels(days, rotation=60, fontsize=10)
    ax1.set_ylim(0, 10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}T"))

    ax2 = ax1.twinx()
    ax2.plot(x, line_values, marker="o", linewidth=2, markersize=5, color="#9bff7a", zorder=4)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}"))

    # 溢出标注
    for i, (val, bv) in enumerate(zip(raw_exps, bar_values)):
        if val / t > 10:
            ax1.text(x=i, y=bv + 0.3, s=f"{val/t:.1f}T",
                     ha="center", va="bottom", color="#fff", fontsize=12, zorder=5)

    tick_color = "#a7adc4"
    for ax in (ax1, ax2):
        ax.tick_params(axis="both", colors=tick_color, labelsize=12)
    ax1.grid(False)
    ax2.grid(False)
    ax1.yaxis.grid(True, linestyle="-", linewidth=0.6, color="#262b3e", alpha=0.9, zorder=-1)
    for sp in ("top", "right", "left"):
        ax1.spines[sp].set_visible(False)
        ax2.spines[sp].set_visible(False)
    ax1.spines["bottom"].set_color("#20253a")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------- 主查询逻辑 ----------
async def _process_player_data(name: str) -> dict:
    """尝试从本地缓存读取玩家数据"""
    player_names = await _load_player_names()
    lower_map = {n.lower(): n for n in player_names}
    if name.lower() not in lower_map:
        player_names[name] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await _save_player_names(player_names)
        return {}
    actual_name = lower_map[name.lower()]
    player_file = os.path.join(_PLAYER_DATA_DIR, f"player_{actual_name}.json")
    player_dict = await _load_json(player_file, {})
    if not player_dict or "data" not in player_dict or not player_dict["data"]:
        return {}
    return player_dict


async def _try_local(name: str) -> Message | None:
    """从本地数据生成回复"""
    player_dict = await _process_player_data(name)
    if not player_dict:
        return None

    lvl_single: dict[str, int] = {}
    lvl_culm: dict[str, int] = {}
    acc = 0
    for i in range(1, 300):
        v = int(level_exp_data.get(f"data.{i}", 0) or 0)
        lvl_single[str(i)] = v
        lvl_culm[str(i)] = acc
        acc += v

    last = player_dict["data"][-1]
    pname = last["name"]
    level = last["level"]
    exp = last["exp"]
    legion = last.get("legionLevel", 0)
    job_name = translate_class_name(last.get("jobName", ""))
    avatar = player_dict.get("img", "")

    gdata = player_dict["data"]
    times = [
        datetime.datetime.fromisoformat(d["datetime"].split(" ")[0]) - datetime.timedelta(days=1)
        for d in gdata
    ]
    lvls = [d["level"] for d in gdata]
    exps = [d["exp"] for d in gdata]

    exp_diffs, lvl_decimals = _get_processed_y(exps, lvls, lvl_single, lvl_culm)
    days, dated_exps, dated_lvls = _format_series_data(times, exp_diffs, lvl_decimals)
    days_needed, exp_pct = _days_to_level(dated_exps, exp, level, lvl_single)

    has_change = any(v is not None and v != 0 for v in dated_exps)

    msg = Message()
    if avatar:
        try:
            base64.b64decode(avatar)
            msg += MessageSegment.image(f"base64://{avatar}")
        except Exception:
            pass

    text = f"角色名：{pname}\n职业：{job_name}\n等级：{level} ({exp_pct}%)\n联盟：{legion}\n"
    if has_change:
        text += f"预计还有{days_needed}天升级\n"
        msg += text
        try:
            chart = _draw_chart(days, dated_exps, dated_lvls)
            msg += MessageSegment.image(f"base64://{chart}")
        except Exception as e:
            logger.error(f"绘制图表失败: {e}")
    else:
        text += "近日无经验变化"
        msg += text

    return msg


async def find_role(name: str) -> Message | str:
    """查询角色信息，优先本地数据，失败则请求 maplestory.gg API"""
    # 1. 尝试本地数据
    local = await _try_local(name)
    if local:
        return local

    # 2. 请求 API
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"https://api.maplestory.gg/v2/public/character/gms/{name}")
    except Exception as e:
        logger.error(f"请求失败: {e}")
        return "请求失败"

    if resp.status_code == 404:
        return f"{name}已身死道消"
    if resp.status_code != 200:
        logger.error(f"请求失败 status={resp.status_code}")
        return "请求失败"

    try:
        data = resp.json()
    except Exception:
        return "解析失败"

    char = data.get("CharacterData")
    if not char:
        return "请求失败"

    # 翻译职业名
    class_name = translate_class_name(char.get("Class", ""))
    if not class_name:
        class_name = translate_class_id(char.get("ClassID", 0))

    msg = Message()

    # 角色图片
    img_url = char.get("CharacterImageURL", "")
    if img_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                img_resp = await client.get(img_url)
            if img_resp.status_code == 200:
                b64 = base64.b64encode(img_resp.content).decode("ascii")
                msg += MessageSegment.image(f"base64://{b64}")
        except Exception:
            pass

    level = char.get("Level", 0)
    exp_pct = char.get("EXPPercent", 0)
    legion = char.get("LegionLevel", 0)
    text = f"角色名：{char.get('Name', name)}\n职业：{class_name}\n等级：{level} ({exp_pct}%)\n联盟：{legion}\n"

    graph_data = char.get("GraphData", [])
    if not graph_data or not any(
        d.get("CurrentEXP", 0) != 0 for d in graph_data
    ):
        text += "近日无经验变化"
        msg += text
        return msg

    # 处理 GraphData 画图
    lvl_single = {}
    for i in range(1, 300):
        v = level_exp_data.get(f"data.{i}", 0)
        if v:
            lvl_single[str(i)] = int(v)

    exp_values = []
    level_values = []
    labels = []
    for j in range(1, len(graph_data)):
        prev = graph_data[j - 1]
        curr = graph_data[j]
        l0, l1 = prev["Level"], curr["Level"]
        e0, e1 = prev.get("CurrentEXP", 0), curr.get("CurrentEXP", 0)
        total = 0
        for lv in range(l0, l1):
            total += lvl_single.get(str(lv), 0)
        le0 = lvl_single.get(str(l0), 1) or 1
        le1 = lvl_single.get(str(l1), 1) or 1
        total -= (e0 / le0) * lvl_single.get(str(l0), 0)
        total += (e1 / le1) * lvl_single.get(str(l1), 0)
        exp_values.append(max(round(total), 0))
        level_values.append(l1 + e1 / le1)
        labels.append(curr["DateLabel"][5:])

    if not any(v != 0 for v in exp_values):
        text += "近日无经验变化"
        msg += text
        return msg

    # 预测升级天数
    avg = sum(exp_values) / len(exp_values) if exp_values else 0
    total_exp = lvl_single.get(str(level), 1) or 1
    remaining = total_exp - total_exp * exp_pct / 100
    days_pred = int(math.ceil(remaining / avg)) if avg > 0 else 10000
    text += f"预计还有{days_pred}天升级\n"
    msg += text

    # 画图
    try:
        chart = _draw_chart(labels, exp_values, level_values)
        msg += MessageSegment.image(f"base64://{chart}")
    except Exception as e:
        logger.error(f"render chart failed: {e}")

    return msg
