#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg 工具模块

提供 FFmpeg 相关的工具函数：
- 获取 FFmpeg 可执行文件路径
- 检查 FFmpeg 是否可用
- 获取 FFmpeg 版本等
"""

import sys
import subprocess
from pathlib import Path

from .path_util import get_tools_dir, get_project_root


def get_default_ffmpeg_path() -> str:
    """
    获取默认的 FFmpeg 路径，优先使用项目内 FFmpeg

    检测顺序：
        1. 项目根目录的 tools/ffmpeg.exe (Windows) 或 tools/ffmpeg (Linux/Mac)
        2. 回退到系统 PATH 中的 ffmpeg

    Returns:
        str: FFmpeg 可执行文件路径
    """
    tools_dir = get_tools_dir()

    # 确定可执行文件名
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    project_ffmpeg = tools_dir / ffmpeg_exe

    if project_ffmpeg.exists():
        return str(project_ffmpeg)

    # 回退到系统 PATH
    return "ffmpeg"


def check_ffmpeg_available(ffmpeg_path: str = "ffmpeg") -> bool:
    """
    检查 FFmpeg 是否可用

    Args:
        ffmpeg_path: FFmpeg 可执行文件路径

    Returns:
        bool: 可用返回 True
    """
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            check=False,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_ffmpeg_version(ffmpeg_path: str = "ffmpeg") -> str:
    """
    获取 FFmpeg 版本信息

    Args:
        ffmpeg_path: FFmpeg 可执行文件路径

    Returns:
        str: 版本号字符串，如 "4.4.2"
    """
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        # 第一行格式: "ffmpeg version 4.4.2 Copyright ..."
        first_line = result.stdout.split('\n')[0]
        if "version" in first_line:
            version = first_line.split("version")[1].strip().split()[0]
            return version
    except Exception:
        pass
    return "unknown"
