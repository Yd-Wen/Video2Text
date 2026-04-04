#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式化工具模块

提供各种格式化相关的工具函数：
- 时间格式化
- 文件大小格式化
- 文本截断等
"""

from typing import Optional


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


def format_duration_chinese(seconds: float) -> str:
    """
    将秒数格式化为中文时间格式

    Args:
        seconds: 时间（秒）

    Returns:
        str: 格式化后的时间（如 "1小时23分45秒"）
    """
    if seconds < 0:
        return "0秒"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")

    return "".join(parts)


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


def format_number(num: float, decimal_places: int = 2) -> str:
    """
    格式化数字（千分位分隔）

    Args:
        num: 数字
        decimal_places: 小数位数

    Returns:
        str: 格式化后的数字字符串
    """
    return f"{num:,.{decimal_places}f}"
