"""Boss 开车订阅"""
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger

from maplebot.utils import db


def _get_boss_chars(boss_list: list[str], input_str: str) -> list[str]:
    """从输入中提取有效的 boss 字符"""
    input_upper = input_str.upper()
    result: list[str] = []
    for ch in input_upper:
        if ch in boss_list and ch not in result:
            result.append(ch)
    return result


def _subscribe(arr: list[str], user_id: str) -> None:
    """订阅指定 boss"""
    for ch in arr:
        key = f"boss_subscribe_{ch}"
        subscribed, _ = db.get(key)
        sub_list = [s for s in subscribed.split(",") if s] if subscribed else []
        if user_id in sub_list:
            continue
        sub_list.append(user_id)
        if len(sub_list) > 50:
            sub_list = sub_list[:50]
        db.set_value(key, ",".join(sub_list))


def _unsubscribe(arr: list[str], user_id: str) -> None:
    """取消订阅指定 boss"""
    for ch in arr:
        key = f"boss_subscribe_{ch}"
        subscribed, _ = db.get(key)
        sub_list = [s for s in subscribed.split(",") if s] if subscribed else []
        if user_id in sub_list:
            sub_list.remove(user_id)
            db.set_value(key, ",".join(sub_list))


async def handle_boss_party(
    bot: Bot,
    event: GroupMessageEvent,
    boss_list: list[str],
    content: str,
) -> Message | None:
    """处理 '我要开车' 命令"""
    arr = _get_boss_chars(boss_list, content)
    if not arr:
        return Message("不准开车!")

    # 收集订阅者
    qq_numbers: set[str] = set()
    for ch in arr:
        subscribed, _ = db.get(f"boss_subscribe_{ch}")
        if subscribed:
            for qq in subscribed.split(","):
                if qq:
                    qq_numbers.add(qq)

    # 排除自己
    qq_numbers.discard(str(event.user_id))

    # 获取群成员列表以过滤不在群内的人
    try:
        members = await bot.get_group_member_list(group_id=event.group_id)
        member_ids = {str(m["user_id"]) for m in members}
        qq_numbers = qq_numbers & member_ids
    except Exception as e:
        logger.error(f"获取群成员列表失败: {e}")

    msg = Message(MessageSegment.text(f"{''.join(arr)} 发车了! "))
    for qq in list(qq_numbers)[:20]:
        msg += MessageSegment.at(int(qq))

    return msg


def handle_subscribe(
    boss_list: list[str],
    content: str,
    user_id: int,
) -> str | None:
    """处理 '订阅开车' 命令"""
    arr = _get_boss_chars(boss_list, content)
    if not arr:
        return "这是去幼儿园的车"
    _subscribe(arr, str(user_id))
    return f"订阅成功 {''.join(arr)}"


def handle_unsubscribe(
    boss_list: list[str],
    content: str,
    user_id: int,
) -> str | None:
    """处理 '取消订阅' 命令"""
    uid = str(user_id)
    if not content:
        _unsubscribe(boss_list, uid)
        return "取消全部订阅成功"
    arr = _get_boss_chars(boss_list, content)
    _unsubscribe(arr, uid)
    return f"取消订阅成功 {''.join(arr)}"
