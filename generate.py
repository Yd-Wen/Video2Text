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
    estimate_tokens,
    split_text_into_chunks,
)

# 导入提示词加载器
from prompts_loader import get_prompt_loader

# 导入 LLM 客户端和配置
from config import get_config
from llm_client import LLMClient, HAS_DASHSCOPE

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
EXIT_LLM_ERROR = 6         # 大模型调用失败

# 【支持的配置选项】与业务逻辑解耦，方便后续扩展
SUPPORTED_FORMATS = ["note", "weekly", "diary"]  # 笔记格式白名单
SUPPORTED_MODELS = ["qwen3-max"]  # 暂时仅支持 qwen3-max

# 【默认值配置】与 argparse 定义保持一致，便于统一修改
DEFAULT_FORMAT = "note"    # 默认技术笔记格式
DEFAULT_MODEL = "qwen3-max"  # 默认使用 qwen3-max

# 【格式推荐的温度设置】较低温度更确定，较高温度更创造性
FORMAT_TEMPERATURES = {
    "note": 0.5,      # 技术笔记：适中，平衡准确性和流畅性
    "weekly": 0.3,    # 周报：较低，确保事实准确
    "diary": 0.7,     # 日记：较高，更有文采和个性
}

# 【输出长度映射】映射到 max_tokens
LENGTH_TOKENS = {
    "short": 2048,    # 简洁摘要
    "medium": 4096,   # 标准笔记
    "long": 8192,     # 详细记录
}


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

    # 【Phase 5: 格式优化参数】
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=None,
        help="生成温度 (0.0-2.0)，控制创造性。较低值更确定，较高值更多样。默认: 按格式自动选择"
    )

    parser.add_argument(
        "--max-length", "-l",
        type=str,
        default="medium",
        choices=["short", "medium", "long"],
        help="输出长度控制: short(简洁摘要), medium(标准笔记), long(详细记录)。默认: medium"
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="禁用流式输出，等待完整响应后再输出（仅影响预览模式）"
    )

    return parser.parse_args()


def generate_multi_chunk(client, prompt_loader, text_chunks: List[str],
                         vocab: Optional[Dict[str, str]], args,
                         temperature: float, max_tokens: int,
                         output_path: Path, logger) -> int:
    """
    【功能】处理多段文本的生成

    【参数】
        client: LLMClient 实例
        prompt_loader: 提示词加载器
        text_chunks: 文本段列表
        vocab: 词汇表
        args: 命令行参数
        temperature: 温度参数
        max_tokens: 最大 token 数
        output_path: 输出文件路径
        logger: 日志记录器

    【返回】
        int: 退出码
    """
    from llm_client import GenerationResult

    logger.info(f"开始处理 {len(text_chunks)} 段文本...")

    all_contents = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_time = 0
    is_partial = False

    for i, chunk in enumerate(text_chunks, 1):
        logger.info(f"\n[{i}/{len(text_chunks)}] 生成第 {i} 段笔记...")

        # 构建提示词
        messages = prompt_loader.build_messages(
            format_type=args.format,
            text=chunk,
            vocab=vocab
        )

        if args.preview:
            # 预览模式只显示第一段
            logger.info("【预览模式仅显示第一段】\n")
            print("-" * 60)
            print(f"# 第 1/{len(text_chunks)} 段\n")

            generated_content = ""
            try:
                for text_chunk in client.generate_stream(messages, temperature=temperature, max_tokens=max_tokens):
                    print(text_chunk, end='', flush=True)
                    generated_content += text_chunk
                print("\n" + "-" * 60)
                logger.info("\n[DONE] 预览完成（多段文本仅显示第一段）")
                # 预览模式不继续处理
                return EXIT_SUCCESS
            except KeyboardInterrupt:
                print("\n" + "-" * 60)
                logger.info("\n[DONE] 生成被中断")
                return EXIT_SUCCESS
        else:
            # 文件模式：逐段生成
            try:
                # 为每段创建临时输出路径
                chunk_output = output_path.with_suffix(f'.part{i}.md')

                result = client.generate_to_file(
                    messages, chunk_output,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    show_progress=True
                )

                all_contents.append(result.content)
                total_input_tokens += result.input_tokens
                total_output_tokens += result.output_tokens
                total_time += result.generation_time

                if result.is_partial:
                    is_partial = True
                    logger.warning(f"⚠️ 第 {i} 段生成被中断")

                logger.info(f"  第 {i} 段完成 ({result.output_tokens} tokens)")

            except Exception as e:
                logger.error(f"错误: 第 {i} 段生成失败 - {e}")
                is_partial = True
                # 继续处理下一段

    # 合并所有段落
    if not args.preview and all_contents:
        logger.info("\n合并所有段落...")

        # 合并内容
        merged_content = f"# {args.format.capitalize()} 笔记\n\n"
        merged_content += f"*本文档由 {len(text_chunks)} 段内容合并生成*\n\n"
        merged_content += "---\n\n"

        for i, content in enumerate(all_contents, 1):
            if len(text_chunks) > 1:
                merged_content += f"## 第 {i} 部分\n\n"
            merged_content += content
            merged_content += "\n\n---\n\n"

        # 写入最终文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)

            # 删除临时文件
            for i in range(1, len(text_chunks) + 1):
                chunk_output = output_path.with_suffix(f'.part{i}.md')
                if chunk_output.exists():
                    chunk_output.unlink()

            # 显示统计
            logger.info("=" * 60)
            logger.info("[DONE] 笔记生成完成！")
            logger.info(f"输出文件: {output_path}")
            logger.info(f"总输入 Token: ~{total_input_tokens}")
            logger.info(f"总输出 Token: ~{total_output_tokens}")
            logger.info(f"总生成时间: {total_time:.2f}秒")

            if is_partial:
                logger.warning("⚠️ 注意: 部分段落生成被中断")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"错误: 合并文件失败 - {e}")
            return EXIT_OUTPUT_ERROR

    return EXIT_SUCCESS


def load_vocab_files(vocab_paths_str: Optional[str], input_path: Path) -> Optional[Dict[str, str]]:
    """
    【功能】加载词汇表文件

    【参数】
        vocab_paths_str: 逗号分隔的词汇表文件路径字符串，为None时自动检测与输入文件同名的JSON
        input_path: 输入文件路径，用于自动检测同名词汇表

    【返回】
        Dict[str, str]: 合并后的词汇表字典，或 None
    """
    if not vocab_paths_str:
        # 自动检测与输入文件同名的 JSON 词汇表文件
        # 例如: test.txt -> 查找 test.json
        auto_vocab = input_path.with_suffix('.json')
        if auto_vocab.exists():
            logging.info(f"  自动加载词汇表: {auto_vocab}")
            return read_vocab_file(auto_vocab)
        # 没有找到同名词汇表，返回空（不加载 default.json）
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

    # Phase 5: 计算实际使用的参数
    temperature = args.temperature if args.temperature is not None else FORMAT_TEMPERATURES.get(args.format, 0.5)
    max_tokens = LENGTH_TOKENS.get(args.max_length, 4096)
    logger.debug(f"  温度: {temperature}")
    logger.debug(f"  输出长度: {args.max_length} ({max_tokens} tokens)")

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

    vocab = load_vocab_files(args.vocab, input_path)
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
    # Step 8: 智能分段（Phase 5: 处理超长文本）
    # -------------------------------------------------------------------------
    logger.info("[6/6] 检查文本长度...")

    # 估算清洗后文本的 token 数
    text_tokens = estimate_tokens(cleaned_text)
    # 预留 4000 tokens 给提示词模板和系统提示词
    context_limit = 12000  # 保守估计，为提示词预留空间

    text_chunks = []
    if text_tokens > context_limit:
        logger.warning(f"⚠️ 文本较长（估算 {text_tokens} tokens），将自动分段处理")
        text_chunks = split_text_into_chunks(cleaned_text, max_tokens=context_limit)
        logger.info(f"  已分为 {len(text_chunks)} 段，逐段生成笔记")
    else:
        text_chunks = [cleaned_text]
        logger.info(f"  [OK] 文本长度适中（估算 {text_tokens} tokens）")

    # -------------------------------------------------------------------------
    # Step 9: 构建提示词并生成
    # -------------------------------------------------------------------------
    logger.info("构建提示词...")

    # 创建提示词加载器
    prompt_loader = get_prompt_loader()

    # 如果只有一段，正常构建提示词
    if len(text_chunks) == 1:
        messages = prompt_loader.build_messages(
            format_type=args.format,
            text=cleaned_text,
            vocab=vocab
        )
        logger.info(f"  [OK] 提示词构建完成")
        logger.info(f"    System prompt长度: {len(messages[0]['content'])} 字符")
        logger.info(f"    User prompt长度: {len(messages[1]['content'])} 字符")
    else:
        # 多段文本，先显示提示词概览
        logger.info(f"  [OK] 将逐段构建提示词，共 {len(text_chunks)} 段")
        messages = None  # 将在生成时逐段构建

    # 如果指定了--show-prompt，打印提示词结构
    if args.show_prompt and messages:
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
    # Step 9: 调用大模型生成笔记
    # -------------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("【Phase 4】调用大模型生成笔记...")
    logger.info("=" * 60)

    # 生成输出文件名
    output_path = generate_output_filename(input_path, args.format, output_dir)

    # 检查 dashscope 包是否安装
    if not HAS_DASHSCOPE:
        logger.error("错误: 未安装 dashscope 包，无法调用大模型")
        logger.error("请运行: pip install dashscope>=1.20.0")
        return EXIT_CONFIG_ERROR

    # 获取模型配置并创建客户端
    try:
        config = get_config()
        client_config = config.get_client_config(args.model)
        client = LLMClient(client_config)
        logger.info(f"模型配置: {client_config.model_name}")
    except RuntimeError as e:
        logger.error(f"错误: {e}")
        return EXIT_CONFIG_ERROR
    except Exception as e:
        logger.error(f"错误: 初始化 LLM 客户端失败 - {e}")
        return EXIT_CONFIG_ERROR

    # 生成笔记
    logger.info(f"生成参数: 温度={temperature}, 最大长度={args.max_length} ({max_tokens} tokens)")

    # 处理多段文本的生成
    if len(text_chunks) > 1:
        # 多段文本模式：逐段生成，然后合并
        return generate_multi_chunk(
            client, prompt_loader, text_chunks, vocab, args,
            temperature, max_tokens, output_path, logger
        )

    # 单段文本生成
    if args.preview:
        # 预览模式：流式输出到终端
        if args.no_stream:
            # 非流式模式
            logger.info("【生成中，按 Ctrl+C 可中断】\n")
            try:
                result = client.generate(messages, temperature=temperature, max_tokens=max_tokens)
                print("-" * 60)
                print(result.content)
                print("-" * 60)
                logger.info("\n[DONE] 预览完成（未保存文件）")
                logger.info(f"输入 Token: ~{result.input_tokens}, 输出 Token: ~{result.output_tokens}")
            except KeyboardInterrupt:
                logger.info("\n[DONE] 生成被中断")
        else:
            # 流式模式
            logger.info("【流式生成中，按 Ctrl+C 可中断】\n")
            print("-" * 60)

            generated_content = ""
            try:
                for chunk in client.generate_stream(messages, temperature=temperature, max_tokens=max_tokens):
                    print(chunk, end='', flush=True)
                    generated_content += chunk
                print("\n" + "-" * 60)
                logger.info("\n[DONE] 预览完成（未保存文件）")
            except KeyboardInterrupt:
                print("\n" + "-" * 60)
                logger.info("\n[DONE] 生成被中断（预览模式不保存）")
    else:
        # 文件模式：生成并保存到文件
        logger.info("正在生成笔记，请稍候...")
        logger.info("【按 Ctrl+C 可中断，已生成内容将保存为 .partial.md】")

        try:
            result = client.generate_to_file(
                messages, output_path,
                temperature=temperature,
                max_tokens=max_tokens,
                show_progress=True
            )

            # 显示生成统计
            logger.info("=" * 60)
            logger.info("[DONE] 笔记生成完成！")
            logger.info(f"输出文件: {output_path}")
            logger.info(f"输入 Token: ~{result.input_tokens}")
            logger.info(f"输出 Token: ~{result.output_tokens}")
            logger.info(f"生成时间: {result.generation_time:.2f}秒")

            if result.is_partial:
                logger.warning("⚠️ 注意: 生成被中断，结果为部分内容")
                logger.info(f"部分结果保存至: {output_path.with_suffix('.partial.md')}")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"错误: 生成笔记失败 - {e}")
            return EXIT_OUTPUT_ERROR

    return EXIT_SUCCESS


# =============================================================================
# 程序入口
# =============================================================================

if __name__ == "__main__":
    # 执行主函数并返回退出码给操作系统
    sys.exit(main())
