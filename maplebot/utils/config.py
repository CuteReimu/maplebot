"""配置管理模块"""
import os

import yaml
from dynaconf import Dynaconf
from nonebot.log import logger

_CONFIG_DIR = os.path.join("config", "maplebot")
_DATA_DIR = os.path.join("data", "maplebot")

os.makedirs(_CONFIG_DIR, exist_ok=True)
os.makedirs(_DATA_DIR, exist_ok=True)

# ---------- 默认值 ----------
_CONFIG_DEFAULTS = {
    "admin": 12345678,
    "admin_groups": [12345678],
    "qq_groups": [12345678],
    "notify_groups": [12345678],
    "notify_qq": [12345678],
    "image_expire_hours": 24,
}

_CONFIG_FILE = os.path.join(_CONFIG_DIR, "Config.yml")
if not os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, "w", encoding="utf-8") as file:
        yaml.dump(_CONFIG_DEFAULTS, file, allow_unicode=True)
    logger.info("已生成默认配置文件: %s", _CONFIG_FILE)

config = Dynaconf(
    settings_files=[_CONFIG_FILE],
    envvar_prefix="MAPLEBOT",
)


# ---------- 数据文件辅助（QunDb / FindRoleData / LevelExpData / ClassImageData） ----------

def _ensure_yaml(path: str, defaults: dict | None = None) -> dict:
    """确保 YAML 文件存在并返回其内容"""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(defaults or {}, f, allow_unicode=True)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    os.replace(tmp, path)


class YamlStore:
    """简单的 YAML 文件读写封装"""

    def __init__(self, directory: str, name: str, defaults: dict | None = None):
        self.path = os.path.join(directory, f"{name}.yml")
        self._data = _ensure_yaml(self.path, defaults)

    def get(self, key: str, default=None):
        keys = key.split(".")
        d = self._data
        for k in keys:
            if isinstance(d, dict):
                val = d.get(k, None)
                if val is None:
                    # YAML 中纯数字 key 会被 safe_load 解析为 int，尝试整数 key
                    try:
                        val = d.get(int(k), None)
                    except (ValueError, TypeError):
                        pass
                d = val
            else:
                return default
        return d if d is not None else default

    def set(self, key: str, value) -> None:
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    def get_string_map_string(self, key: str) -> dict[str, str]:
        val = self.get(key, {})
        if not isinstance(val, dict):
            return {}
        return {str(k): str(v) for k, v in val.items()}

    def save(self) -> None:
        _save_yaml(self.path, self._data)

    def reload(self) -> None:
        self._data = _ensure_yaml(self.path)

    @property
    def data(self) -> dict:
        return self._data


# 各个数据存储实例
qun_db = YamlStore(_DATA_DIR, "QunDb")
find_role_data = YamlStore(_DATA_DIR, "FindRoleData")
level_exp_data = YamlStore(_DATA_DIR, "LevelExpData")
