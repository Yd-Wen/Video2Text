#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理工具模块

提供文本读取、预处理、编码检测等相关工具函数：
- 文本文件读取（支持编码自动检测）
- JSON转录文件读取
- 文本清洗（去除时间戳、合并断行等）
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


# =============================================================================
# 文本读取与编码检测
# =============================================================================

def read_text_file(file_path: Path) -> str:
    """
    【功能】读取文本文件，支持编码自动检测

    【参数】
        file_path: 文件路径

    【返回】
        str: 文件内容

    【异常】
        UnicodeDecodeError: 编码检测失败
        IOError: 文件读取失败
    """
    # 【编码尝试顺序】UTF-8优先，其次是GBK，最后是Latin-1容错
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # 所有编码都失败
    raise UnicodeDecodeError(f"无法识别文件编码: {file_path}")


def read_json_transcript(file_path: Path) -> str:
    """
    【功能】读取JSON格式的转录结果，提取文本内容

    【参数】
        file_path: JSON文件路径

    【返回】
        str: 合并后的文本内容
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理Whisper输出的JSON格式
    if isinstance(data, dict):
        # 如果有text字段直接返回
        if 'text' in data:
            return data['text']

        # 如果有segments字段，合并所有segment的text
        if 'segments' in data and isinstance(data['segments'], list):
            texts = []
            for seg in data['segments']:
                if isinstance(seg, dict) and 'text' in seg:
                    texts.append(seg['text'])
            return ' '.join(texts)

    # 如果是列表格式（segments数组）
    if isinstance(data, list):
        texts = []
        for seg in data:
            if isinstance(seg, dict) and 'text' in seg:
                texts.append(seg['text'])
        return ' '.join(texts)

    # 默认返回空字符串
    return ""


def read_vocab_file(file_path: Path) -> Dict[str, str]:
    """
    【功能】读取词汇表JSON文件

    【参数】
        file_path: JSON文件路径

    【返回】
        Dict[str, str]: 词汇表映射（错误词 -> 正确词）

    【示例】
        vocab.json: {"Sai AI": "CLI", "Giu AI": "GUI"}
        返回: {"Sai AI": "CLI", "Giu AI": "GUI"}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 确保返回的是 Dict[str, str]
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        else:
            logger.warning(f"词汇表文件格式错误: {file_path}，应为JSON对象")
            return {}

    except json.JSONDecodeError as e:
        logger.error(f"词汇表JSON解析失败: {file_path} - {e}")
        return {}
    except Exception as e:
        logger.error(f"读取词汇表失败: {file_path} - {e}")
        return {}


def merge_vocab_files(file_paths: List[Path]) -> Dict[str, str]:
    """
    【功能】合并多个词汇表文件

    后加载的词汇表会覆盖先加载的相同键值

    【参数】
        file_paths: 词汇表文件路径列表

    【返回】
        Dict[str, str]: 合并后的词汇表
    """
    merged = {}

    for path in file_paths:
        vocab = read_vocab_file(path)
        merged.update(vocab)
        logger.debug(f"加载词汇表: {path.name}，包含 {len(vocab)} 个词条")

    logger.info(f"词汇表合并完成，共 {len(merged)} 个词条")
    return merged


# =============================================================================
# 文本预处理
# =============================================================================

def clean_text(text: str) -> str:
    """
    【功能】基础文本清洗

    【处理内容】
        1. 去除时间戳 [00:12:34] 或 <00:12:34>
        2. 合并断行（去除行内换行符）
        3. 去除多余空行
        4. 去除说话人标识 "Speaker: "

    【参数】
        text: 原始文本

    【返回】
        str: 清洗后的文本
    """
    # 去除时间戳 [00:00:00.000] 或 <00:00:00>
    text = re.sub(r'\[?\d{1,2}:\d{2}:\d{2}(\.\d{3})?\]?', '', text)
    text = re.sub(r'<\d{1,2}:\d{2}:\d{2}(\.\d{3})?>', '', text)

    # 去除说话人标识（行首的 "Speaker: " 或 "Speaker："）
    text = re.sub(r'^[^：:\n]{1,20}[：:]\s*', '', text, flags=re.MULTILINE)

    # 合并行内换行符（保留段落间的空行）
    lines = text.split('\n')
    cleaned_lines = []
    current_paragraph = []

    for line in lines:
        stripped = line.strip()
        if stripped:
            current_paragraph.append(stripped)
        else:
            # 遇到空行，结束当前段落
            if current_paragraph:
                cleaned_lines.append(' '.join(current_paragraph))
                current_paragraph = []

    # 处理最后一个段落
    if current_paragraph:
        cleaned_lines.append(' '.join(current_paragraph))

    # 用双换行符连接段落
    text = '\n\n'.join(cleaned_lines)

    # 去除多余空行（3个以上连续换行符转为2个）
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 去除首尾空白
    text = text.strip()

    return text


def apply_vocab_correction(text: str, vocab: Dict[str, str]) -> str:
    """
    【功能】应用词汇表纠错

    【参数】
        text: 原始文本
        vocab: 词汇表映射（错误词 -> 正确词）

    【返回】
        str: 纠错后的文本
    """
    if not vocab:
        return text

    corrected = text
    for wrong, correct in vocab.items():
        # 使用整词匹配，避免部分匹配
        # 例如：只替换 "Sai AI"，不替换 "Sai AIx" 中的部分内容
        pattern = r'\b' + re.escape(wrong) + r'\b'
        corrected = re.sub(pattern, correct, corrected, flags=re.IGNORECASE)

    return corrected


def clean_and_correct_text(text: str, vocab: Optional[Dict[str, str]] = None) -> str:
    """
    【功能】完整文本清洗和纠错流程

    【处理流程】
        1. 基础文本清洗
        2. 词汇表纠错（如果提供）

    【参数】
        text: 原始文本
        vocab: 词汇表（可选）

    【返回】
        str: 处理后的文本
    """
    # 基础清洗
    cleaned = clean_text(text)

    # 词汇表纠错
    if vocab:
        cleaned = apply_vocab_correction(cleaned, vocab)

    return cleaned


# =============================================================================
# 文件输出
# =============================================================================

def generate_output_filename(input_path: Path, format_type: str, output_dir: Path) -> Path:
    """
    【功能】生成输出文件名

    【命名规则】
        格式: {format_type}_{input_stem}.md
        示例: note_test.md, weekly_meeting.md

    【参数】
        input_path: 输入文件路径
        format_type: 笔记格式（note/weekly/diary）
        output_dir: 输出目录

    【返回】
        Path: 完整的输出文件路径
    """
    stem = input_path.stem
    filename = f"{format_type}_{stem}.md"
    return output_dir / filename


def write_markdown(content: str, output_path: Path) -> None:
    """
    【功能】写入Markdown文件

    【参数】
        content: 文件内容
        output_path: 输出文件路径

    【异常】
        IOError: 写入失败
    """
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
