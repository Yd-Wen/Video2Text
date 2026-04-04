#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块

功能:
    - 通用工具函数集合
    - 文件验证、日志设置、格式转换等
    - 不依赖其他项目模块的独立功能

设计原则:
    - 函数式编程，无状态
    - 纯工具函数，不依赖项目特定逻辑
"""

import os
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


def validate_input_file(file_path: Path) -> bool:
    """
    验证输入文件是否有效

    检查项:
        - 文件存在
        - 是文件（不是目录）
        - 可读
        - 非空

    Args:
        file_path: 文件路径

    Returns:
        bool: 验证通过返回True
    """
    path = Path(file_path)

    if not path.exists():
        logging.debug(f"文件不存在: {path}")
        return False

    if not path.is_file():
        logging.debug(f"路径不是文件: {path}")
        return False

    if not os.access(path, os.R_OK):
        logging.debug(f"文件不可读: {path}")
        return False

    if path.stat().st_size == 0:
        logging.debug(f"文件为空: {path}")
        return False

    return True


def validate_output_dir(dir_path: Path) -> bool:
    """
    验证/创建输出目录

    检查项:
        - 目录存在或可以创建
        - 可写

    Args:
        dir_path: 目录路径

    Returns:
        bool: 验证通过返回True
    """
    path = Path(dir_path)

    try:
        # 尝试创建目录（包括父目录）
        path.mkdir(parents=True, exist_ok=True)

        # 检查是否可写
        if not os.access(path, os.W_OK):
            logging.debug(f"目录不可写: {path}")
            return False

        return True

    except Exception as e:
        logging.debug(f"无法创建或访问目录 {path}: {e}")
        return False


def get_file_size_human(size_bytes: int) -> str:
    """
    将字节数转换为人类可读格式

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 人类可读的大小（如 "1.5 MB"）
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """
    将秒数格式化为人类可读的时间

    Args:
        seconds: 时间（秒）

    Returns:
        str: 格式化后的时间（如 "1:23:45" 或 "12:34"）
    """
    if seconds < 0:
        return "0:00"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    清理文件名中的非法字符

    Windows非法字符: < > : " / \ | ? *
    Unix非法字符: /

    Args:
        filename: 原始文件名
        replacement: 替换字符，默认下划线

    Returns:
        str: 清理后的文件名
    """
    # Windows和Unix的非法字符
    illegal_chars = '<>:"|?*\\/'

    result = filename
    for char in illegal_chars:
        result = result.replace(char, replacement)

    # 移除控制字符
    result = "".join(c for c in result if ord(c) >= 32)

    # 限制长度
    if len(result) > 200:
        result = result[:200]

    # 去除首尾空白和点
    result = result.strip(" .")

    # 防止空文件名
    if not result:
        result = "unnamed"

    return result


def check_disk_space(path: Path, required_mb: int = 100) -> bool:
    """
    检查指定路径是否有足够的磁盘空间

    Args:
        path: 要检查的目录路径
        required_mb: 需要的空间（MB）

    Returns:
        bool: 空间充足返回True
    """
    try:
        stat = os.statvfs(path) if hasattr(os, 'statvfs') else None

        if stat:
            # Unix/Linux/Mac
            available_bytes = stat.f_frsize * stat.f_bavail
            available_mb = available_bytes / (1024 * 1024)
        else:
            # Windows - 使用shutil
            import shutil
            _, _, available_bytes = shutil.disk_usage(path)
            available_mb = available_bytes / (1024 * 1024)

        return available_mb >= required_mb

    except Exception as e:
        logging.debug(f"无法检查磁盘空间: {e}")
        # 无法检查时默认返回True，避免阻塞
        return True


def get_video_extensions() -> list[str]:
    """
    获取常见视频文件扩展名列表

    Returns:
        list: 小写扩展名列表（不含点）
    """
    return [
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm",
        "m4v", "mpg", "mpeg", "3gp", "ogv", "ts", "m2ts"
    ]


def is_video_file(file_path: Path) -> bool:
    """
    检查文件是否为视频文件（基于扩展名）

    Args:
        file_path: 文件路径

    Returns:
        bool: 是视频文件返回True
    """
    ext = Path(file_path).suffix.lower().lstrip(".")
    return ext in get_video_extensions()


def safe_remove(file_path: Path) -> bool:
    """
    安全删除文件（忽略错误）

    Args:
        file_path: 要删除的文件路径

    Returns:
        bool: 删除成功返回True
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        pass
    return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    根据数量返回单数或复数形式

    Args:
        count: 数量
        singular: 单数形式
        plural: 复数形式，None则在单数后加's'

    Returns:
        str: 适当的词形
    """
    if count == 1:
        return f"{count} {singular}"

    if plural is None:
        plural = f"{singular}s"

    return f"{count} {plural}"
