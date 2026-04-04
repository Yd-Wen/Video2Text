#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Text (V2T) - 视频语音转文本工具
主入口脚本

功能:
    - 解析命令行参数
    - 协调音频提取、转录、输出的完整流程
    - 提供统一的错误处理和退出码

使用示例:
    python transcribe.py --input video.mp4 --output ./output/
    python transcribe.py -i video.mp4 -o ./output/ -l zh -m base

作者: V2T Project
版本: 1.0.0
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# 导入项目模块
from audio_extractor import AudioExtractor
from transcriber import WhisperTranscriber
from output_writer import OutputWriter
from utils import validate_input_file, validate_output_dir, setup_logging


# =============================================================================
# 常量定义
# =============================================================================

# 退出码定义 - 遵循Unix惯例，便于脚本调用和CI集成
EXIT_SUCCESS = 0           # 成功完成
EXIT_INVALID_ARGS = 1      # 参数错误（argparse自动处理）
EXIT_FILE_NOT_FOUND = 2    # 输入文件不存在
EXIT_FFMPEG_ERROR = 3      # FFmpeg音频提取失败
EXIT_TRANSCRIBE_ERROR = 4  # 转录过程出错
EXIT_OUTPUT_ERROR = 5      # 输出写入失败
EXIT_MODEL_ERROR = 6       # 模型加载失败

# 支持的输出格式
SUPPORTED_FORMATS = ["txt", "srt", "vtt", "json"]

# 支持的Whisper模型
SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large"]

# 默认配置
DEFAULT_MODEL = "base"
DEFAULT_FORMAT = "txt"
DEFAULT_LANGUAGE = "auto"


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的参数对象

    设计说明:
        - 使用argparse标准库，无需额外依赖
        - 支持长短参数形式（如 -i 和 --input）
        - 提供清晰的帮助信息和默认值
    """
    parser = argparse.ArgumentParser(
        prog="transcribe.py",
        description="Video2Text (V2T) - 视频语音转文本工具，基于OpenAI Whisper",
        epilog="示例: python transcribe.py -i video.mp4 -o ./output/ -l zh -m base",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 必需参数
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="输入视频文件路径（必需）"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="输出目录路径（必需）"
    )

    # 可选参数 - 语言
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=DEFAULT_LANGUAGE,
        help=f"语言代码，如 zh(中文)、en(英文)、ja(日语)。默认: {DEFAULT_LANGUAGE}（自动检测）"
    )

    # 可选参数 - 模型
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        choices=SUPPORTED_MODELS,
        help=f"Whisper模型大小。可选: {', '.join(SUPPORTED_MODELS)}。默认: {DEFAULT_MODEL}"
    )

    # 可选参数 - 输出格式
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_FORMAT,
        choices=SUPPORTED_FORMATS,
        help=f"输出格式。可选: {', '.join(SUPPORTED_FORMATS)}。默认: {DEFAULT_FORMAT}"
    )

    # 可选参数 - 保留临时文件（调试用）
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="保留临时音频文件（调试用，默认自动删除）"
    )

    # 可选参数 - FFmpeg路径
    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default="ffmpeg",
        help="FFmpeg可执行文件路径（默认使用系统PATH中的ffmpeg）"
    )

    # 可选参数 - 详细日志
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志输出"
    )

    return parser.parse_args()


def main() -> int:
    """
    主入口函数

    Returns:
        int: 退出码，0表示成功，其他表示错误类型

    流程:
        1. 解析参数
        2. 验证输入输出
        3. 提取音频
        4. 加载模型并转录
        5. 写入结果
        6. 清理临时文件
    """
    # 解析命令行参数
    args = parse_arguments()

    # 设置日志级别
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Video2Text (V2T) - 视频语音转文本工具")
    logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # 步骤1: 验证输入文件
    # -------------------------------------------------------------------------
    logger.info(f"[1/4] 验证输入文件: {args.input}")
    input_path = Path(args.input)
    if not validate_input_file(input_path):
        logger.error(f"错误: 输入文件不存在或不可读 - {args.input}")
        return EXIT_FILE_NOT_FOUND
    logger.info(f"  ✓ 输入文件有效: {input_path.name}")

    # -------------------------------------------------------------------------
    # 步骤2: 验证/创建输出目录
    # -------------------------------------------------------------------------
    logger.info(f"[2/4] 验证输出目录: {args.output}")
    output_dir = Path(args.output)
    if not validate_output_dir(output_dir):
        logger.error(f"错误: 无法创建或写入输出目录 - {args.output}")
        return EXIT_OUTPUT_ERROR
    logger.info(f"  ✓ 输出目录就绪: {output_dir.absolute()}")

    # -------------------------------------------------------------------------
    # 步骤3: 提取音频
    # -------------------------------------------------------------------------
    logger.info("[3/4] 提取音频...")
    audio_extractor = AudioExtractor(ffmpeg_path=args.ffmpeg_path)

    temp_audio_path: Optional[Path] = None
    try:
        temp_audio_path = audio_extractor.extract(input_path)
        logger.info(f"  ✓ 音频提取完成: {temp_audio_path}")
    except Exception as e:
        logger.error(f"错误: 音频提取失败 - {e}")
        return EXIT_FFMPEG_ERROR

    # -------------------------------------------------------------------------
    # 步骤4: 转录音频
    # -------------------------------------------------------------------------
    logger.info("[4/4] 开始转录...")
    transcriber = WhisperTranscriber(model_name=args.model)

    try:
        # 加载模型（首次会下载，可能较慢）
        logger.info(f"  加载Whisper模型: {args.model}")
        transcriber.load_model()

        # 执行转录
        language = None if args.language == "auto" else args.language
        result = transcriber.transcribe(temp_audio_path, language=language)
        logger.info(f"  ✓ 转录完成，共 {len(result['segments'])} 个片段")

    except Exception as e:
        logger.error(f"错误: 转录失败 - {e}")
        # 保留临时文件以便调试
        if temp_audio_path and temp_audio_path.exists():
            logger.info(f"  保留临时文件以供调试: {temp_audio_path}")
        return EXIT_TRANSCRIBE_ERROR

    # -------------------------------------------------------------------------
    # 步骤5: 写入输出文件
    # -------------------------------------------------------------------------
    logger.info("保存转录结果...")
    output_writer = OutputWriter(output_dir=output_dir)

    try:
        output_file = output_writer.write(
            result=result,
            source_filename=input_path.stem,
            format_type=args.format
        )
        logger.info(f"  ✓ 结果已保存: {output_file}")
    except Exception as e:
        logger.error(f"错误: 写入输出文件失败 - {e}")
        return EXIT_OUTPUT_ERROR

    # -------------------------------------------------------------------------
    # 步骤6: 清理临时文件
    # -------------------------------------------------------------------------
    if not args.keep_temp and temp_audio_path and temp_audio_path.exists():
        try:
            temp_audio_path.unlink()
            logger.info("  ✓ 临时文件已清理")
        except Exception as e:
            logger.warning(f"  警告: 无法删除临时文件 - {e}")
    elif args.keep_temp:
        logger.info(f"  保留临时音频文件: {temp_audio_path}")

    # -------------------------------------------------------------------------
    # 完成
    # -------------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("✓ 转录任务完成！")
    logger.info(f"输出文件: {output_file}")
    logger.info("=" * 60)

    return EXIT_SUCCESS


if __name__ == "__main__":
    # 执行主函数并返回退出码
    sys.exit(main())
