#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Note (V2N) - 视频转笔记统一工具
主入口脚本 (main.py)

【模块用途】
    作为项目的统一命令行入口，提供三种工作模式：
    1. v2t 模式: 视频转文本 (Video to Text)
    2. t2n 模式: 文本转笔记 (Text to Note)
    3. v2n 模式: 视频转笔记 (Video to Note，一键完成)

【使用示例】
    # 模式1: 视频转文本
    python main.py --mode v2t --input video.mp4

    # 模式2: 文本转笔记
    python main.py --mode t2n --input transcript.txt --note-format note

    # 模式3: 视频直接转笔记
    python main.py --mode v2n --input video.mp4 --note-format weekly

【设计原则】
    - 复用现有: transcribe.py 和 generate.py 完全复用，不做重复实现
    - 参数透传: 各模式专属参数原样传递给对应脚本
    - 流程协调: v2n模式自动串联v2t和t2n流程
"""

import sys
import os
import argparse
import logging
import subprocess
import signal
from pathlib import Path
from typing import Optional, List

# =============================================================================
# 从 utils 包导入工具函数
# =============================================================================

from utils import (
    setup_logging,
    validate_input_file,
    validate_output_dir,
    get_project_root,
)

# =============================================================================
# 配置常量区
# =============================================================================

# 【退出码定义】
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_V2T_ERROR = 3
EXIT_T2N_ERROR = 4
EXIT_INTERRUPTED = 130

# 【支持的配置选项】
SUPPORTED_MODES = ["v2t", "t2n", "v2n"]
SUPPORTED_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
SUPPORTED_NOTE_FORMATS = ["note", "weekly", "diary"]
SUPPORTED_TEXT_FORMATS = ["txt", "json"]

# 【默认值配置】
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_NOTE_FORMAT = "note"
DEFAULT_TEXT_FORMAT = "txt"
DEFAULT_LLM_MODEL = "qwen3-max"


# =============================================================================
# 命令行参数解析
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    【功能】解析命令行参数

    【返回】
        argparse.Namespace: 包含所有解析后参数的对象
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Video2Note (V2N) - 视频转笔记统一工具，支持 v2t/t2n/v2n 三种模式",
        epilog="""示例:
  # 视频转文本
  python main.py --mode v2t -i video.mp4

  # 文本转笔记
  python main.py --mode t2n -i transcript.txt -nf weekly

  # 视频直接转笔记（一键完成）
  python main.py --mode v2n -i video.mp4 -nf note --keep-text
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 【核心参数组】
    parser.add_argument(
        "--mode", "-m",
        type=str,
        required=True,
        choices=SUPPORTED_MODES,
        help=f"工作模式。必需。可选: {', '.join(SUPPORTED_MODES)}"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="输入文件路径（必需）。视频文件(mp4/mkv等)或文本文件(txt/json)。"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出根目录。默认: output/"
    )

    # 【v2t 相关参数】
    v2t_group = parser.add_argument_group("v2t 模式参数（视频转文本）")
    v2t_group.add_argument(
        "--whisper-model",
        type=str,
        default=DEFAULT_WHISPER_MODEL,
        choices=SUPPORTED_WHISPER_MODELS,
        help=f"Whisper 模型大小。可选: {', '.join(SUPPORTED_WHISPER_MODELS)}。默认: {DEFAULT_WHISPER_MODEL}"
    )

    v2t_group.add_argument(
        "--language", "-l",
        type=str,
        default="auto",
        help="语言代码，如 zh(中文)、en(英文)、ja(日语)。默认: auto（自动检测）"
    )

    v2t_group.add_argument(
        "--text-format",
        type=str,
        default=DEFAULT_TEXT_FORMAT,
        choices=SUPPORTED_TEXT_FORMATS,
        help=f"文本输出格式。可选: {', '.join(SUPPORTED_TEXT_FORMATS)}。默认: {DEFAULT_TEXT_FORMAT}"
    )

    v2t_group.add_argument(
        "--simplified-chinese",
        action="store_true",
        help="强制使用简体中文输出（针对中文语音）"
    )

    v2t_group.add_argument(
        "--device", "-d",
        type=str,
        default=None,
        choices=["cpu", "cuda"],
        help="Whisper运行设备。可选: cpu, cuda。默认: auto"
    )

    v2t_group.add_argument(
        "--keep-temp",
        action="store_true",
        help="保留临时音频文件（调试用）。默认会自动删除。"
    )

    v2t_group.add_argument(
        "--ffmpeg-path",
        type=str,
        default=None,
        help="FFmpeg 可执行文件路径（默认优先使用项目 tools/ 目录下的 ffmpeg）"
    )

    # 【t2n 相关参数】
    t2n_group = parser.add_argument_group("t2n 模式参数（文本转笔记）")
    t2n_group.add_argument(
        "--note-format", "-nf",
        type=str,
        default=DEFAULT_NOTE_FORMAT,
        choices=SUPPORTED_NOTE_FORMATS,
        help=f"笔记格式。可选: {', '.join(SUPPORTED_NOTE_FORMATS)}。默认: {DEFAULT_NOTE_FORMAT}"
    )

    t2n_group.add_argument(
        "--llm-model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"大模型选择。默认: {DEFAULT_LLM_MODEL}"
    )

    t2n_group.add_argument(
        "--vocab",
        type=str,
        default=None,
        help="自定义词汇表JSON文件路径，支持多个文件用逗号分隔"
    )

    t2n_group.add_argument(
        "--temperature", "-t",
        type=float,
        default=None,
        help="生成温度 (0.0-2.0)。较低值更确定，较高值更多样。默认: 按格式自动选择"
    )

    t2n_group.add_argument(
        "--max-length",
        type=str,
        default="medium",
        choices=["short", "medium", "long"],
        help="输出长度: short(简洁), medium(标准), long(详细)。默认: medium"
    )

    t2n_group.add_argument(
        "--preview",
        action="store_true",
        help="预览模式：不保存文件，直接打印到终端"
    )

    t2n_group.add_argument(
        "--show-prompt",
        action="store_true",
        help="显示提示词结构（调试用）"
    )

    # 【v2n 专用参数】
    v2n_group = parser.add_argument_group("v2n 模式参数（视频转笔记）")
    v2n_group.add_argument(
        "--keep-text",
        action="store_true",
        help="保留中间文本文件（默认自动清理）"
    )

    # 【通用参数】
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志输出（DEBUG 级别）"
    )

    return parser.parse_args()


# =============================================================================
# 工具函数
# =============================================================================

def build_v2t_command(args: argparse.Namespace, output_dir: str) -> List[str]:
    """
    【功能】构建 transcribe.py 的命令行参数

    【参数】
        args: 解析后的命令行参数
        output_dir: 文本输出目录

    【返回】
        List[str]: 命令行参数列表
    """
    cmd = [
        sys.executable,
        "transcribe.py",
        "-i", args.input,
        "-o", output_dir,
        "-m", args.whisper_model,
        "-l", args.language,
        "-f", args.text_format,
    ]

    if args.simplified_chinese:
        cmd.append("--simplified-chinese")

    if args.device:
        cmd.extend(["-d", args.device])

    if args.keep_temp:
        cmd.append("--keep-temp")

    if args.ffmpeg_path:
        cmd.extend(["--ffmpeg-path", args.ffmpeg_path])

    if args.verbose:
        cmd.append("-v")

    return cmd


def build_t2n_command(args: argparse.Namespace, input_file: str, output_dir: str) -> List[str]:
    """
    【功能】构建 generate.py 的命令行参数

    【参数】
        args: 解析后的命令行参数
        input_file: 输入文本文件路径
        output_dir: 笔记输出目录

    【返回】
        List[str]: 命令行参数列表
    """
    cmd = [
        sys.executable,
        "generate.py",
        "-i", input_file,
        "-o", output_dir,
        "-f", args.note_format,
        "-m", args.llm_model,
    ]

    if args.vocab:
        cmd.extend(["--vocab", args.vocab])

    if args.temperature is not None:
        cmd.extend(["-t", str(args.temperature)])

    if args.max_length:
        cmd.extend(["--max-length", args.max_length])

    if args.preview:
        cmd.append("--preview")

    if args.show_prompt:
        cmd.append("--show-prompt")

    if args.verbose:
        cmd.append("-v")

    return cmd


def run_subprocess(cmd: List[str], logger: logging.Logger, error_code: int) -> int:
    """
    【功能】运行子进程并处理错误

    【参数】
        cmd: 命令行参数列表
        logger: 日志记录器
        error_code: 错误时返回的退出码

    【返回】
        int: 子进程的退出码
    """
    logger.debug(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        logger.info("\n用户中断")
        return EXIT_INTERRUPTED
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return error_code


def get_filename_without_ext(filepath: str) -> str:
    """获取不带扩展名的文件名"""
    return Path(filepath).stem


# =============================================================================
# 主函数 - 流程编排
# =============================================================================

def main() -> int:
    """
    【功能】主入口函数 - 根据模式调度对应的处理流程

    【处理流程】
        Step 1: 解析命令行参数
        Step 2: 设置日志系统
        Step 3: 验证输入文件
        Step 4: 根据模式执行对应流程

    【返回】
        int: 退出码，0 表示成功
    """
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

    # 【欢迎信息】
    logger.info("=" * 60)
    logger.info("Video2Note (V2N) - 视频转笔记统一工具")
    logger.info(f"工作模式: {args.mode.upper()}")
    logger.info("=" * 60)

    # verbose 模式下显示详细配置
    if args.verbose:
        logger.debug("【运行配置】")
        logger.debug(f"  输入文件: {args.input}")
        logger.debug(f"  输出目录: {args.output}")
        logger.debug(f"  模式: {args.mode}")

    # -------------------------------------------------------------------------
    # Step 3: 验证输入文件
    # -------------------------------------------------------------------------
    logger.info("[1/3] 验证输入文件...")
    input_path = Path(args.input)

    if not validate_input_file(input_path):
        logger.error(f"错误: 输入文件不存在或不可读 - {args.input}")
        return EXIT_FILE_NOT_FOUND

    logger.info(f"  [OK] 输入文件有效: {input_path.name}")

    # -------------------------------------------------------------------------
    # Step 4: 根据模式执行对应流程
    # -------------------------------------------------------------------------
    logger.info("[2/3] 初始化输出目录...")

    output_root = Path(args.output)
    text_output_dir = output_root / "text"
    notes_output_dir = output_root / "notes"
    temp_output_dir = output_root / "temp"

    # 确保输出目录存在
    if not args.preview or args.mode == "v2t":
        text_output_dir.mkdir(parents=True, exist_ok=True)
    if not args.preview or args.mode in ["t2n", "v2n"]:
        notes_output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "v2n":
        temp_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"  [OK] 输出目录就绪: {output_root.absolute()}")

    # -------------------------------------------------------------------------
    # Step 5: 根据模式执行
    # -------------------------------------------------------------------------
    logger.info("[3/3] 执行处理流程...")
    logger.info("")

    if args.mode == "v2t":
        # ========== v2t 模式: 视频转文本 ==========
        logger.info("=" * 60)
        logger.info("【v2t 模式】视频转文本")
        logger.info("=" * 60)

        cmd = build_v2t_command(args, str(text_output_dir))
        exit_code = run_subprocess(cmd, logger, EXIT_V2T_ERROR)

        if exit_code == EXIT_SUCCESS:
            logger.info("")
            logger.info("=" * 60)
            logger.info("[DONE] 视频转文本完成！")
            logger.info(f"输出目录: {text_output_dir}")
            logger.info("=" * 60)

        return exit_code

    elif args.mode == "t2n":
        # ========== t2n 模式: 文本转笔记 ==========
        logger.info("=" * 60)
        logger.info("【t2n 模式】文本转笔记")
        logger.info("=" * 60)

        cmd = build_t2n_command(args, args.input, str(notes_output_dir))
        exit_code = run_subprocess(cmd, logger, EXIT_T2N_ERROR)

        if exit_code == EXIT_SUCCESS:
            logger.info("")
            logger.info("=" * 60)
            logger.info("[DONE] 文本转笔记完成！")
            logger.info(f"输出目录: {notes_output_dir}")
            logger.info("=" * 60)

        return exit_code

    elif args.mode == "v2n":
        # ========== v2n 模式: 视频转笔记 ==========
        logger.info("=" * 60)
        logger.info("【v2n 模式】视频转笔记（一键完成）")
        logger.info("=" * 60)

        # 步骤1: 视频转文本
        logger.info("")
        logger.info("-" * 60)
        logger.info("【步骤 1/2】视频转文本")
        logger.info("-" * 60)

        temp_text_file = temp_output_dir / f"{get_filename_without_ext(args.input)}.txt"

        # 构建 v2t 命令（输出到 temp 目录）
        v2t_args = argparse.Namespace(**vars(args))
        v2t_args.text_format = "txt"  # 强制使用 txt 格式

        cmd_v2t = build_v2t_command(v2t_args, str(temp_output_dir))
        exit_code = run_subprocess(cmd_v2t, logger, EXIT_V2T_ERROR)

        if exit_code != EXIT_SUCCESS:
            logger.error("错误: 视频转文本失败")
            return exit_code

        # 检查文本文件是否生成
        if not temp_text_file.exists():
            # 可能文件名有差异，尝试查找
            txt_files = list(temp_output_dir.glob("*.txt"))
            if txt_files:
                temp_text_file = txt_files[0]
            else:
                logger.error(f"错误: 未能找到生成的文本文件")
                return EXIT_V2T_ERROR

        logger.info(f"  [OK] 临时文本文件: {temp_text_file}")

        # 步骤2: 文本转笔记
        logger.info("")
        logger.info("-" * 60)
        logger.info("【步骤 2/2】文本转笔记")
        logger.info("-" * 60)

        cmd_t2n = build_t2n_command(args, str(temp_text_file), str(notes_output_dir))
        exit_code = run_subprocess(cmd_t2n, logger, EXIT_T2N_ERROR)

        if exit_code != EXIT_SUCCESS:
            logger.error("错误: 文本转笔记失败")
            # 保留临时文件以便调试
            logger.info(f"保留临时文件: {temp_text_file}")
            return exit_code

        # 步骤3: 清理临时文件
        if not args.keep_text and temp_text_file.exists():
            try:
                temp_text_file.unlink()
                logger.info(f"  [OK] 临时文本文件已清理")
            except Exception as e:
                logger.warning(f"  警告: 无法删除临时文件 - {e}")
        elif args.keep_text:
            logger.info(f"  [OK] 保留临时文本文件: {temp_text_file}")

        # 完成
        logger.info("")
        logger.info("=" * 60)
        logger.info("[DONE] 视频转笔记完成！")
        logger.info(f"输出目录: {notes_output_dir}")
        logger.info("=" * 60)

        return EXIT_SUCCESS

    else:
        logger.error(f"错误: 不支持的模式 - {args.mode}")
        return EXIT_INVALID_ARGS


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    sys.exit(main())
