"""
日志配置模块

提供统一的日志配置和获取日志记录器的功能
"""

import logging
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件名 (可选)
        log_dir: 日志目录 (默认 ~/.local/share/secondbrain/logs)
    """
    # 确定日志目录
    if log_dir is None:
        log_dir = os.path.expanduser("~/.local/share/secondbrain/logs")
    else:
        log_dir = os.path.expanduser(log_dir)

    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # 确定日志文件路径
    if log_file is None:
        log_file = os.path.join(log_dir, "secondbrain.log")

    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称 (通常使用 __name__)

    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)


# 初始化日志系统
def init_logging():
    """初始化日志系统（在模块导入时调用）"""
    # 检查是否已经配置过
    if not logging.getLogger().handlers:
        setup_logging()


# 自动初始化
init_logging()
