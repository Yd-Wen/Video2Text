#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Text (V2T) - 视频语音转文本工具
主入口脚本 (transcribe.py)

【模块用途】
    作为项目的命令行入口，负责：
    1. 解析用户命令行参数
    2. 协调音频提取 → 语音转录 → 结果输出的完整流程
    3. 提供统一的错误处理和标准退出码

【使用示例】
    # 基础用法 - 必需参数
    python transcribe.py --input video.mp4 --output ./output/

    # 完整参数 - 指定语言、模型、格式
    python transcribe.py -i video.mp4 -o ./output/ -l zh -m base -f srt

    # 调试模式 - 保留临时文件，显示详细日志
    python transcribe.py -i video.mp4 -o ./output/ -v --keep-temp

【设计原则】
    - 单一职责：只负责流程编排，具体实现委托给子模块
    - 快速失败：前置验证，尽早发现错误
    - 标准退出码：便于脚本调用和CI集成
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 【导入项目模块】
from audio_extractor import AudioExtractor
from transcriber import WhisperTranscriber
from output_writer import OutputWriter


# =============================================================================
# 配置常量区 - 集中管理可配置参数
# =============================================================================

# 【退出码定义】遵循 Unix 惯例，便于 shell 脚本捕获错误类型
EXIT_SUCCESS = 0           # 执行成功
EXIT_INVALID_ARGS = 1      # 参数错误（由 argparse 自动处理）
EXIT_FILE_NOT_FOUND = 2    # 输入文件不存在或无法读取
EXIT_FFMPEG_ERROR = 3      # FFmpeg 音频提取失败
EXIT_TRANSCRIBE_ERROR = 4  # Whisper 转录过程出错
EXIT_OUTPUT_ERROR = 5      # 输出写入失败
EXIT_MODEL_ERROR = 6       # 模型加载失败

# 【支持的配置选项】与业务逻辑解耦，方便后续扩展
SUPPORTED_FORMATS = ["txt", "srt", "vtt", "json"]  # 输出格式白名单
SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large"]  # Whisper模型

# 【默认值配置】与 argparse 定义保持一致，便于统一修改
DEFAULT_MODEL = "base"     # 平衡准确度与速度
DEFAULT_FORMAT = "txt"     # 最通用的纯文本格式
DEFAULT_LANGUAGE = "auto"  # 由 Whisper 自动检测语言


# =============================================================================
# 路径配置
# =============================================================================

def get_project_root() -> Path:
    """
    【功能】获取项目根目录

    【返回】
        Path: 项目根目录路径（即 transcribe.py 所在目录）
    """
    return Path(__file__).parent


def get_models_dir() -> Path:
    """
    【功能】获取模型存放目录

    【说明】
        模型存放在项目根目录的 models/ 文件夹下，
        如果不存在会自动创建。

    【返回】
        Path: 模型目录路径
    """
    models_dir = get_project_root() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


# =============================================================================
# FFmpeg 路径检测
# =============================================================================

def get_default_ffmpeg_path() -> str:
    """
    【功能】获取默认的 FFmpeg 路径，优先使用项目内 FFmpeg

    【检测顺序】
        1. 项目根目录的 tools/ffmpeg.exe (Windows) 或 tools/ffmpeg (Linux/Mac)
        2. 回退到系统 PATH 中的 ffmpeg

    【返回】
        str: FFmpeg 可执行文件路径
    """
    project_dir = Path(__file__).parent
    tools_dir = project_dir / "tools"

    # 确定可执行文件名
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    project_ffmpeg = tools_dir / ffmpeg_exe

    if project_ffmpeg.exists():
        return str(project_ffmpeg)

    # 回退到系统 PATH
    return "ffmpeg"


def cleanup_temp_files() -> None:
    """
    【功能】清理项目临时目录中的残留文件

    【用途】
        在程序启动时调用，清理上次运行残留的临时音频文件。
        避免因程序异常退出导致的临时文件堆积。
    """
    temp_dir = Path(__file__).parent / "temp"
    if temp_dir.exists():
        for f in temp_dir.glob("v2t_audio_*.wav"):
            try:
                f.unlink()
            except Exception:
                pass  # 静默忽略删除失败


# =============================================================================
# 命令行参数解析
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    【功能】解析命令行参数

    【设计说明】
        - 使用标准库 argparse，无额外依赖
        - 同时支持长短参数形式（如 -i 和 --input）
        - 提供清晰的帮助信息和合理的默认值
        - 必填参数和可选参数分组展示

    【返回】
        argparse.Namespace: 包含所有解析后参数的对象
    """
    # 【ArgumentParser 配置】
    # - prog: 程序名，用于帮助信息显示
    # - description: 简短描述，显示在帮助信息开头
    # - epilog: 示例命令，显示在帮助信息末尾
    # - formatter_class: 使用 RawDescriptionHelpFormatter 保留示例格式
    parser = argparse.ArgumentParser(
        prog="transcribe.py",
        description="Video2Text (V2T) - 视频语音转文本工具，基于 OpenAI Whisper",
        epilog="示例: python transcribe.py -i video.mp4 -o ./output/ -l zh -m base",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 【必需参数组】用户必须提供的输入

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="输入视频文件路径（必需）。支持 MP4/MKV/AVI/MOV 等常见格式。"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出目录路径。默认: output/"
    )

    # 【可选参数组】使用默认值即可运行的配置

    parser.add_argument(
        "--language", "-l",
        type=str,
        default=DEFAULT_LANGUAGE,
        help=f"语言代码，如 zh(中文)、en(英文)、ja(日语)。默认: {DEFAULT_LANGUAGE}（自动检测）"
    )

    parser.add_argument(
        "--simplified-chinese",
        action="store_true",
        help="强制使用简体中文输出（针对中文语音）"
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        choices=SUPPORTED_MODELS,  # 限制可选值，输入无效时自动提示
        help=f"Whisper 模型大小。可选: {', '.join(SUPPORTED_MODELS)}。默认: {DEFAULT_MODEL}"
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_FORMAT,
        choices=SUPPORTED_FORMATS,
        help=f"输出格式。可选: {', '.join(SUPPORTED_FORMATS)}。默认: {DEFAULT_FORMAT}"
    )

    parser.add_argument(
        "--keep-temp",
        action="store_true",  # 布尔标志，存在为 True，不存在为 False
        help="保留临时音频文件（调试用）。默认会自动删除临时文件。"
    )

    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default=None,
        help="FFmpeg 可执行文件路径（默认优先使用项目 tools/ 目录下的 ffmpeg）"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志输出（DEBUG 级别），便于排查问题"
    )

    return parser.parse_args()


# =============================================================================
# 日志系统配置
# =============================================================================

def setup_logging(level: int = logging.INFO) -> None:
    """
    【功能】配置日志系统

    【设计说明】
        - 使用标准库 logging，无需额外依赖
        - 根据 verbose 模式切换日志详细程度
        - 非 verbose 模式下输出简洁，适合日常使用

    【参数】
        level: 日志级别，logging.INFO 或 logging.DEBUG
    """
    # 根据级别选择格式：DEBUG 显示更多信息
    if level == logging.DEBUG:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        log_format = "%(message)s"  # 简洁格式，只显示消息内容

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True  # 覆盖任何已有的日志配置
    )


# =============================================================================
# 验证函数
# =============================================================================

def validate_input_file(file_path: Path) -> bool:
    """
    【功能】验证输入文件是否有效

    【验证项】
        1. 文件是否存在
        2. 是否是文件（非目录）
        3. 是否可读
        4. 文件是否非空

    【参数】
        file_path: 要验证的文件路径

    【返回】
        bool: 验证通过返回 True，否则返回 False
    """
    import os

    if not file_path.exists():
        logging.debug(f"文件不存在: {file_path}")
        return False

    if not file_path.is_file():
        logging.debug(f"路径不是文件: {file_path}")
        return False

    if not os.access(file_path, os.R_OK):
        logging.debug(f"文件不可读: {file_path}")
        return False

    if file_path.stat().st_size == 0:
        logging.debug(f"文件为空: {file_path}")
        return False

    return True


def validate_output_dir(dir_path: Path) -> bool:
    """
    【功能】验证输出目录，不存在则自动创建

    【验证项】
        1. 目录是否存在或可创建
        2. 目录是否可写

    【参数】
        dir_path: 输出目录路径

    【返回】
        bool: 验证通过返回 True，否则返回 False
    """
    import os

    try:
        # 递归创建目录（包括父目录），exist_ok=True 避免重复创建报错
        dir_path.mkdir(parents=True, exist_ok=True)

        # 检查目录写入权限
        if not os.access(dir_path, os.W_OK):
            logging.debug(f"目录不可写: {dir_path}")
            return False

        return True
    except Exception as e:
        logging.debug(f"无法创建或访问目录 {dir_path}: {e}")
        return False


# =============================================================================
# 主函数 - 流程编排
# =============================================================================

def main() -> int:
    """
    【功能】主入口函数 - 编排完整的转录流程

    【处理流程】
        Step 1: 解析命令行参数
        Step 2: 设置日志级别
        Step 3: 验证输入文件
        Step 4: 验证/创建输出目录
        Step 5: 提取音频（占位）
        Step 6: 转录音频（占位）
        Step 7: 写入结果（占位）
        Step 8: 清理临时文件（占位）

    【返回】
        int: 退出码，0 表示成功，其他表示错误类型

    【退出码说明】
        0 - 成功完成
        1 - 参数错误（由 argparse 处理）
        2 - 输入文件不存在
        3 - FFmpeg 音频提取失败
        4 - 转录失败
        5 - 输出写入失败
        6 - 模型加载失败
    """
    # -------------------------------------------------------------------------
    # Step 0: 启动清理
    # -------------------------------------------------------------------------
    # 清理上次运行残留的临时文件
    cleanup_temp_files()

    # -------------------------------------------------------------------------
    # Step 1: 解析命令行参数
    # -------------------------------------------------------------------------
    args = parse_arguments()

    # -------------------------------------------------------------------------
    # Step 2: 设置日志系统
    # -------------------------------------------------------------------------
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    # 【处理 FFmpeg 路径】
    # 如果用户未指定，使用自动检测的默认路径
    if args.ffmpeg_path is None:
        args.ffmpeg_path = get_default_ffmpeg_path()

    # 【欢迎信息】仅在非 verbose 模式显示简洁标题
    logger.info("=" * 60)
    logger.info("Video2Text (V2T) - 视频语音转文本工具")
    logger.info("=" * 60)

    # verbose 模式下显示详细配置
    logger.debug("【运行配置】")
    logger.debug(f"  输入文件: {args.input}")
    logger.debug(f"  输出目录: {args.output}")
    logger.debug(f"  语言: {args.language}")
    logger.debug(f"  模型: {args.model}")
    logger.debug(f"  格式: {args.format}")
    logger.debug(f"  保留临时文件: {args.keep_temp}")
    logger.debug(f"  FFmpeg 路径: {args.ffmpeg_path}")

    # -------------------------------------------------------------------------
    # Step 3: 验证输入文件
    # -------------------------------------------------------------------------
    logger.info("[1/5] 验证输入文件...")
    input_path = Path(args.input)

    if not validate_input_file(input_path):
        logger.error(f"错误: 输入文件不存在或不可读 - {args.input}")
        return EXIT_FILE_NOT_FOUND

    logger.info(f"  [OK] 输入文件有效: {input_path.name}")

    # -------------------------------------------------------------------------
    # Step 4: 验证/创建输出目录
    # -------------------------------------------------------------------------
    logger.info("[2/5] 验证输出目录...")
    output_dir = Path(args.output)

    if not validate_output_dir(output_dir):
        logger.error(f"错误: 无法创建或写入输出目录 - {args.output}")
        return EXIT_OUTPUT_ERROR

    logger.info(f"  [OK] 输出目录就绪: {output_dir.absolute()}")

    # -------------------------------------------------------------------------
    # Step 5: 提取音频
    # -------------------------------------------------------------------------
    logger.info("[3/5] 提取音频...")

    # 【初始化音频提取器】
    # 传入用户指定的 FFmpeg 路径，如果不在 PATH 中会立即报错
    try:
        audio_extractor = AudioExtractor(ffmpeg_path=args.ffmpeg_path)
    except RuntimeError as e:
        logger.error(f"错误: {e}")
        return EXIT_FFMPEG_ERROR

    # 【执行音频提取】
    # 输出临时 WAV 文件，供后续转录使用
    temp_audio_path: Optional[Path] = None
    try:
        temp_audio_path = audio_extractor.extract(input_path)
        logger.info(f"  [OK] 音频提取完成: {temp_audio_path}")
    except FileNotFoundError as e:
        logger.error(f"错误: {e}")
        return EXIT_FILE_NOT_FOUND
    except RuntimeError as e:
        logger.error(f"错误: 音频提取失败 - {e}")
        return EXIT_FFMPEG_ERROR

    # -------------------------------------------------------------------------
    # Step 6: 转录音频
    # -------------------------------------------------------------------------
    logger.info("[4/5] 加载模型并转录...")

    # 【初始化转录器】
    # 指定模型下载目录为项目根目录下的 models/ 文件夹
    models_dir = get_models_dir()
    transcriber = WhisperTranscriber(
        model_name=args.model,
        download_root=str(models_dir)
    )

    # 【存储转录结果】
    transcribe_result: Optional[Dict[str, Any]] = None

    try:
        # 【加载模型】
        # 首次加载会下载模型（如果需要），显示模型大小信息
        logger.info(f"  加载 Whisper 模型: {args.model}")
        transcriber.load_model()

        # 【执行转录】
        # language=None 表示自动检测，否则使用用户指定的语言
        language = None if args.language == "auto" else args.language
        transcribe_result = transcriber.transcribe(
            temp_audio_path,
            language=language,
            ffmpeg_path=args.ffmpeg_path,
            simplified_chinese=args.simplified_chinese
        )

        # 【显示转录统计】
        num_segments = len(transcribe_result["segments"])
        detected_lang = transcribe_result["language"]
        logger.info(f"  [OK] 转录完成")
        logger.info(f"    检测到语言: {detected_lang}")
        logger.info(f"    段落数: {num_segments}")

        # 【verbose 模式显示文本预览】
        if args.verbose:
            preview_text = transcribe_result["text"][:200]
            if len(transcribe_result["text"]) > 200:
                preview_text += "..."
            logger.debug(f"  文本预览: {preview_text}")

    except RuntimeError as e:
        logger.error(f"错误: 转录失败 - {e}")
        # 【保留临时文件以便调试】
        if temp_audio_path and temp_audio_path.exists():
            logger.info(f"  保留临时文件以供调试: {temp_audio_path}")
        return EXIT_TRANSCRIBE_ERROR
    except Exception as e:
        logger.error(f"错误: 未知转录错误 - {e}")
        if temp_audio_path and temp_audio_path.exists():
            logger.info(f"  保留临时文件以供调试: {temp_audio_path}")
        return EXIT_TRANSCRIBE_ERROR

    # -------------------------------------------------------------------------
    # Step 7: 写入输出文件
    # -------------------------------------------------------------------------
    logger.info("[5/5] 保存转录结果...")

    # 【初始化输出写入器】
    output_writer = OutputWriter(output_dir=output_dir)

    try:
        # 【执行写入】
        output_file = output_writer.write(
            result=transcribe_result,
            source_filename=input_path.name,
            format_type=args.format
        )

        logger.info(f"  [OK] 结果已保存: {output_file}")

    except ValueError as e:
        logger.error(f"错误: 输出格式无效 - {e}")
        return EXIT_OUTPUT_ERROR
    except IOError as e:
        logger.error(f"错误: 写入输出文件失败 - {e}")
        return EXIT_OUTPUT_ERROR

    # -------------------------------------------------------------------------
    # Step 8: 清理临时文件
    # -------------------------------------------------------------------------
    # 【自动清理临时音频文件】
    # 如果用户未指定 --keep-temp，删除提取的临时音频
    if not args.keep_temp and temp_audio_path and temp_audio_path.exists():
        try:
            temp_audio_path.unlink()
            logger.info("  [OK] 临时文件已清理")
        except Exception as e:
            logger.warning(f"  警告: 无法删除临时文件 - {e}")
    elif args.keep_temp and temp_audio_path:
        logger.info(f"  保留临时音频文件: {temp_audio_path}")

    # -------------------------------------------------------------------------
    # 完成
    # -------------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("[DONE] 转录任务完成！")
    logger.info(f"输出文件: {output_file}")
    logger.info("=" * 60)

    return EXIT_SUCCESS


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 执行主函数并返回退出码给操作系统
    sys.exit(main())
