"""maplebot 主插件 - NoneBot2 命令路由"""
# pylint: disable=wrong-import-position
from __future__ import annotations

import random
from typing import Any

from nonebot import on_command, on_message, require
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import (
    Bot as V11Bot,
    GroupMessageEvent,
    MessageSegment as V11Seg,
)
from nonebot.log import logger
from nonebot.params import CommandArg, Command
from nonebot.rule import Rule

try:
    from nonebot.adapters.console import (
        MessageEvent as ConsoleMessageEvent,
    )
    _HAS_CONSOLE = True
except ImportError:
    ConsoleMessageEvent = None  # type: ignore[assignment, misc]
    _HAS_CONSOLE = False

# NoneBot2 要求在 require 之后再导入插件模块
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from maplebot.commands.arc_more_damage import get_more_damage_arc
from maplebot.commands.boss_party import (
    handle_boss_party,
    handle_subscribe,
    handle_unsubscribe,
)
from maplebot.commands.cube import calculate_cube, calculate_cube_all
from maplebot.commands.find_role import find_role
from maplebot.commands.scrape import scrape_role_background
from maplebot.commands.level_exp import (
    calculate_level_exp,
    calculate_exp_between_level,
    calculate_exp_damage,
)
from maplebot.commands.star_force import calculate_star_force, calculate_boom_count
from maplebot.utils.config import config, qun_db, find_role_data
from maplebot.utils.dict_tfidf import get_familiar_value, add_into_dict
from maplebot.utils.dict_entry import serialize_message, build_message

logger.opt(colors=True).info("<green>✅ maplebot_main 插件加载成功！</green>")

# ---------- 待添加词条队列 ----------
_add_db_qq_list: dict[int, str] = {}

_BOSS_LIST = list("3678946M绿黑赛狗")

_HELP_TIPS = [
    "查询 游戏名", "绑定 游戏名", "解绑",
    "洗魔方", "洗魔方 部位 [等级]",
    "模拟升星 200 0 22 [七折] [减爆] [保护]",
    "升级经验", "升级经验 起始级 目标级",
    "等级压制 等级差",
    "神秘压制",
    "我要开车 BOSS编号", "订阅开车 BOSS编号", "取消订阅 [BOSS编号]",
    "爆炸次数",
]


def _deal_key(s: str) -> str:
    """处理词条 key：中文数字转阿拉伯、转小写"""
    s = s.strip()
    trans = str.maketrans("零一二三四五六七八九", "0123456789")
    return s.translate(trans).lower()


def _in_valid_group(group_id: int) -> bool:
    groups = config.get("qq_groups", [])
    return int(group_id) in [int(g) for g in groups]


# ====================== 通用工具 ======================

async def _check_valid_group(event: Event) -> bool:
    """Rule：仅允许配置中的 QQ 群或 Console 事件"""
    if _is_console(event):
        return True
    if isinstance(event, GroupMessageEvent):
        return _in_valid_group(event.group_id)
    return False


_valid_group_rule = Rule(_check_valid_group)


def _get_user_id(event: Event) -> int:
    try:
        return int(event.get_user_id())
    except (ValueError, NotImplementedError):
        return 0


def _is_console(event: Event) -> bool:
    return _HAS_CONSOLE and ConsoleMessageEvent is not None and isinstance(event, ConsoleMessageEvent)


def _make_image_or_text(s: str, event: Event) -> Any:
    """OneBot 返回 MessageSegment.image；Console 返回纯文字占位。"""
    if _is_console(event):
        return s
    return V11Seg.image(f"base64://{s}")


async def _is_admin(bot: Bot, event: Event) -> bool:
    """判断当前用户是否为管理员"""
    if _is_console(event):
        return True
    if isinstance(bot, V11Bot) and isinstance(event, GroupMessageEvent):
        from maplebot.utils.perm import is_admin  # pylint: disable=import-outside-toplevel
        return await is_admin(bot, event.group_id, event.user_id)
    return False


# ====================== TF-IDF 追踪（最高优先级，不阻塞） ======================
_tfidf_tracker = on_message(priority=1, block=False)


@_tfidf_tracker.handle()
async def _handle_tfidf(event: Event):
    if not isinstance(event, GroupMessageEvent) or not _in_valid_group(event.group_id):
        return
    raw_text = event.get_plaintext().strip()
    if raw_text:
        add_into_dict(raw_text)


# ====================== 词条添加回调（高优先级，匹配时阻塞） ======================
_dict_callback = on_message(priority=5, block=False)


@_dict_callback.handle()
async def _handle_dict_callback(event: Event):
    if not isinstance(event, GroupMessageEvent) or not _in_valid_group(event.group_id):
        return
    user_id = _get_user_id(event)
    if user_id not in _add_db_qq_list:
        return
    key = _add_db_qq_list.pop(user_id)
    if key == "太阳":
        await _dict_callback.finish("未知错误")
        return
    # 序列化消息（图片会被下载到本地缓存）
    buf = serialize_message(event.get_message())
    m = qun_db.get_string_map_string("data")
    m[key] = buf
    qun_db.set("data", m)
    qun_db.save()
    await _dict_callback.finish("编辑词条成功")


# ====================== 命令处理器（priority=10） ======================

# ---- 查看帮助 ----
_help_cmd = on_command("查看帮助", rule=_valid_group_rule, priority=10, block=True)


@_help_cmd.handle()
async def _handle_help():
    await _help_cmd.finish("你可以使用以下功能：\n" + "\n".join(sorted(_HELP_TIPS)))


# ---- ping ----
_ping_cmd = on_command("ping", rule=_valid_group_rule, priority=10, block=True)


@_ping_cmd.handle()
async def _handle_ping(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        await _ping_cmd.finish("pong")


# ---- roll ----
_roll_cmd = on_command("roll", rule=_valid_group_rule, priority=10, block=True)


@_roll_cmd.handle()
async def _handle_roll(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        await _roll_cmd.finish(f"roll: {random.randint(0, 99)}")
    else:
        try:
            upper = int(content)
            if upper > 0:
                await _roll_cmd.finish(f"roll: {random.randint(1, upper)}")
        except ValueError:
            pass


# ---- 等级压制 ----
_exp_damage_cmd = on_command("等级压制", rule=_valid_group_rule, priority=10, block=True)


@_exp_damage_cmd.handle()
async def _handle_exp_damage(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        result = calculate_exp_damage(content)
        if result:
            await _exp_damage_cmd.finish(result)


# ---- 升级经验 ----
_level_exp_cmd = on_command("升级经验", rule=_valid_group_rule, priority=10, block=True)


@_level_exp_cmd.handle()
async def _handle_level_exp(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        result = calculate_level_exp()
        if result:
            await _level_exp_cmd.finish(_make_image_or_text(result, event))
    else:
        p = content.split(" ", 1)
        if len(p) == 2:
            try:
                start, end = int(p[0]), int(p[1])
                result = calculate_exp_between_level(start, end)
                if result:
                    await _level_exp_cmd.finish(result)
            except ValueError:
                pass


# ---- 爆炸次数 ----
_boom_cmd = on_command("爆炸次数", rule=_valid_group_rule, priority=10, block=True)


@_boom_cmd.handle()
async def _handle_boom(args=CommandArg()):
    content = args.extract_plain_text().strip()
    msgs = calculate_boom_count(content or "", new_kms=True)
    msgs += calculate_boom_count(content or "", new_kms=False)
    for msg in msgs:
        await _boom_cmd.send(msg)
    await _boom_cmd.finish()


# ---- 神秘压制 ----
_arc_cmd = on_command("神秘压制", rule=_valid_group_rule, priority=10, block=True)


@_arc_cmd.handle()
async def _handle_arc(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        result = get_more_damage_arc()
        if result:
            await _arc_cmd.finish(_make_image_or_text(result, event))


# ---- 模拟升星 / 模拟上星 / 升星期望 / 上星期望 ----
_star_force_cmd = on_command(
    "模拟升星",
    aliases={"模拟上星", "升星期望", "上星期望", "模拟升星旧", "模拟上星旧", "升星期望旧", "上星期望旧"},
    rule=_valid_group_rule,
    priority=10,
    block=True,
)


@_star_force_cmd.handle()
async def _handle_star_force(cmd: tuple[str, ...] = Command(), args=CommandArg()):
    cmd_name = cmd[0]
    new_kms = not cmd_name.endswith("旧")
    content = args.extract_plain_text().strip()
    if not content:
        await _star_force_cmd.finish("命令格式：\r\n模拟升星 200 0 22\r\n后面可以加：七折、减爆、保护")
    else:
        result = calculate_star_force(new_kms, content)
        for msg in result:
            await _star_force_cmd.send(msg)
        await _star_force_cmd.finish()


# ---- 洗魔方 ----
_cube_cmd = on_command("洗魔方", rule=_valid_group_rule, priority=10, block=True)


@_cube_cmd.handle()
async def _handle_cube(args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_cube_all() if not content else calculate_cube(content)
    for msg in result:
        await _cube_cmd.send(msg)
    await _cube_cmd.finish()


# ---- 查询我 ----
_query_me_cmd = on_command("查询我", rule=_valid_group_rule, priority=10, block=True)


@_query_me_cmd.handle()
async def _handle_query_me(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        user_id = _get_user_id(event)
        data = find_role_data.get_string_map_string("data")
        name = data.get(str(user_id), "")
        if not name:
            await _query_me_cmd.finish("你还未绑定")
        else:
            result = await find_role(name)
            if _is_console(event) and not isinstance(result, str):
                await _query_me_cmd.finish(result.extract_plain_text())
            else:
                await _query_me_cmd.finish(result)


# ---- 查询绑定 QQ号 ----
_query_bind_cmd = on_command("查询绑定", rule=_valid_group_rule, priority=10, block=True)


@_query_bind_cmd.handle()
async def _handle_query_bind(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        try:
            qq = int(content)
            data = find_role_data.get_string_map_string("data")
            name = data.get(str(qq), "")
            if name:
                await _query_bind_cmd.finish(f"该玩家绑定了：{name}")
            else:
                await _query_bind_cmd.finish("该玩家还未绑定")
        except ValueError:
            await _query_bind_cmd.finish("命令格式：查询绑定 QQ号")


# ---- 查询词条 / 搜索词条 ----
_search_dict_cmd = on_command(
    "查询词条", aliases={"搜索词条"}, rule=_valid_group_rule, priority=10, block=True,
)


@_search_dict_cmd.handle()
async def _handle_search_dict(args=CommandArg()):
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        await _deal_search_dict(_search_dict_cmd, key)


# ---- 查询 游戏名 ----
_query_cmd = on_command("查询", rule=_valid_group_rule, priority=10, block=True)


@_query_cmd.handle()
async def _handle_query(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content and " " not in content:
        result = await find_role(content)
        if _is_console(event) and not isinstance(result, str):
            await _query_cmd.finish(result.extract_plain_text())
        else:
            await _query_cmd.finish(result)


# ---- 绑定 ----
_bind_cmd = on_command("绑定", rule=_valid_group_rule, priority=10, block=True)


@_bind_cmd.handle()
async def _handle_bind(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content and " " not in content:
        user_id = _get_user_id(event)
        data = find_role_data.get_string_map_string("data")
        uid = str(user_id)
        if uid in data and data[uid]:
            await _bind_cmd.finish("你已经绑定过了，如需更换请先解绑")
        else:
            data[uid] = content
            find_role_data.set("data", data)
            find_role_data.save()
            await _bind_cmd.finish("绑定成功")


# ---- 解绑 ----
_unbind_cmd = on_command("解绑", rule=_valid_group_rule, priority=10, block=True)


@_unbind_cmd.handle()
async def _handle_unbind(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        user_id = _get_user_id(event)
        data = find_role_data.get_string_map_string("data")
        uid = str(user_id)
        if uid in data and data[uid]:
            del data[uid]
            find_role_data.set("data", data)
            find_role_data.save()
            await _unbind_cmd.finish("解绑成功")
        else:
            await _unbind_cmd.finish("你还未绑定")


# ---- 我要开车 ----
_kaiche_cmd = on_command("我要开车", rule=_valid_group_rule, priority=10, block=True)


@_kaiche_cmd.handle()
async def _handle_kaiche(bot: Bot, event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if _is_console(event):
        await _kaiche_cmd.finish("（Console 调试模式不支持开车功能，需要 OneBot V11 环境）")
    elif isinstance(bot, V11Bot) and isinstance(event, GroupMessageEvent):
        result = await handle_boss_party(bot, event, _BOSS_LIST, content)
        if result:
            await _kaiche_cmd.finish(result)


# ---- 订阅开车 ----
_subscribe_cmd = on_command("订阅开车", rule=_valid_group_rule, priority=10, block=True)


@_subscribe_cmd.handle()
async def _handle_subscribe(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    user_id = _get_user_id(event)
    result = handle_subscribe(_BOSS_LIST, content, user_id)
    if result:
        await _subscribe_cmd.finish(result)


# ---- 取消订阅 ----
_unsubscribe_cmd = on_command("取消订阅", rule=_valid_group_rule, priority=10, block=True)


@_unsubscribe_cmd.handle()
async def _handle_unsubscribe(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    user_id = _get_user_id(event)
    result = handle_unsubscribe(_BOSS_LIST, content, user_id)
    if result:
        await _unsubscribe_cmd.finish(result)


# ---- 添加词条（管理员） ----
_add_dict_cmd = on_command("添加词条", rule=_valid_group_rule, priority=10, block=True)


@_add_dict_cmd.handle()
async def _handle_add_dict(bot: Bot, event: Event, args=CommandArg()):
    if not await _is_admin(bot, event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        user_id = _get_user_id(event)
        await _deal_add_dict(_add_dict_cmd, user_id, key)


# ---- 修改词条（管理员） ----
_modify_dict_cmd = on_command("修改词条", rule=_valid_group_rule, priority=10, block=True)


@_modify_dict_cmd.handle()
async def _handle_modify_dict(bot: Bot, event: Event, args=CommandArg()):
    if not await _is_admin(bot, event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        user_id = _get_user_id(event)
        await _deal_modify_dict(_modify_dict_cmd, user_id, key)


# ---- 删除词条（管理员） ----
_delete_dict_cmd = on_command("删除词条", rule=_valid_group_rule, priority=10, block=True)


@_delete_dict_cmd.handle()
async def _handle_delete_dict(bot: Bot, event: Event, args=CommandArg()):
    if not await _is_admin(bot, event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        await _deal_remove_dict(_delete_dict_cmd, key)


# ====================== 词条模糊匹配（最低优先级） ======================
_dict_fallback = on_message(priority=20, block=False)


@_dict_fallback.handle()
async def _handle_dict_fallback(event: Event):
    if not isinstance(event, GroupMessageEvent) or not _in_valid_group(event.group_id):
        return
    raw_text = event.get_plaintext().strip()
    if not raw_text:
        return
    m = qun_db.get_string_map_string("data")
    s = get_familiar_value(m, _deal_key(raw_text))
    if not s:
        return
    msg = build_message(s)
    if msg:
        await _dict_fallback.finish(msg)


# ====================== 词条 CRUD ======================
async def _deal_add_dict(matcher, user_id: int, key: str):
    if "." in key:
        await matcher.finish("词条名称中不能包含 . 符号")
        return
    if key == "太阳":
        await matcher.finish("未知错误")
        return
    m = qun_db.get_string_map_string("data")
    if key in m:
        await matcher.finish("词条已存在")
    else:
        await matcher.send("请输入要添加的内容")
        _add_db_qq_list[user_id] = key


async def _deal_modify_dict(matcher, user_id: int, key: str):
    m = qun_db.get_string_map_string("data")
    if key not in m:
        await matcher.finish("词条不存在")
    else:
        await matcher.send("请输入要修改的内容")
        _add_db_qq_list[user_id] = key


async def _deal_remove_dict(matcher, key: str):
    if key == "太阳":
        await matcher.finish("未知错误")
        return
    m = qun_db.get_string_map_string("data")
    if key not in m:
        await matcher.finish("词条不存在")
        return
    del m[key]
    qun_db.set("data", m)
    qun_db.save()
    await matcher.finish("删除词条成功")


async def _deal_search_dict(matcher, key: str):
    m = qun_db.get_string_map_string("data")
    res = sorted([k for k in m if key in k])
    if res:
        num = len(res)
        if num > 10:
            res = res[:10]
            res[9] += f"\n等{num}个词条"
        lines = [f"{i + 1}. {r}" for i, r in enumerate(res)]
        await matcher.finish("搜索到以下词条：\n" + "\n".join(lines))
    else:
        await matcher.finish(f"搜索不到词条({key})")


# ====================== 定时任务：角色数据预抓取 ======================
async def _cron_find_role():
    logger.info("[cron] 开始角色数据预抓取")
    await scrape_role_background()


for _hour in (1, 9, 15):
    scheduler.add_job(
        _cron_find_role,
        "cron",
        hour=_hour,
        minute=0,
        second=0,
        id=f"find_role_bg_{_hour:02d}",
        timezone="Asia/Shanghai",
    )
