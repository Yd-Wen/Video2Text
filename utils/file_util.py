#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件工具模块

提供文件操作相关的工具函数：
- 文件验证
- 目录验证
- 文件清理
- 文件名处理等
"""

import os
import logging
from pathlib import Path
from typing import Optional

from .path_util import get_temp_dir

logger = logging.getLogger(__name__)


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
        logger.debug(f"文件不存在: {path}")
        return False

    if not path.is_file():
        logger.debug(f"路径不是文件: {path}")
        return False

    if not os.access(path, os.R_OK):
        logger.debug(f"文件不可读: {path}")
        return False

    if path.stat().st_size == 0:
        logger.debug(f"文件为空: {path}")
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
            logger.debug(f"目录不可写: {path}")
            return False

        return True

    except Exception as e:
        logger.debug(f"无法创建或访问目录 {path}: {e}")
        return False


def cleanup_temp_files(pattern: str = "v2t_audio_*.wav") -> int:
    """
    清理项目临时目录中的残留文件

    在程序启动时调用，清理上次运行残留的临时音频文件。
    避免因程序异常退出导致的临时文件堆积。

    Args:
        pattern: 文件匹配模式，默认清理音频临时文件

    Returns:
        int: 删除的文件数量
    """
    temp_dir = get_temp_dir()
    count = 0

    if temp_dir.exists():
        for f in temp_dir.glob(pattern):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass  # 静默忽略删除失败

    if count > 0:
        logger.debug(f"清理了 {count} 个临时文件")

    return count


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
        logger.debug(f"无法检查磁盘空间: {e}")
        # 无法检查时默认返回True，避免阻塞
        return True


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


def get_unique_filename(dir_path: Path, filename: str) -> Path:
    """
    获取唯一的文件名（如果已存在则添加序号）

    Args:
        dir_path: 目录路径
        filename: 原始文件名

    Returns:
        Path: 唯一的文件路径
    """
    target = dir_path / filename
    if not target.exists():
        return target

    # 分离文件名和扩展名
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while True:
        new_filename = f"{stem}_{counter}{suffix}"
        new_target = dir_path / new_filename
        if not new_target.exists():
            return new_target
        counter += 1
