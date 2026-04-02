"""NoneBot2 主入口"""
import inspect
import logging
import os

import nonebot
from loguru import logger
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

_IS_PROD = os.getenv("ENVIRONMENT", "dev").lower() == "prod"

# 非 prod 模式下加载 ConsoleAdapter，方便本地调试
if not _IS_PROD:
    try:
        from nonebot.adapters.console import Adapter as ConsoleAdapter
        driver.register_adapter(ConsoleAdapter)  # type: ignore[arg-type]
    except ImportError:
        pass

# prod 环境：将所有日志（loguru + stdlib logging）输出到按天分割的文件
if _IS_PROD:
    _LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(_LOG_DIR, exist_ok=True)

    # 移除 loguru 默认的控制台 sink
    # 注意：nonebot 的 logger 与 loguru 的 logger 是同一个对象，只需操作一次
    logger.remove()

    # 添加按天滚动、保留 7 天的文件 sink
    _log_path = os.path.join(_LOG_DIR, "{time:YYYY-MM-DD}.log")
    _sink_cfg = {
        "rotation": "00:00",       # 每天 0 点切割
        "retention": "7 days",     # 保留最近 7 天
        "encoding": "utf-8",
        "enqueue": True,           # 异步写入，避免阻塞事件循环
        "backtrace": True,
        "diagnose": False,         # prod 下关闭变量诊断，防止敏感信息泄露
        "format": "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
    }
    logger.add(_log_path, **_sink_cfg)

    # 将标准库 logging 的输出拦截到 loguru，避免第三方库日志丢失
    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno  # type: ignore[assignment]
            frame, depth = inspect.currentframe(), 0
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back  # type: ignore[assignment]
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.DEBUG, force=True)

# 加载插件目录
nonebot.load_plugins("maplebot/plugins")

if __name__ == "__main__":
    nonebot.run()
