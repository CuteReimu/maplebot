"""权限检查模块"""
import logging

from nonebot.adapters.onebot.v11 import Bot

from maplebot.utils.config import config

logger = logging.getLogger("maplebot.perm")
def is_super_admin(qq: int) -> bool:
    return qq == config.get("admin", 0)
async def is_admin(bot: Bot, group_id: int, qq: int) -> bool:
    if is_super_admin(qq):
        return True
    try:
        info = await bot.get_group_member_info(group_id=group_id, user_id=qq, no_cache=False)
        return info.get("role") in ("admin", "owner")
    except Exception as e:
        logger.error("获取群成员信息失败: %s", e)
        return False
