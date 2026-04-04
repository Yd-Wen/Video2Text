#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径工具模块

提供项目路径相关的工具函数：
- 获取项目根目录
- 获取模型存放目录
- 获取临时目录等
"""

from pathlib import Path


def get_project_root() -> Path:
    """
    获取项目根目录

    Returns:
        Path: 项目根目录路径（即包含此文件的父目录的父目录）
    """
    return Path(__file__).parent.parent


def get_models_dir() -> Path:
    """
    获取模型存放目录

    模型存放在项目根目录的 models/ 文件夹下，
    如果不存在会自动创建。

    Returns:
        Path: 模型目录路径
    """
    models_dir = get_project_root() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_temp_dir() -> Path:
    """
    获取临时文件目录

    Returns:
        Path: 临时目录路径
    """
    temp_dir = get_project_root() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_tools_dir() -> Path:
    """
    获取工具目录（存放FFmpeg等）

    Returns:
        Path: 工具目录路径
    """
    tools_dir = get_project_root() / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    return tools_dir


def get_output_dir() -> Path:
    """
    获取默认输出目录

    Returns:
        Path: 输出目录路径
    """
    output_dir = get_project_root() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
