"""权限检查模块"""
from maplebot.utils.config import admin_data


def is_super_admin(qq: str) -> bool:
    return qq == admin_data.get("super_admin")


def is_admin(qq: str) -> bool:
    if is_super_admin(qq):
        return True
    return qq in admin_data.get("admin", [])


def try_init_super_admin(qq: str) -> None:
    if admin_data.get("super_admin"):
        return
    admin_data.set("super_admin", qq)
    admin_data.save()


def add_admin(qq: str) -> bool:
    admins: list[str] = admin_data.get("admin", [])
    if qq in admins:
        return False
    admins.append(qq)
    admin_data.set("admin", admins)
    admin_data.save()
    return True


def del_admin(qq: str) -> bool:
    admins: list[str] = admin_data.get("admin", [])
    if qq not in admins:
        return False
    admins.remove(qq)
    admin_data.set("admin", admins)
    admin_data.save()
    return True
