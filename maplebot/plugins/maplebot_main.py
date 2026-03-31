"""maplebot 主插件 - NoneBot2 命令路由"""
from __future__ import annotations

import json
import logging
import random
from typing import Any, Callable, Awaitable

from nonebot import on_message
from nonebot.log import logger as nb_logger
from nonebot.adapters.onebot.v11 import (
    Bot as V11Bot,
    GroupMessageEvent,
    MessageSegment as V11Seg,
)

try:
    from nonebot.adapters.console import (
        Bot as ConsoleBot,
        MessageEvent as ConsoleMessageEvent,
        MessageSegment as ConSeg,
    )
    _HAS_CONSOLE = True
except ImportError:
    _HAS_CONSOLE = False

from maplebot.commands.arc_more_damage import get_more_damage_arc
from maplebot.commands.boss_party import (
    handle_boss_party,
    handle_subscribe,
    handle_unsubscribe,
)
from maplebot.commands.cube import calculate_cube, calculate_cube_all
from maplebot.commands.find_role import find_role
from maplebot.commands.gen_table import gen_table
from maplebot.commands.level_exp import (
    calculate_level_exp,
    calculate_exp_between_level,
    calculate_exp_damage,
)
from maplebot.commands.potion import calculate_potion
from maplebot.commands.star_force import calculate_star_force, calculate_boom_count
from maplebot.utils.config import config, qun_db, find_role_data
from maplebot.utils.dict_tfidf import get_familiar_value, add_into_dict

logger = logging.getLogger("maplebot.plugin")
nb_logger.opt(colors=True).info("<green>✅ maplebot_main 插件加载成功！</green>")

# ====================== Matchers ======================
group_msg = on_message(priority=10, block=False)
if _HAS_CONSOLE:
    console_msg = on_message(priority=10, block=False)

# ---------- 待添加词条队列 ----------
_add_db_qq_list: dict[int, str] = {}

_BOSS_LIST = list("3678946M绿黑赛狗")

_HELP_TIPS = [
    "查询 游戏名", "绑定 游戏名", "解绑",
    "洗魔方", "洗魔方 部位 [等级]",
    "模拟升星 200 0 22 [七折] [减爆] [保护]",
    "升级经验", "升级经验 起始级 目标级",
    "8421", "等级压制 等级差",
    "生成表格", "神秘压制",
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


# ====================== 通用发送回调类型 ======================
# send(message) — 统一的回复函数
SendFunc = Callable[[Any], Awaitable[None]]


def _make_image_or_text(base64_data: str, *, is_console: bool) -> Any:
    """OneBot 返回 MessageSegment.image；Console 返回纯文字占位。"""
    if is_console:
        return "[图片结果 - 请在 QQ 中查看]"
    return V11Seg.image(f"base64://{base64_data}")


# ====================== 核心命令路由（适配器无关） ======================
async def _dispatch(
    send: SendFunc,
    raw_text: str,
    user_id: int,
    message_obj: Any,
    *,
    is_console: bool = False,
    is_admin: bool = False,
    # 以下仅 OneBot V11 场景使用
    bot: V11Bot | None = None,
    event: GroupMessageEvent | None = None,
) -> None:
    """核心命令分发，不依赖具体适配器类型。"""

    # ---------- 可能是词条添加的回复 ----------
    if user_id in _add_db_qq_list:
        key = _add_db_qq_list.pop(user_id)
        if key == "太阳":
            await send("未知错误")
            return
        buf = json.dumps(str(message_obj))
        m = qun_db.get_string_map_string("data")
        m[key] = buf
        qun_db.set("data", m)
        qun_db.save()
        await send("编辑词条成功")
        return

    if not raw_text:
        return

    # 统计 TF-IDF
    add_into_dict(raw_text)

    # 解析命令
    parts = raw_text.split(" ", 1)
    cmd = parts[0]
    content = parts[1].strip() if len(parts) > 1 else ""

    # ---- 查看帮助 ----
    if cmd == "查看帮助":
        await send("你可以使用以下功能：\n" + "\n".join(sorted(_HELP_TIPS)))
        return

    # ---- ping ----
    if cmd == "ping" and not content:
        await send("pong")
        return

    # ---- roll ----
    if cmd == "roll":
        if not content:
            await send(f"roll: {random.randint(0, 99)}")
        else:
            try:
                upper = int(content)
                if upper > 0:
                    await send(f"roll: {random.randint(1, upper)}")
            except ValueError:
                pass
        return

    # ---- 8421 (药水表) ----
    if cmd == "8421" and not content:
        result = calculate_potion()
        if result:
            await send(_make_image_or_text(result, is_console=is_console))
        return

    # ---- 等级压制 ----
    if cmd == "等级压制" and content:
        result = calculate_exp_damage(content)
        if result:
            await send(result)
        return

    # ---- 生成表格 ----
    if cmd == "生成表格" and content:
        result = gen_table(content)
        if result:
            await send(_make_image_or_text(result, is_console=is_console))
        return

    # ---- 升级经验 ----
    if cmd == "升级经验":
        if not content:
            result = calculate_level_exp()
            if result:
                await send(_make_image_or_text(result, is_console=is_console))
        else:
            p = content.split(" ", 1)
            if len(p) == 2:
                try:
                    start, end = int(p[0]), int(p[1])
                    result = calculate_exp_between_level(start, end)
                    if result:
                        await send(result)
                except ValueError:
                    pass
        return

    # ---- 爆炸次数 ----
    if cmd == "爆炸次数":
        msgs = calculate_boom_count(content or "", new_kms=True)
        msgs += calculate_boom_count(content or "", new_kms=False)
        for msg in msgs:
            await send(msg)
        return

    # ---- 神秘压制 ----
    if cmd == "神秘压制" and not content:
        result = get_more_damage_arc()
        if result:
            await send(_make_image_or_text(result, is_console=is_console))
        return

    # ---- 模拟升星 / 模拟上星 / 升星期望 / 上星期望 ----
    for sf_cmd in ("模拟升星", "模拟上星", "升星期望", "上星期望"):
        if cmd in (sf_cmd, sf_cmd + "旧"):
            new_kms = not cmd.endswith("旧")
            if not content:
                await send("命令格式：\r\n模拟升星 200 0 22\r\n后面可以加：七折、减爆、保护")
            else:
                result = calculate_star_force(new_kms, content)
                for msg in result:
                    await send(msg)
            return

    # ---- 洗魔方 ----
    if cmd == "洗魔方":
        result = calculate_cube_all() if not content else calculate_cube(content)
        for msg in result:
            await send(msg)
        return

    # ---- 查询我 ----
    if cmd == "查询我" and not content:
        data = find_role_data.get_string_map_string("data")
        name = data.get(str(user_id), "")
        if not name:
            await send("你还未绑定")
        else:
            msgs = await find_role(name)
            for msg in msgs:
                await send(msg)
        return

    # ---- 查询 游戏名 ----
    if cmd == "查询" and content and " " not in content:
        msgs = await find_role(content)
        for msg in msgs:
            await send(msg)
        return

    # ---- 查询绑定 QQ号 ----
    if cmd == "查询绑定" and content:
        try:
            qq = int(content)
            data = find_role_data.get_string_map_string("data")
            name = data.get(str(qq), "")
            if name:
                await send(f"该玩家绑定了：{name}")
            else:
                await send("该玩家还未绑定")
        except ValueError:
            await send("命令格式：查询绑定 QQ号")
        return

    # ---- 绑定 ----
    if cmd == "绑定" and content and " " not in content:
        data = find_role_data.get_string_map_string("data")
        uid = str(user_id)
        if uid in data and data[uid]:
            await send("你已经绑定过了，如需更换请先解绑")
        else:
            data[uid] = content
            find_role_data.set("data", data)
            find_role_data.save()
            await send("绑定成功")
        return

    # ---- 解绑 ----
    if cmd == "解绑" and not content:
        data = find_role_data.get_string_map_string("data")
        uid = str(user_id)
        if uid in data and data[uid]:
            del data[uid]
            find_role_data.set("data", data)
            find_role_data.save()
            await send("解绑成功")
        else:
            await send("你还未绑定")
        return

    # ---- 我要开车 / 订阅开车 / 取消订阅 ----
    if cmd == "我要开车":
        if is_console:
            await send("（Console 调试模式不支持开车功能，需要 OneBot V11 环境）")
        elif bot and event:
            result = await handle_boss_party(bot, event, _BOSS_LIST, content)
            if result:
                await send(result)
        return
    if cmd == "订阅开车":
        result = handle_subscribe(_BOSS_LIST, content, user_id)
        if result:
            await send(result)
        return
    if cmd == "取消订阅":
        result = handle_unsubscribe(_BOSS_LIST, content, user_id)
        if result:
            await send(result)
        return

    # ---- 词条操作（搜索/添加/修改/删除）----
    if raw_text.startswith("查询词条 ") or raw_text.startswith("搜索词条 "):
        key = _deal_key(raw_text[5:])
        if key:
            await _deal_search_dict(send, key)
        return

    if is_admin:
        if raw_text.startswith("添加词条 "):
            key = _deal_key(raw_text[5:])
            if key:
                await _deal_add_dict(send, user_id, key)
            return
        if raw_text.startswith("修改词条 "):
            key = _deal_key(raw_text[5:])
            if key:
                await _deal_modify_dict(send, user_id, key)
            return
        if raw_text.startswith("删除词条 "):
            key = _deal_key(raw_text[5:])
            if key:
                await _deal_remove_dict(send, key)
            return

    # ---- 词条调用（模糊匹配）----
    m = qun_db.get_string_map_string("data")
    s = get_familiar_value(m, _deal_key(raw_text))
    if s:
        await send(s)


# ====================== OneBot V11 Handler ======================
@group_msg.handle()
async def handle_group(bot: V11Bot, event: GroupMessageEvent):
    if not _in_valid_group(event.group_id):
        return

    raw_text = event.get_plaintext().strip()
    user_id = event.user_id

    # 判断管理员权限
    from maplebot.utils.perm import is_admin as _is_admin_v11
    admin = await _is_admin_v11(bot, event.group_id, user_id)

    async def send(msg: Any) -> None:
        await bot.send(event, msg)

    await _dispatch(
        send, raw_text, user_id, event.get_message(),
        is_console=False, is_admin=admin,
        bot=bot, event=event,
    )


# ====================== Console Handler ======================
if _HAS_CONSOLE:
    @console_msg.handle()
    async def handle_console(bot: ConsoleBot, event: ConsoleMessageEvent):
        raw_text = event.get_plaintext().strip()
        user_id = 0  # Console 调试用户

        async def send(msg: Any) -> None:
            # Console 适配器：只能发纯文本
            text = msg if isinstance(msg, str) else str(msg)
            await bot.send(event, ConSeg.text(text))

        # Console 模式视为管理员，方便调试
        await _dispatch(
            send, raw_text, user_id, event.get_message(),
            is_console=True, is_admin=True,
        )


# ====================== 词条 CRUD ======================
async def _deal_add_dict(send: SendFunc, user_id: int, key: str):
    if "." in key:
        await send("词条名称中不能包含 . 符号")
        return
    if key == "太阳":
        await send("未知错误")
        return
    m = qun_db.get_string_map_string("data")
    if key in m:
        await send("词条已存在")
    else:
        await send("请输入要添加的内容")
        _add_db_qq_list[user_id] = key


async def _deal_modify_dict(send: SendFunc, user_id: int, key: str):
    m = qun_db.get_string_map_string("data")
    if key not in m:
        await send("词条不存在")
    else:
        await send("请输入要修改的内容")
        _add_db_qq_list[user_id] = key


async def _deal_remove_dict(send: SendFunc, key: str):
    if key == "太阳":
        await send("未知错误")
        return
    m = qun_db.get_string_map_string("data")
    if key not in m:
        await send("词条不存在")
        return
    del m[key]
    qun_db.set("data", m)
    qun_db.save()
    await send("删除词条成功")


async def _deal_search_dict(send: SendFunc, key: str):
    m = qun_db.get_string_map_string("data")
    res = sorted([k for k in m if key in k])
    if res:
        num = len(res)
        if num > 10:
            res = res[:10]
            res[9] += f"\n等{num}个词条"
        lines = [f"{i + 1}. {r}" for i, r in enumerate(res)]
        await send("搜索到以下词条：\n" + "\n".join(lines))
    else:
        await send(f"搜索不到词条({key})")
