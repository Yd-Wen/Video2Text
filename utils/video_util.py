#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频工具模块

提供视频文件相关的工具函数：
- 视频扩展名列表
- 视频文件检测等
"""

from pathlib import Path


def get_video_extensions() -> list[str]:
    """
    获取常见视频文件扩展名列表

    Returns:
        list: 小写扩展名列表（不含点）
    """
    return [
        # 常见格式
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm",
        # Apple 格式
        "m4v", "m4p", "m4b",
        # MPEG 格式
        "mpg", "mpeg", "mp2", "mpe", "mpv",
        "m2v", "ts", "m2ts", "mts",
        # 移动设备格式
        "3gp", "3g2",
        # 其他格式
        "ogv", "ogg", "ogm",
        "vob", "dv",
        "nut", "nsv",
        "f4v", "f4p", "f4a", "f4b",
        "divx", "xvid",
        "rm", "rmvb",
        "asf", "wm",
        "qt", "yuv",
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


def get_video_info_fallback(file_path: Path) -> dict:
    """
    获取视频基本信息（基于文件扩展名，不依赖FFmpeg）

    Args:
        file_path: 视频文件路径

    Returns:
        dict: 包含扩展名、格式等基本信息
    """
    path = Path(file_path)

    return {
        "filename": path.name,
        "stem": path.stem,
        "suffix": path.suffix,
        "extension": path.suffix.lower().lstrip("."),
        "is_video": is_video_file(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
