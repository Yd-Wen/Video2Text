#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块

提供日志配置相关的工具函数：
- 设置日志级别和格式
- 支持文件输出
- 第三方库日志级别控制等
"""

import sys
import logging
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[Path] = None
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别，默认INFO
        format_string: 自定义格式字符串，None使用默认格式
        log_file: 日志文件路径，None表示只输出到控制台

    默认格式:
        控制台: "%(message)s"（简洁）
        DEBUG级别: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    """
    # 确定格式
    if format_string is None:
        if level == logging.DEBUG:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            format_string = "%(message)s"

    # 配置处理器
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=True  # 覆盖已有配置
    )

    # 设置第三方库的日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("ffmpeg").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取配置好的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)


def set_silent_mode() -> None:
    """
    设置静默模式（只显示错误）

    用于批量处理时减少输出
    """
    setup_logging(level=logging.ERROR)
