#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出写入模块

功能:
    - 将转录结果写入不同格式的文件
    - 支持TXT、SRT、VTT、JSON格式
    - 自动处理文件名冲突

设计说明:
    - TXT: 纯文本，适合阅读和编辑
    - SRT: SubRip字幕格式，适合视频播放器
    - VTT: WebVTT字幕格式，适合Web视频
    - JSON: 完整数据格式，包含所有元信息
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OutputWriter:
    """
    输出写入器类

    负责将转录结果保存为各种格式的文件。

    Attributes:
        output_dir (Path): 输出目录路径
        encoding (str): 文件编码，默认UTF-8
    """

    # 支持的输出格式
    SUPPORTED_FORMATS = ["txt", "srt", "vtt", "json"]

    def __init__(self, output_dir: Path, encoding: str = "utf-8"):
        """
        初始化输出写入器

        Args:
            output_dir: 输出目录路径
            encoding: 文件编码，默认"utf-8"

        Raises:
            ValueError: 输出目录无效
        """
        self.output_dir = Path(output_dir)
        self.encoding = encoding

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.output_dir.is_dir():
            raise ValueError(f"输出路径不是有效目录: {output_dir}")

        logger.debug(f"输出写入器初始化: {self.output_dir}")

    def write(
        self,
        result: Dict[str, Any],
        source_filename: str,
        format_type: str = "txt"
    ) -> Path:
        """
        写入转录结果到文件

        Args:
            result: 转录结果字典
            source_filename: 源文件名（用于生成输出文件名）
            format_type: 输出格式（txt/srt/vtt/json）

        Returns:
            Path: 生成的输出文件路径

        Raises:
            ValueError: 不支持的格式
            IOError: 文件写入失败
        """
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的输出格式: {format_type}\n"
                f"支持的格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # 生成输出文件路径
        output_file = self._generate_output_path(source_filename, format_type)

        logger.debug(f"写入{format_type.upper()}格式: {output_file}")

        # 根据格式调用对应的写入方法
        writers = {
            "txt": self._write_txt,
            "srt": self._write_srt,
            "vtt": self._write_vtt,
            "json": self._write_json,
        }

        writer = writers[format_type]
        writer(result, output_file)

        return output_file

    def _generate_output_path(self, source_filename: str, format_type: str) -> Path:
        """
        生成输出文件路径

        如果文件已存在，自动添加序号后缀避免覆盖。

        Args:
            source_filename: 源文件名（不含扩展名）
            format_type: 输出格式扩展名

        Returns:
            Path: 输出文件路径
        """
        base_name = Path(source_filename).stem
        output_file = self.output_dir / f"{base_name}.{format_type}"

        # 如果文件已存在，添加序号
        counter = 1
        while output_file.exists():
            output_file = self.output_dir / f"{base_name}_{counter}.{format_type}"
            counter += 1

        return output_file

    def _write_txt(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        写入纯文本格式

        格式说明:
            - 仅包含转录的完整文本
            - 段落之间用空行分隔
            - 适合阅读和编辑
        """
        text = result.get("text", "").strip()

        # 如果没有完整文本，从段落拼接
        if not text and "segments" in result:
            text = "\n\n".join(
                seg.get("text", "").strip()
                for seg in result["segments"]
            )

        with open(output_file, "w", encoding=self.encoding) as f:
            f.write(text)
            f.write("\n")  # 文件末尾换行

    def _write_srt(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        写入SRT字幕格式

        SRT格式规范:
            1. 段落序号（从1开始）
            2. 时间轴: HH:MM:SS,mmm --> HH:MM:SS,mmm
            3. 字幕文本（可多行）
            4. 空行（段落分隔）
        """
        segments = result.get("segments", [])

        with open(output_file, "w", encoding=self.encoding) as f:
            for i, seg in enumerate(segments, start=1):
                start_time = self._seconds_to_srt_time(seg.get("start", 0))
                end_time = self._seconds_to_srt_time(seg.get("end", 0))
                text = seg.get("text", "").strip()

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n")
                f.write("\n")

    def _write_vtt(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        写入WebVTT字幕格式

        VTT格式规范:
            - 文件头: WEBVTT
            - 时间轴: HH:MM:SS.mmm --> HH:MM:SS.mmm
            - 支持样式和定位（本实现使用基础格式）
        """
        segments = result.get("segments", [])

        with open(output_file, "w", encoding=self.encoding) as f:
            f.write("WEBVTT\n")
            f.write("\n")

            for seg in segments:
                start_time = self._seconds_to_vtt_time(seg.get("start", 0))
                end_time = self._seconds_to_vtt_time(seg.get("end", 0))
                text = seg.get("text", "").strip()

                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n")
                f.write("\n")

    def _write_json(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        写入JSON格式

        包含完整信息:
            - 完整文本
            - 所有段落（含时间戳和置信度）
            - 检测到的语言
            - 元数据（生成时间、版本等）
        """
        # 添加元数据
        output_data = {
            "text": result.get("text", "").strip(),
            "language": result.get("language", "unknown"),
            "segments": result.get("segments", []),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "format": "json"
            }
        }

        with open(output_file, "w", encoding=self.encoding) as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """
        将秒数转换为SRT时间格式: HH:MM:SS,mmm

        Args:
            seconds: 时间（秒）

        Returns:
            str: SRT格式时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        """
        将秒数转换为VTT时间格式: HH:MM:SS.mmm

        Args:
            seconds: 时间（秒）

        Returns:
            str: VTT格式时间字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """
        获取支持的格式列表

        Returns:
            list: 格式名称列表
        """
        return cls.SUPPORTED_FORMATS.copy()
