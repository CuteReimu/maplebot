"""KV 数据库"""
import logging
import os
import shelve
import threading

logger = logging.getLogger("maplebot.db")

_DB_DIR = os.path.join("assets", "database")
os.makedirs(_DB_DIR, exist_ok=True)
_DB_PATH = os.path.join(_DB_DIR, "maplebot")
_lock = threading.Lock()


def get(key: str) -> tuple[str, bool]:
    """根据 Key 获取 Value，返回 (value, ok)"""
    with _lock:
        try:
            with shelve.open(_DB_PATH) as db:
                if key in db:
                    return db[key], True
                return "", False
        except Exception as e:
            logger.error("get failed: key=%s, error=%s", key, e)
            return "", False


def set_value(key: str, value: str) -> None:
    """设置键值对"""
    with _lock:
        try:
            with shelve.open(_DB_PATH) as db:
                db[key] = value
        except Exception as e:
            logger.error("set failed: key=%s, error=%s", key, e)


def delete(key: str) -> None:
    """删除 Key"""
    with _lock:
        try:
            with shelve.open(_DB_PATH) as db:
                if key in db:
                    del db[key]
        except Exception as e:
            logger.error("delete failed: key=%s, error=%s", key, e)
