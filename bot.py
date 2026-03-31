"""NoneBot2 主入口"""
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载插件目录
nonebot.load_plugins("maplebot/plugins")

if __name__ == "__main__":
    nonebot.run()

