"""maplebot 主插件 - NoneBot2 命令路由"""
# pylint: disable=wrong-import-position
import os
import random
from typing import Any

from nonebot import on_command, on_message, require, get_bot
from nonebot.adapters import Event
from nonebot.adapters.qq import GroupMessageCreateEvent, C2CMessageCreateEvent
from nonebot.adapters.qq.message import Message, MessageSegment, LocalAttachment
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
from maplebot.commands.cube import calculate_cube, calculate_cube_all
from maplebot.commands.find_role import find_role
from maplebot.commands.scrape import scrape_role_background
from maplebot.commands.level_exp import (
    calculate_level_exp,
    calculate_exp_between_level,
    calculate_exp_damage,
)
from maplebot.commands.star_force import calculate_star_force, calculate_boom_count
from maplebot.commands.slide_puzzle import generate_slide_puzzle_gif
from maplebot.commands.bonus_att import calculate_bonus_att
from maplebot.commands.bonus_bd import calculate_bonus_bd
from maplebot.commands.bonus_idf import calculate_bonus_idf
from maplebot.commands.bonus_cd import calculate_bonus_cd
from maplebot.commands.calculator import calculate_arc_cost, calculate_sac_cost, calculate_hexa_cost
from maplebot.utils.config import config, qun_db, find_role_data
from maplebot.utils.dict_tfidf import get_familiar_value, add_into_dict
from maplebot.utils.dict_entry import serialize_message, build_message, cleanup_orphan_images, find_entries_with_missing_images

logger.opt(colors=True).info("<green>✅ maplebot_main 插件加载成功！</green>")

# ---------- 待添加词条队列 ----------
_add_db_qq_list: dict[str, str] = {}

_BOSS_LIST = list("4M36789绿黑赛狗卡波马猴")

_HELP_TIPS = [
    "查询 游戏名", "绑定 游戏名", "解绑",
    "洗魔方", "洗魔方 部位 [等级]",
    "模拟升星 200 0 22 [七折] [减爆] [保护]",
    "升级经验", "升级经验 起始级 目标级",
    "等级压制 等级差",
    "神秘压制",
    "爆炸次数",
    "滑块",
    "攻击收益 当前攻击% 新增攻击%",
    "BOSS伤害收益 当前伤害% 当前B伤% 新增伤害/B伤%",
    "无视收益 怪物防御% 当前无视% 新增无视%",
    "爆伤收益 当前爆伤% 新增爆伤%",
    "神秘/原初 初始等级 目标等级",
    "六转 技能/精通/强化/通用/通用五转 初始等级 目标等级",
]


def _deal_key(s: str) -> str:
    """处理词条 key：转小写"""
    return s.strip().lower()


# ====================== 通用工具 ======================

def _ensure_iterable(var):
    try:
        iter(var)
        return var
    except TypeError:
        return [var]


async def _send_many_pics_msg(old_message, reply_message):
    reply_msg = Message()
    has_pic = False
    for msg in _ensure_iterable(reply_message):
        if isinstance(msg, LocalAttachment):
            if has_pic:
                await old_message.send(reply_msg)
                reply_msg = Message()
            has_pic = not has_pic
        reply_msg += msg
    await old_message.finish(reply_msg if len(reply_msg) > 0 else None)


def _is_console(event: Event) -> bool:
    return _HAS_CONSOLE and ConsoleMessageEvent is not None and isinstance(event, ConsoleMessageEvent)


def _make_image_or_text(s: bytes, event: Event) -> Any:
    """OneBot 返回 MessageSegment.file_image；Console 返回纯文字占位。"""
    if _is_console(event):
        return "[图片]"
    return MessageSegment.file_image(s)


# 目前没有什么好办法获得角色在群里的身份，先只允许私聊进行管理，然后只允许管理加好友
def _is_admin(event: Event) -> bool:
    if _is_console(event):
        return True
    return isinstance(event, C2CMessageCreateEvent)


# ====================== TF-IDF 追踪（最高优先级，不阻塞） ======================
_tfidf_tracker = on_message(priority=1, block=False)


@_tfidf_tracker.handle()
async def _handle_tfidf(event: Event):
    if not isinstance(event, GroupMessageCreateEvent):
        return
    raw_text = event.get_plaintext().strip()
    if raw_text:
        add_into_dict(raw_text)


# ====================== 词条添加回调（高优先级，匹配时阻塞） ======================
_dict_callback = on_message(priority=5, block=False)


@_dict_callback.handle()
async def _handle_dict_callback(event: Event):
    if not isinstance(event, GroupMessageCreateEvent):
        return
    user_id = event.get_user_id()
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
_help_cmd = on_command("查看帮助", force_whitespace=True, priority=10, block=True)


@_help_cmd.handle()
async def _handle_help():
    await _help_cmd.finish("你可以使用以下功能：\n" + "\n".join(sorted(_HELP_TIPS)))


# ---- 艾特机器人（无其他内容）触发帮助 ----
async def _check_at_bot_only(event: Event) -> bool:
    """Rule：@机器人且无其他有效内容（NoneBot2 已将 @bot 段剥离，直接检查剩余消息）"""
    if not isinstance(event, GroupMessageCreateEvent):
        return False
    if not event.to_me:
        return False
    for seg in event.get_message():
        if seg.type == "text":
            if seg.data.get("text", "").strip():
                return False  # 含非空文字
        else:
            return False  # 图片/表情等其他段
    return True


_at_bot_cmd = on_message(rule=Rule(_check_at_bot_only), priority=10, block=True)


@_at_bot_cmd.handle()
async def _handle_at_bot():
    await _at_bot_cmd.finish("你可以使用以下功能：\n" + "\n".join(sorted(_HELP_TIPS)))


# ---- ping ----
_ping_cmd = on_command("ping", force_whitespace=True, priority=10, block=True)


@_ping_cmd.handle()
async def _handle_ping(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        await _ping_cmd.finish("pong")


# ---- roll ----
_roll_cmd = on_command("roll", force_whitespace=True, priority=10, block=True)


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
_exp_damage_cmd = on_command("等级压制", force_whitespace=True, priority=10, block=True)


@_exp_damage_cmd.handle()
async def _handle_exp_damage(args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        result = calculate_exp_damage(content)
        if result:
            await _exp_damage_cmd.finish(result)
    else:
        await _exp_damage_cmd.finish("命令格式：\n等级压制 等级差")


# ---- 升级经验 ----
_level_exp_cmd = on_command("升级经验", force_whitespace=True, priority=10, block=True)


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
_boom_cmd = on_command("爆炸次数", force_whitespace=True, priority=10, block=True)


@_boom_cmd.handle()
async def _handle_boom(args=CommandArg()):
    content = args.extract_plain_text().strip()
    msg = calculate_boom_count(content or "", new_kms=True)
    if msg:
        await _boom_cmd.finish(msg)


# ---- 滑块（数字华容道动图） ----
_slide_puzzle_cmd = on_command("滑块", force_whitespace=True, priority=10, block=True)


@_slide_puzzle_cmd.handle()
async def _handle_slide_puzzle(event: Event):
    try:
        img = generate_slide_puzzle_gif()
        await _slide_puzzle_cmd.finish(_make_image_or_text(img, event))
    except Exception as e:
        logger.error(f"[slide_puzzle] 生成失败: {e}")
        await _slide_puzzle_cmd.finish()


# ---- 攻击收益 ----
_bonus_att_cmd = on_command("攻击收益", force_whitespace=True, priority=10, block=True)


@_bonus_att_cmd.handle()
async def _handle_bonus_att(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_bonus_att(content)
    if _is_console(event) and not isinstance(result, str):
        await _bonus_att_cmd.finish(result.extract_plain_text())
    else:
        await _bonus_att_cmd.finish(result)


# ---- BOSS伤害收益 ----
_bonus_bd_cmd = on_command("BOSS伤害收益", aliases={"B伤收益", "boss伤害收益", "Boss伤害收益", "b伤收益", "BD收益", "bd收益"}, force_whitespace=True, priority=10, block=True)


@_bonus_bd_cmd.handle()
async def _handle_bonus_bd(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_bonus_bd(content)
    if _is_console(event) and not isinstance(result, str):
        await _bonus_bd_cmd.finish(result.extract_plain_text())
    else:
        await _bonus_bd_cmd.finish(result)


# ---- 无视收益 ----
_bonus_idf_cmd = on_command("无视收益", force_whitespace=True, priority=10, block=True)


@_bonus_idf_cmd.handle()
async def _handle_bonus_idf(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_bonus_idf(content)
    if _is_console(event) and not isinstance(result, str):
        await _bonus_idf_cmd.finish(result.extract_plain_text())
    else:
        await _bonus_idf_cmd.finish(result)


# ---- 爆伤收益 ----
_bonus_cd_cmd = on_command("爆伤收益", aliases={"暴伤收益"}, force_whitespace=True, priority=10, block=True)


@_bonus_cd_cmd.handle()
async def _handle_bonus_cd(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_bonus_cd(content)
    if _is_console(event) and not isinstance(result, str):
        await _bonus_cd_cmd.finish(result.extract_plain_text())
    else:
        await _bonus_cd_cmd.finish(result)


# ---- 神秘压制 ----
_arc_cmd = on_command("神秘压制", force_whitespace=True, priority=10, block=True)


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
    force_whitespace=True,
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
        await _star_force_cmd.finish(result)


# ---- 洗魔方 ----
_cube_cmd = on_command("洗魔方", force_whitespace=True, priority=10, block=True)


@_cube_cmd.handle()
async def _handle_cube(args=CommandArg()):
    content = args.extract_plain_text().strip()
    result = calculate_cube_all() if not content else calculate_cube(content)
    await _cube_cmd.finish(result)


# ---- 查询我 ----
_query_me_cmd = on_command("查询我", force_whitespace=True, priority=10, block=True)


@_query_me_cmd.handle()
async def _handle_query_me(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        user_id = event.get_user_id()
        data = find_role_data.get_string_map_string("data")
        name = data.get(str(user_id), "")
        if not name:
            await _query_me_cmd.finish("你还未绑定")
        else:
            result = await find_role(name)
            if _is_console(event) and not isinstance(result, str):
                await _query_me_cmd.finish(result.extract_plain_text())
            else:
                await _send_many_pics_msg(_query_me_cmd, result)


# ---- 查询绑定 QQ号 ----
_query_bind_cmd = on_command("查询绑定", force_whitespace=True, priority=10, block=True)


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
    "查询词条", aliases={"搜索词条"}, force_whitespace=True, priority=10, block=True,
)


@_search_dict_cmd.handle()
async def _handle_search_dict(args=CommandArg()):
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        await _deal_search_dict(_search_dict_cmd, key)


# ---- 查询 游戏名 ----
# force_whitespace 不能用于此命令：需要同时支持 "查询 @某人"（有空格）和 "查询@某人"（无空格，at段紧跟命令）
_query_cmd = on_command("查询", priority=10, block=True)


@_query_cmd.handle()
async def _handle_query(event: Event, args=CommandArg()):
    # 处理 "查询@某人" 或 "查询 @某人"（带/不带空格均支持）
    at_segs = [seg for seg in args if seg.type == "at"]
    if at_segs:
        target_qq = str(at_segs[0].data.get("qq", ""))
        if target_qq:
            data = find_role_data.get_string_map_string("data")
            name = data.get(target_qq, "")
            if not name:
                await _query_cmd.finish("该玩家还未绑定")
            else:
                result = await find_role(name)
                if _is_console(event) and not isinstance(result, str):
                    await _query_cmd.finish(result.extract_plain_text())
                else:
                    await _send_many_pics_msg(_query_cmd, result)
            return

    content = args.extract_plain_text().strip()
    if content and " " not in content:
        result = await find_role(content)
        if _is_console(event) and not isinstance(result, str):
            await _query_cmd.finish(result.extract_plain_text())
        else:
            await _send_many_pics_msg(_query_cmd, result)


# ---- 绑定 ----
_bind_cmd = on_command("绑定", force_whitespace=True, priority=10, block=True)


@_bind_cmd.handle()
async def _handle_bind(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content and " " not in content:
        user_id = event.get_user_id()
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
_unbind_cmd = on_command("解绑", force_whitespace=True, priority=10, block=True)


@_unbind_cmd.handle()
async def _handle_unbind(event: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if not content:
        user_id = event.get_user_id()
        data = find_role_data.get_string_map_string("data")
        uid = str(user_id)
        if uid in data and data[uid]:
            del data[uid]
            find_role_data.set("data", data)
            find_role_data.save()
            await _unbind_cmd.finish("解绑成功")
        else:
            await _unbind_cmd.finish("你还未绑定")


# ---- 添加词条（管理员） ----
_add_dict_cmd = on_command("添加词条", force_whitespace=True, priority=10, block=True)


@_add_dict_cmd.handle()
async def _handle_add_dict(event: Event, args=CommandArg()):
    if not _is_admin(event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        user_id = event.get_user_id()
        await _deal_add_dict(_add_dict_cmd, user_id, key)


# ---- 修改词条（管理员） ----
_modify_dict_cmd = on_command("修改词条", force_whitespace=True, priority=10, block=True)


@_modify_dict_cmd.handle()
async def _handle_modify_dict(event: Event, args=CommandArg()):
    if not _is_admin(event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        user_id = event.get_user_id()
        await _deal_modify_dict(_modify_dict_cmd, user_id, key)


# ---- 删除词条（管理员） ----
_delete_dict_cmd = on_command("删除词条", force_whitespace=True, priority=10, block=True)


@_delete_dict_cmd.handle()
async def _handle_delete_dict(event: Event, args=CommandArg()):
    if not _is_admin(event):
        return
    content = args.extract_plain_text().strip()
    key = _deal_key(content)
    if key:
        await _deal_remove_dict(_delete_dict_cmd, key)


# ---- 列出过期图片（管理员）：找出本地图片文件已丢失的词条 ----
_missing_img_cmd = on_command("列出过期图片", force_whitespace=True, priority=10, block=True)


@_missing_img_cmd.handle()
async def _handle_missing_img(event: Event):
    if not _is_admin(event):
        return
    m = qun_db.get_string_map_string("data")
    missing = find_entries_with_missing_images(m)
    if not missing:
        await _missing_img_cmd.finish("所有词条的图片均正常，未发现缺失文件。")
        return
    total = len(missing)
    display = missing[:50]
    lines = [f"{i + 1}. {k}" for i, k in enumerate(display)]
    header = f"以下 {total} 个词条存在图片文件缺失：\n"
    suffix = f"\n（仅显示前 50 条，共 {total} 条）" if total > 50 else ""
    await _missing_img_cmd.finish(header + "\n".join(lines) + suffix)


# ---- 计算神秘/原初/六转升级成本   ----
_arc_calculate_cmd = on_command("神秘", force_whitespace=True, priority=10, block=True)


@_arc_calculate_cmd.handle()
async def _handle_arc_calculate(_: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        try:
            start, end = content.split()
            start, end = int(start), int(end)
            result = calculate_arc_cost(start, end)
            await _arc_calculate_cmd.finish(result)
            return
        except (ValueError, IndexError):
            pass
    await _arc_calculate_cmd.finish("命令格式：\n神秘 初始等级 目标等级， 等级1~20")

_sac_calculate_cmd = on_command("原初", force_whitespace=True, priority=10, block=True)


@_sac_calculate_cmd.handle()
async def _handle_sac_calculate(_: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        try:
            start, end = content.split()
            start, end = int(start), int(end)
            result = calculate_sac_cost(start, end)
            await _sac_calculate_cmd.finish(result)
            return
        except (ValueError, IndexError):
            pass
    await _sac_calculate_cmd.finish("命令格式：\n原初 初始等级 目标等级， 等级1~11")

_hexa_calculate_cmd = on_command("六转", force_whitespace=True, priority=10, block=True)


@_hexa_calculate_cmd.handle()
async def _handle_hexa_calculate(_: Event, args=CommandArg()):
    content = args.extract_plain_text().strip()
    if content:
        try:
            hexa_type, start, end = content.split()
            start, end = int(start), int(end)
            result = calculate_hexa_cost(hexa_type, start, end)
            await _hexa_calculate_cmd.finish(result)
            return
        except (ValueError, IndexError) as _:
            pass
    await _hexa_calculate_cmd.finish("命令格式：\n六转 技能/精通/强化/通用/通用五转 初始等级 目标等级， 等级0~30")

# ====================== 词条模糊匹配（最低优先级） ======================
_dict_fallback = on_message(priority=20, block=False)


@_dict_fallback.handle()
async def _handle_dict_fallback(event: Event):
    if not isinstance(event, GroupMessageCreateEvent):
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
        await _send_many_pics_msg(_dict_fallback, msg)


# ====================== 词条 CRUD ======================
async def _deal_add_dict(matcher, user_id: str, key: str):
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


async def _deal_modify_dict(matcher, user_id: str, key: str):
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
async def _notify_scrape_failure():
    return False
    """抓取失败时向配置的群发送告警并艾特管理员"""
    try:
        bot = get_bot()
    except Exception:
        logger.warning("[cron] 无法获取 bot 实例，跳过告警通知")
        return
    if not isinstance(bot, V11Bot):
        return
    notify_groups = config.get("notify_groups", [])
    notify_qq = config.get("notify_qq", [])
    msg = V11Message(V11Seg.text("角色数据预抓取失败"))
    for qq in notify_qq:
        msg += V11Seg.at(str(qq))
    for group in notify_groups:
        try:
            await bot.send_group_msg(group_id=int(group), message=msg)
        except Exception as ex:
            logger.warning(f"[cron] 发送告警通知失败 (group={group}): {ex}")


async def _cron_find_role():
    logger.info("[cron] 开始角色数据预抓取")
    try:
        await scrape_role_background()
        logger.info("[cron] 完成角色数据预抓取")
    except Exception as e:
        logger.error(f"[cron] 角色数据预抓取失败: {e}")
        await _notify_scrape_failure()


async def _cron_cleanup_images():
    """定时清理孤立词条图片"""
    logger.info("[cron] 开始清理孤立词条图片")
    try:
        m = qun_db.get_string_map_string("data")
        moved, deleted = cleanup_orphan_images(m)
        logger.info(f"[cron] 图片清理完成：移入暂存 {moved} 张，删除过期 {deleted} 张")
    except Exception as e:
        logger.error(f"[cron] 词条图片清理失败: {e}")


if os.getenv("ENVIRONMENT", "dev").lower() == "prod":
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

scheduler.add_job(
    _cron_cleanup_images,
    "cron",
    hour=4,
    minute=0,
    second=0,
    id="cleanup_orphan_images",
    timezone="Asia/Shanghai",
)
