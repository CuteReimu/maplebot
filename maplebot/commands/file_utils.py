"""玩家数据文件工具"""
import asyncio
import json
import os
import datetime

from nonebot.log import logger

NAME_FILE = "player_name.txt"
NEW_NAME_FILE = "player_name.json"
PLAYER_DICT_FN = "player_data/player_{}.json"

# 全局文件锁：保护所有文件读写操作
_file_lock = asyncio.Lock()

if not os.path.exists("./player_data"):
    os.makedirs("./player_data")
assert os.path.isdir("./player_data")

logger.info(f"Program started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def read_with_retry(path, encoding="utf-8", attempts=3, delay=0.05, default=""):
    for i in range(attempts):
        try:
            async with _file_lock:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
            logger.info(f"Successfully read {path}")
            return content
        except FileNotFoundError:
            if i < attempts - 1:
                await asyncio.sleep(delay)
            else:
                async with _file_lock:
                    with open(path, "w", encoding=encoding) as f:
                        f.write(default)  # Create an empty file
                logger.warning(f"File {path} not found. Created new file with default content.")
                return default
    return '{}'


async def load_player_names():
    if os.path.exists(NEW_NAME_FILE):
        content = await read_with_retry(NEW_NAME_FILE, encoding="utf-8", default="{}")
        names = json.loads(content)
        logger.info('Loaded player name from json')
        return names
    content = await read_with_retry(NAME_FILE, encoding="utf-8", default="")
    _names = [line.strip() for line in content.splitlines() if line.strip()]
    names = {name: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") for name in _names}
    await save_dict(NEW_NAME_FILE, names)
    logger.info('Loaded player name from txt and converted to json')
    return names


async def save_player_names(names):
    temp_name = f"{NEW_NAME_FILE}.tmp"
    async with _file_lock:
        with open(temp_name, "w", encoding="utf-8") as f:
            json.dump(names, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, NEW_NAME_FILE)
    logger.info(f'Saved file {NEW_NAME_FILE}')


async def remove_player_names(names_to_remove, updated_names):
    names = await load_player_names()
    for name in names_to_remove:
        if name in names:
            del names[name]
    names.update(updated_names)
    await save_player_names(names)
    logger.info(f'Removed {len(names_to_remove)} player names')


async def save_dict(fn, _dict):
    temp_name = f"{fn}.tmp"
    async with _file_lock:
        with open(temp_name, "w", encoding="utf8") as f:
            json.dump(_dict, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, fn)


async def load_dict(fn):
    content = await read_with_retry(fn, encoding="utf8", default=json.dumps({}))
    try:
        _dict = json.loads(content)
    except json.JSONDecodeError:
        _dict = {}
    return _dict


def same_dict(dict1, dict2):
    keys = ["exp", "level", "jobID", "legionLevel", "raidPower"]
    for key in keys:
        if dict1.get(key) != dict2.get(key):
            return False
    date1 = datetime.datetime.strptime(dict1.get("datetime"), "%Y-%m-%d %H:%M:%S")
    date2 = datetime.datetime.strptime(dict2.get("datetime"), "%Y-%m-%d %H:%M:%S")
    if abs((date1 - date2)) >= datetime.timedelta(hours=20):
        return False
    return True
