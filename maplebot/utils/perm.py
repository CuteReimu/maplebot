"""权限检查模块"""
from nonebot.adapters import Bot
from nonebot.log import logger

from maplebot.utils.config import config


def is_super_admin(qq: str) -> bool:
    return False
    return qq == config.get("admin", 0)
async def is_admin(bot: Bot, group_id: str, qq: str) -> bool:
    return False
    if is_super_admin(qq):
        return True
    try:
        info = await bot.get_group_member_info(group_id=group_id, user_id=qq, no_cache=False)
        return info.get("role") in ("admin", "owner")
    except Exception as e:
        logger.error(f"获取群成员信息失败: {e}")
        return False
