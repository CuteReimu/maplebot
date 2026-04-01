"""NoneBot2 主入口"""
import os
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 非 prod 模式下加载 ConsoleAdapter，方便本地调试
if os.getenv("ENVIRONMENT", "dev").lower() != "prod":
    try:
        from nonebot.adapters.console import Adapter as ConsoleAdapter  # noqa: PLC0415
        driver.register_adapter(ConsoleAdapter)  # type: ignore[arg-type]
    except ImportError:
        pass

# 加载插件目录
nonebot.load_plugins("maplebot/plugins")

if __name__ == "__main__":
    nonebot.run()
