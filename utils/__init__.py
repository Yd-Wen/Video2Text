#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数包

将通用工具函数按功能分类：
- path_util: 路径相关
- file_util: 文件操作
- log_util: 日志配置
- format_util: 格式化
- text_util: 文本处理（T2N新增）
- video_util: 视频文件
- ffmpeg_util: FFmpeg相关

使用示例:
    from utils import setup_logging, validate_input_file
    from utils.path_util import get_project_root
    from utils.text_util import read_text_file, clean_text
"""

# 常用工具函数直接导出，方便使用
from .log_util import setup_logging
from .file_util import (
    validate_input_file,
    validate_output_dir,
    cleanup_temp_files,
    safe_remove,
    sanitize_filename,
    check_disk_space,
    get_file_size_human,
)
from .path_util import (
    get_project_root,
    get_models_dir,
)
from .ffmpeg_util import get_default_ffmpeg_path
from .format_util import (
    format_duration,
    truncate_text,
    pluralize,
)
from .video_util import (
    get_video_extensions,
    is_video_file,
)
from .text_util import (
    read_text_file,
    read_json_transcript,
    read_vocab_file,
    merge_vocab_files,
    clean_text,
    apply_vocab_correction,
    clean_and_correct_text,
    generate_output_filename,
    write_markdown,
    estimate_tokens,
    split_text_into_chunks,
)

__all__ = [
    # 日志
    'setup_logging',
    # 文件操作
    'validate_input_file',
    'validate_output_dir',
    'cleanup_temp_files',
    'safe_remove',
    'sanitize_filename',
    'check_disk_space',
    'get_file_size_human',
    # 路径
    'get_project_root',
    'get_models_dir',
    # FFmpeg
    'get_default_ffmpeg_path',
    # 格式化
    'format_duration',
    'truncate_text',
    'pluralize',
    # 视频
    'get_video_extensions',
    'is_video_file',
    # 文本处理（T2N）
    'read_text_file',
    'read_json_transcript',
    'read_vocab_file',
    'merge_vocab_files',
    'clean_text',
    'apply_vocab_correction',
    'clean_and_correct_text',
    'generate_output_filename',
    'write_markdown',
    # 文本分段（Phase 5）
    'estimate_tokens',
    'split_text_into_chunks',
]
