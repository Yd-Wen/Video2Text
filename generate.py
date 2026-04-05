#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text2Note (T2N) - 文本转笔记工具
主入口脚本 (generate.py)

【模块用途】
    作为项目的命令行入口，负责：
    1. 解析用户命令行参数
    2. 读取本地文本文件（支持txt/json）
    3. 预处理文本（清洗、纠错）
    4. 调用大模型生成结构化笔记
    5. 输出Markdown文件

【使用示例】
    # 基础用法 - 必需参数
    python generate.py --input ./output/text/test.txt --output ./output/notes/

    # 指定格式
    python generate.py --input meeting.txt --output ./output/notes/ --format weekly

    # 使用多个词汇表
    python generate.py --input meeting.txt --vocab vocab/default.json,vocab/work.json

    # 预览模式
    python generate.py --input draft.txt --preview

【设计原则】
    - 单一职责：只负责流程编排，具体实现委托给子模块
    - 快速失败：前置验证，尽早发现错误
    - 标准退出码：便于脚本调用和CI集成
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# =============================================================================
# 从 utils 包导入工具函数
# =============================================================================

from utils import (
    setup_logging,
    validate_input_file,
    validate_output_dir,
    get_project_root,
    read_text_file,
    read_json_transcript,
    read_vocab_file,
    merge_vocab_files,
    clean_text,
    apply_vocab_correction,
    generate_output_filename,
    write_markdown,
)

# 导入提示词加载器
from prompts_loader import get_prompt_loader

# =============================================================================
# 配置常量区 - 集中管理可配置参数
# =============================================================================

# 【退出码定义】遵循 Unix 惯例，便于 shell 脚本捕获错误类型
EXIT_SUCCESS = 0           # 执行成功
EXIT_INVALID_ARGS = 1      # 参数错误（由 argparse 自动处理）
EXIT_FILE_NOT_FOUND = 2    # 输入文件不存在或无法读取
EXIT_READ_ERROR = 3        # 文件读取失败
EXIT_OUTPUT_ERROR = 4      # 输出写入失败
EXIT_CONFIG_ERROR = 5      # 配置错误

# 【支持的配置选项】与业务逻辑解耦，方便后续扩展
SUPPORTED_FORMATS = ["note", "weekly", "diary"]  # 笔记格式白名单
SUPPORTED_MODELS = ["deepseek", "openai", "qwen"]  # 支持的模型

# 【默认值配置】与 argparse 定义保持一致，便于统一修改
DEFAULT_FORMAT = "note"    # 默认技术笔记格式
DEFAULT_MODEL = "deepseek"  # 默认使用deepseek


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
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Text2Note (T2N) - 文本转笔记工具，调用大模型生成结构化笔记",
        epilog="示例: python generate.py --input transcript.txt --output ./output/notes/ --format note",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 【必需参数组】用户必须提供的输入
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="输入文本文件路径（必需）。支持txt/json格式。"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output/notes",
        help="输出目录路径。默认: output/notes/"
    )

    # 【可选参数组】使用默认值即可运行的配置
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_FORMAT,
        choices=SUPPORTED_FORMATS,
        help=f"笔记格式。可选: {', '.join(SUPPORTED_FORMATS)}。默认: {DEFAULT_FORMAT}"
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        choices=SUPPORTED_MODELS,
        help=f"大模型选择。可选: {', '.join(SUPPORTED_MODELS)}。默认: {DEFAULT_MODEL}"
    )

    parser.add_argument(
        "--vocab",
        type=str,
        default=None,
        help="自定义词汇表JSON文件路径，支持多个文件用逗号分隔（如：vocab/default.json,vocab/tech.json）"
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式：不保存文件，直接打印到终端"
    )

    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="显示提示词结构（用于调试）：打印system和user提示词"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志输出（DEBUG 级别），便于排查问题"
    )

    return parser.parse_args()


def load_vocab_files(vocab_paths_str: Optional[str]) -> Optional[Dict[str, str]]:
    """
    【功能】加载词汇表文件

    【参数】
        vocab_paths_str: 逗号分隔的词汇表文件路径字符串

    【返回】
        Dict[str, str]: 合并后的词汇表字典，或 None
    """
    if not vocab_paths_str:
        # 默认加载 default.json
        default_vocab = Path("vocab/default.json")
        if default_vocab.exists():
            return read_vocab_file(default_vocab)
        return None

    # 解析多个文件路径
    paths = [p.strip() for p in vocab_paths_str.split(",")]

    vocab_files = []
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            vocab_files.append(path)
        else:
            logging.warning(f"词汇表文件不存在: {path}")

    if not vocab_files:
        return None

    # 合并多个词汇表
    return merge_vocab_files(vocab_files)


# =============================================================================
# 主函数 - 流程编排
# =============================================================================

def main() -> int:
    """
    【功能】主入口函数 - 编排完整的笔记生成流程

    【处理流程】
        Step 1: 解析命令行参数
        Step 2: 设置日志级别
        Step 3: 验证输入文件
        Step 4: 验证/创建输出目录
        Step 5: 读取文本文件
        Step 6: 加载词汇表
        Step 7: 预处理文本
        Step 8: 构建提示词
        Step 9: 输出结果（文件或预览）

    【返回】
        int: 退出码，0 表示成功，其他表示错误类型
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
    logger.info("Text2Note (T2N) - 文本转笔记工具")
    logger.info("=" * 60)

    # verbose 模式下显示详细配置
    logger.debug("【运行配置】")
    logger.debug(f"  输入文件: {args.input}")
    logger.debug(f"  输出目录: {args.output}")
    logger.debug(f"  格式: {args.format}")
    logger.debug(f"  模型: {args.model}")
    logger.debug(f"  词汇表: {args.vocab or '默认'}")
    logger.debug(f"  预览模式: {args.preview}")
    logger.debug(f"  显示提示词: {args.show_prompt}")

    # -------------------------------------------------------------------------
    # Step 3: 验证输入文件
    # -------------------------------------------------------------------------
    logger.info("[1/6] 验证输入文件...")
    input_path = Path(args.input)

    if not validate_input_file(input_path):
        logger.error(f"错误: 输入文件不存在或不可读 - {args.input}")
        return EXIT_FILE_NOT_FOUND

    logger.info(f"  [OK] 输入文件有效: {input_path.name}")

    # -------------------------------------------------------------------------
    # Step 4: 验证/创建输出目录
    # -------------------------------------------------------------------------
    if not args.preview:
        logger.info("[2/6] 验证输出目录...")
        output_dir = Path(args.output)

        if not validate_output_dir(output_dir):
            logger.error(f"错误: 无法创建或写入输出目录 - {args.output}")
            return EXIT_OUTPUT_ERROR

        logger.info(f"  [OK] 输出目录就绪: {output_dir.absolute()}")
    else:
        logger.info("[2/6] 预览模式，跳过输出目录验证")
        output_dir = Path(args.output)

    # -------------------------------------------------------------------------
    # Step 5: 读取文本文件
    # -------------------------------------------------------------------------
    logger.info("[3/6] 读取文本文件...")

    try:
        # 根据文件扩展名选择读取方式
        if input_path.suffix.lower() == '.json':
            raw_text = read_json_transcript(input_path)
            logger.info(f"  [OK] JSON转录文件读取完成")
        else:
            raw_text = read_text_file(input_path)
            logger.info(f"  [OK] 文本文件读取完成")

        # 显示文本统计
        char_count = len(raw_text)
        line_count = raw_text.count('\n') + 1
        logger.info(f"    字符数: {char_count}")
        logger.info(f"    行数: {line_count}")

    except UnicodeDecodeError as e:
        logger.error(f"错误: 文件编码识别失败 - {e}")
        return EXIT_READ_ERROR
    except Exception as e:
        logger.error(f"错误: 文件读取失败 - {e}")
        return EXIT_READ_ERROR

    # -------------------------------------------------------------------------
    # Step 6: 加载词汇表
    # -------------------------------------------------------------------------
    logger.info("[4/6] 加载词汇表...")

    vocab = load_vocab_files(args.vocab)
    if vocab:
        logger.info(f"  [OK] 词汇表加载完成，共 {len(vocab)} 条映射")
    else:
        logger.info(f"  [OK] 未使用词汇表")

    # -------------------------------------------------------------------------
    # Step 7: 预处理文本
    # -------------------------------------------------------------------------
    logger.info("[5/6] 预处理文本...")

    # 基础清洗
    cleaned_text = clean_text(raw_text)

    # 应用词汇表纠错
    if vocab:
        cleaned_text = apply_vocab_correction(cleaned_text, vocab)
        logger.info(f"  [OK] 文本清洗和词汇纠错完成")
    else:
        logger.info(f"  [OK] 文本清洗完成")

    # 显示清洗统计
    cleaned_char_count = len(cleaned_text)
    removed_chars = char_count - cleaned_char_count
    logger.info(f"    清洗后字符数: {cleaned_char_count}")
    logger.info(f"    去除字符数: {removed_chars}")

    # verbose 模式下显示预览
    if args.verbose:
        preview = cleaned_text[:300]
        if len(cleaned_text) > 300:
            preview += "..."
        logger.debug(f"  清洗后预览: {preview}")

    # -------------------------------------------------------------------------
    # Step 8: 构建提示词
    # -------------------------------------------------------------------------
    logger.info("[6/6] 构建提示词...")

    # 创建提示词加载器
    prompt_loader = get_prompt_loader()

    # 构建消息
    messages = prompt_loader.build_messages(
        format_type=args.format,
        text=cleaned_text,
        vocab=vocab
    )

    logger.info(f"  [OK] 提示词构建完成")
    logger.info(f"    System prompt长度: {len(messages[0]['content'])} 字符")
    logger.info(f"    User prompt长度: {len(messages[1]['content'])} 字符")

    # 如果指定了--show-prompt，打印提示词结构
    if args.show_prompt:
        logger.info("=" * 60)
        logger.info("【提示词结构预览】")
        logger.info("=" * 60)
        print("\n" + "=" * 60)
        print("【SYSTEM PROMPT】")
        print("=" * 60)
        print(messages[0]['content'][:1000] + "..." if len(messages[0]['content']) > 1000 else messages[0]['content'])
        print("\n" + "=" * 60)
        print("【USER PROMPT】")
        print("=" * 60)
        print(messages[1]['content'][:800] + "..." if len(messages[1]['content']) > 800 else messages[1]['content'])
        print("=" * 60)

    # -------------------------------------------------------------------------
    # Step 9: 生成并输出结果
    # -------------------------------------------------------------------------
    # 生成输出文件名
    output_path = generate_output_filename(input_path, args.format, output_dir)

    # 构建Markdown内容（Phase 3：包含提示词预览，等待Phase 4大模型集成）
    md_content = f"""# {args.format.capitalize()} - {input_path.stem}

## 原始文本

{cleaned_text}

---

## 笔记内容

*[待Phase 4完成后由大模型生成结构化笔记]*

- 格式: {args.format}
- 模型: {args.model}
- System Prompt长度: {len(messages[0]['content'])} 字符
- User Prompt长度: {len(messages[1]['content'])} 字符
- 词汇表条目: {len(vocab) if vocab else 0} 条

"""

    if args.preview:
        # 预览模式：打印到终端
        logger.info("=" * 60)
        logger.info("【预览模式】输出内容:")
        logger.info("=" * 60)
        print(md_content)
        logger.info("=" * 60)
        logger.info("[DONE] 预览完成（未保存文件）")
    else:
        # 文件模式：写入Markdown
        try:
            write_markdown(md_content, output_path)
            logger.info("=" * 60)
            logger.info("[DONE] 处理完成！")
            logger.info(f"输出文件: {output_path}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"错误: 写入输出文件失败 - {e}")
            return EXIT_OUTPUT_ERROR

    return EXIT_SUCCESS


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 执行主函数并返回退出码给操作系统
    sys.exit(main())
