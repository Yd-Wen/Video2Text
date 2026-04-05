#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Note (V2N) - 输出写入模块 (output_writer.py)

【模块用途】
    负责将转录结果保存为各种格式的文件。

    核心功能：
    1. 支持多种输出格式：TXT、JSON
    2. 自动处理文件名冲突（添加序号后缀）
    3. 确保输出目录存在并可写
    4. 统一的结果格式标准化

【输出格式说明】
    TXT: 纯文本格式
        - 仅包含转录的完整文本
        - 段落之间用空行分隔
        - 适合阅读、编辑、搜索引擎索引

    JSON: 完整数据格式
        - 包含所有转录信息
        - 包括时间戳、置信度、元数据
        - 适合程序化处理和分析

【使用示例】
    from output_writer import OutputWriter

    # 创建写入器
    writer = OutputWriter(output_dir=Path("./output"))

    # 写入不同格式
    writer.write(result, "video", format_type="txt")   # 纯文本
    writer.write(result, "video", format_type="json")  # 完整JSON

【依赖要求】
    - Python: 标准库 (json, pathlib, datetime)
    - 无第三方依赖
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# 获取模块级日志记录器
logger = logging.getLogger(__name__)


class OutputWriter:
    """
    【输出写入器类】

    封装转录结果的文件写入功能，支持多种格式。

    【属性】
        output_dir (Path): 输出目录路径
        encoding (str): 文件编码，默认 UTF-8

    【设计原则】
        - 格式无关：调用方只需提供格式类型，具体实现内部处理
        - 安全写入：自动处理文件名冲突，避免覆盖已有文件
        - 编码一致：统一使用 UTF-8，确保多语言支持
    """

    # 【支持的输出格式】
    SUPPORTED_FORMATS = ["txt", "json"]

    def __init__(self, output_dir: Path, encoding: str = "utf-8"):
        """
        【初始化输出写入器】

        【参数】
            output_dir: 输出目录路径（Path 对象或字符串）
            encoding: 文件编码，默认 "utf-8"

        【异常】
            ValueError: 输出路径不是有效目录

        【示例】
            # 使用默认编码
            writer = OutputWriter(Path("./output"))

            # 指定编码
            writer = OutputWriter(Path("./output"), encoding="utf-8-sig")
        """
        self.output_dir = Path(output_dir)
        self.encoding = encoding

        # 【自动创建输出目录】
        # 如果目录不存在，递归创建（包括父目录）
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 【验证目录有效性】
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
        【写入转录结果到文件】

        【参数】
            result: 转录结果字典，必须包含以下字段：
                    - text: 完整转录文本
                    - language: 检测到的语言代码
                    - segments: 段落列表，每个包含:
                        - id: 段落序号
                        - start: 开始时间（秒）
                        - end: 结束时间（秒）
                        - text: 段落文本
                        - confidence: 置信度（可选）
            source_filename: 源文件名（用于生成输出文件名）
            format_type: 输出格式（txt/srt/vtt/json）

        【返回】
            Path: 生成的输出文件完整路径

        【异常】
            ValueError: 不支持的格式
            IOError: 文件写入失败

        【示例】
            result = {
                "text": "你好世界",
                "language": "zh",
                "segments": [
                    {"id": 0, "start": 0.0, "end": 2.0, "text": "你好世界"}
                ]
            }

            # 写入 TXT
            path = writer.write(result, "video.mp4", "txt")
            # 生成: output/video.txt
        """
        # 【验证格式有效性】
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的输出格式: {format_type}\n"
                f"支持的格式: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # 【生成输出文件路径】
        output_file = self._generate_output_path(source_filename, format_type)

        logger.debug(f"写入 {format_type.upper()} 格式: {output_file}")

        # 【根据格式调用对应的写入方法】
        # 使用字典映射，便于扩展新格式
        writers = {
            "txt": self._write_txt,
            "json": self._write_json,
        }

        writer = writers[format_type]
        writer(result, output_file)

        logger.debug(f"  写入成功: {output_file.stat().st_size} 字节")

        return output_file

    def _generate_output_path(self, source_filename: str, format_type: str) -> Path:
        """
        【私有方法】生成输出文件路径

        【功能】
            基于源文件名生成输出文件名。
            如果文件已存在，自动添加序号后缀避免覆盖。

        【参数】
            source_filename: 源文件名（如 "video.mp4"）
            format_type: 输出格式扩展名（如 "txt"）

        【返回】
            Path: 输出文件路径（如 "output/video.txt" 或 "output/video_1.txt"）

        【示例】
            # 首次调用
            path = _generate_output_path("video.mp4", "txt")
            # 返回: output/video.txt

            # 文件已存在时的调用
            path = _generate_output_path("video.mp4", "txt")
            # 返回: output/video_1.txt
        """
        # 【提取基础文件名】
        # 去除原扩展名，如 "video.mp4" -> "video"
        base_name = Path(source_filename).stem

        # 【生成初始输出路径】
        output_file = self.output_dir / f"{base_name}.{format_type}"

        # 【处理文件名冲突】
        # 如果文件已存在，添加序号后缀
        counter = 1
        while output_file.exists():
            output_file = self.output_dir / f"{base_name}_{counter}.{format_type}"
            counter += 1

        return output_file

    def _write_txt(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        【私有方法】写入纯文本格式

        【格式说明】
            - 仅包含转录的完整文本
            - 如果 result 中没有完整文本，从段落拼接
            - 段落之间用空行分隔
            - 文件末尾添加换行符

        【示例输出】
            第一段转录文本。

            第二段转录文本。

            第三段转录文本。
        """
        # 【获取完整文本】
        text = result.get("text", "").strip()

        # 【如果无完整文本，从段落拼接】
        if not text and "segments" in result:
            text = "\n\n".join(
                seg.get("text", "").strip()
                for seg in result["segments"]
            )

        # 【写入文件】
        with open(output_file, "w", encoding=self.encoding) as f:
            f.write(text)
            f.write("\n")  # 文件末尾添加换行符（POSIX 标准）

    def _write_json(self, result: Dict[str, Any], output_file: Path) -> None:
        """
        【私有方法】写入 JSON 格式

        【JSON 结构】
            {
                "text": "完整转录文本",
                "language": "检测到的语言代码",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 5.32,
                        "text": "段落文本",
                        "confidence": -0.5
                    }
                ],
                "metadata": {
                    "generated_at": "2024-01-15T10:30:00",
                    "version": "1.0.0",
                    "format": "json"
                }
            }

        【特点】
            - 包含完整的转录信息
            - 支持程序化处理
            - 包含生成时间戳
        """
        # 【构建完整数据结构】
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

        # 【写入 JSON 文件】
        with open(output_file, "w", encoding=self.encoding) as f:
            json.dump(
                output_data,
                f,
                ensure_ascii=False,  # 支持 Unicode，不转义中文
                indent=2             # 美化格式，2 空格缩进
            )

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """
        【类方法】获取支持的格式列表

        【返回】
            list: 格式名称列表 ["txt", "json"]

        【示例】
            formats = OutputWriter.get_supported_formats()
            print(f"支持格式: {', '.join(formats)}")
        """
        return cls.SUPPORTED_FORMATS.copy()
