#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Client - 大模型调用客户端 (DashScope 版本)

统一封装 DashScope (通义千问) 的 API 调用，支持：
- 流式响应处理，实时写入文件
- 超时重试机制（3次指数退避）
- Token 估算预警
- Ctrl+C 中断处理，保存为 .partial.md

【依赖】
    pip install dashscope>=1.20.0

【使用示例】
    from llm_client import LLMClient
    from config import get_config

    config = get_config().get_client_config("qwen")
    client = LLMClient(config)

    messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"}
    ]

    # 流式生成
    for chunk in client.generate_stream(messages):
        print(chunk, end='', flush=True)

    # 或保存到文件
    client.generate_to_file(messages, Path("output.md"))
"""

import sys
import time
import signal
import logging
from pathlib import Path
from typing import Iterator, Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入 dashscope
try:
    import dashscope
    from dashscope import Generation
    from dashscope.api_entities.dashscope_response import GenerationResponse
    HAS_DASHSCOPE = True
except ImportError:
    HAS_DASHSCOPE = False
    logger.warning("未安装 dashscope 包，LLM 功能不可用。运行: pip install dashscope>=1.20.0")

from config import ModelConfig, get_config


# =============================================================================
# 常量配置
# =============================================================================

# 重试配置
MAX_RETRIES = 3                  # 最大重试次数
RETRY_DELAY_BASE = 1.0           # 基础重试延迟（秒）
RETRY_DELAY_MAX = 30.0           # 最大重试延迟（秒）

# Token 预警阈值
TOKEN_WARNING_THRESHOLD = 32000  # 输入超过此值时警告

# 流式响应配置
STREAM_TIMEOUT = 300             # 流式响应超时（秒）
CHUNK_TIMEOUT = 60               # 单个 chunk 超时（秒）

# DashScope 错误码（需要重试的）
RETRY_ERROR_CODES = [
    'Throttling',           # 限流
    'ServiceUnavailable',   # 服务不可用
    'InternalError',        # 内部错误
    'Timeout',              # 超时
]


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class GenerationResult:
    """生成结果数据结构"""
    content: str                   # 生成的完整内容
    input_tokens: int              # 输入 token 数（估算）
    output_tokens: int             # 输出 token 数（估算）
    generation_time: float         # 生成耗时（秒）
    is_partial: bool               # 是否为部分结果（中断导致）
    interrupt_reason: Optional[str] = None  # 中断原因


@dataclass
class GenerationProgress:
    """生成进度数据结构"""
    chunk: str                     # 当前 chunk 内容
    total_content: str             # 累计内容
    chunk_number: int              # chunk 序号
    elapsed_time: float            # 已用时间


# =============================================================================
# Token 估算器
# =============================================================================

class TokenEstimator:
    """
    Token 估算器

    用于估算输入文本的 token 数量，超出阈值时发出警告。
    """

    # 中文字符平均 token 数（经验值）
    CHARS_PER_TOKEN_ZH = 1.5
    # 英文单词平均 token 数
    WORDS_PER_TOKEN_EN = 0.75

    @classmethod
    def estimate(cls, text: str) -> int:
        """
        估算文本的 token 数量

        【参数】
            text: 输入文本

        【返回】
            int: 估算的 token 数
        """
        # 粗略估算：中文字符 + 英文单词
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        estimated = int(chinese_chars / cls.CHARS_PER_TOKEN_ZH +
                       other_chars / cls.WORDS_PER_TOKEN_EN)
        return max(1, estimated)

    @classmethod
    def check_warning(cls, text: str, threshold: int = TOKEN_WARNING_THRESHOLD) -> bool:
        """
        检查是否需要发出 token 预警

        【参数】
            text: 输入文本
            threshold: 预警阈值

        【返回】
            bool: 是否超过阈值
        """
        estimated = cls.estimate(text)
        if estimated > threshold:
            logger.warning(
                f"⚠️ 输入文本较长（估算约 {estimated} tokens），"
                f"可能接近或超出模型上下文限制（{threshold}）"
            )
            return True
        return False


# =============================================================================
# LLM 客户端
# =============================================================================

class LLMClient:
    """
    大模型调用客户端 (DashScope 版本)

    封装 DashScope API 调用，支持流式响应和错误处理。
    """

    def __init__(self, config: ModelConfig):
        """
        初始化 LLM 客户端

        【参数】
            config: 模型配置（来自 Config.get_client_config）

        【异常】
            RuntimeError: dashscope 包未安装
        """
        if not HAS_DASHSCOPE:
            raise RuntimeError(
                "未安装 dashscope 包。请运行: pip install dashscope>=1.20.0"
            )

        self.config = config
        dashscope.api_key = config.api_key

        # 中断标志
        self._interrupted = False
        self._current_generation = False

        # 注册信号处理
        self._setup_signal_handler()

        logger.info(f"LLMClient 初始化完成: {config.model_name}")

    def _setup_signal_handler(self) -> None:
        """
        设置信号处理器（用于捕获 Ctrl+C）

        注意：Windows 和 Unix 的信号处理略有不同。
        """
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # 在非主线程中无法设置信号处理器
            pass

    def _signal_handler(self, signum, frame) -> None:
        """
        信号处理器

        设置中断标志，让生成循环可以优雅退出。
        """
        logger.info("收到中断信号，准备停止生成...")
        self._interrupted = True

        # 如果当前正在生成，不立即退出，让生成循环处理
        if self._current_generation:
            logger.info("正在保存已生成内容...")
        else:
            sys.exit(0)

    def _create_chat_completion(self, messages: List[Dict[str, str]],
                                 temperature: Optional[float] = None,
                                 max_tokens: Optional[int] = None,
                                 stream: bool = True):
        """
        创建聊天完成请求

        【参数】
            messages: 消息列表
            temperature: 温度参数（覆盖默认值）
            max_tokens: 最大 token 数（覆盖默认值）
            stream: 是否使用流式响应

        【返回】
            流式响应迭代器或完整响应
        """
        response = Generation.call(
            model=self.config.model_name,
            messages=messages,
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
            result_format='message',
            stream=stream,
        )
        return response

    def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        带指数退避的重试机制

        【参数】
            func: 要执行的函数
            *args, **kwargs: 函数参数

        【返回】
            Any: 函数执行结果

        【异常】
            重试耗尽后抛出最后一次异常
        """
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_code = getattr(e, 'code', None)
                error_message = str(e)

                # 判断是否可重试
                should_retry = (
                    error_code in RETRY_ERROR_CODES or
                    'throttling' in error_message.lower() or
                    'timeout' in error_message.lower() or
                    'service unavailable' in error_message.lower()
                )

                if should_retry and attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
                    logger.warning(f"API 错误，{delay:.1f}秒后重试 ({attempt + 1}/{MAX_RETRIES})...")
                    time.sleep(delay)
                else:
                    # 不可重试的错误或重试耗尽
                    raise

        # 重试耗尽
        raise last_exception

    def generate_stream(self, messages: List[Dict[str, str]],
                        temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None,
                        progress_callback: Optional[Callable[[GenerationProgress], None]] = None
                        ) -> Iterator[str]:
        """
        流式生成内容

        【参数】
            messages: 消息列表（OpenAI 格式）
            temperature: 温度参数
            max_tokens: 最大 token 数
            progress_callback: 进度回调函数

        【返回】
            Iterator[str]: 内容块迭代器

        【使用示例】
            for chunk in client.generate_stream(messages):
                print(chunk, end='', flush=True)
        """
        if not messages:
            raise ValueError("messages 不能为空")

        # 估算输入 token 并检查
        all_content = "\n".join(m.get("content", "") for m in messages)
        TokenEstimator.check_warning(all_content)

        self._current_generation = True
        self._interrupted = False
        start_time = time.time()
        chunk_count = 0
        accumulated_content = ""

        try:
            # 使用重试机制获取响应
            response = self._retry_with_backoff(
                self._create_chat_completion,
                messages,
                temperature,
                max_tokens,
                stream=True
            )

            for chunk in response:
                # 检查中断
                if self._interrupted:
                    logger.info("生成被用户中断")
                    break

                # 处理流式响应
                if hasattr(chunk, 'output') and chunk.output:
                    # 获取 choices
                    choices = chunk.output.get('choices', [])
                    if choices:
                        delta = choices[0].get('message', {})
                        content = delta.get('content', '')

                        if content:
                            chunk_count += 1
                            accumulated_content += content

                            # 调用进度回调
                            if progress_callback:
                                progress = GenerationProgress(
                                    chunk=content,
                                    total_content=accumulated_content,
                                    chunk_number=chunk_count,
                                    elapsed_time=time.time() - start_time
                                )
                                progress_callback(progress)

                            yield content

        except Exception as e:
            logger.error(f"生成过程出错: {e}")
            raise
        finally:
            self._current_generation = False

    def generate(self, messages: List[Dict[str, str]],
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> GenerationResult:
        """
        生成完整内容（非流式）

        【参数】
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        【返回】
            GenerationResult: 生成结果
        """
        start_time = time.time()
        chunks = []

        for chunk in self.generate_stream(messages, temperature, max_tokens):
            chunks.append(chunk)

        content = "".join(chunks)
        elapsed = time.time() - start_time

        # 估算 token 数
        input_tokens = TokenEstimator.estimate(
            "\n".join(m.get("content", "") for m in messages)
        )
        output_tokens = TokenEstimator.estimate(content)

        return GenerationResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            generation_time=elapsed,
            is_partial=self._interrupted,
            interrupt_reason="用户中断" if self._interrupted else None
        )

    def generate_to_file(self, messages: List[Dict[str, str]],
                         output_path: Path,
                         temperature: Optional[float] = None,
                         max_tokens: Optional[int] = None,
                         show_progress: bool = True) -> GenerationResult:
        """
        生成内容并写入文件（支持中断恢复）

        【参数】
            messages: 消息列表
            output_path: 输出文件路径
            temperature: 温度参数
            max_tokens: 最大 token 数
            show_progress: 是否显示进度

        【返回】
            GenerationResult: 生成结果

        【说明】
            如果用户按 Ctrl+C 中断，已生成内容会保存为 .partial.md 文件。
        """
        start_time = time.time()
        output_path = Path(output_path)

        # 创建临时文件路径
        temp_path = output_path.with_suffix('.partial.md')

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        chunks = []
        chunk_count = 0
        last_log_time = start_time

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                for chunk in self.generate_stream(messages, temperature, max_tokens):
                    f.write(chunk)
                    f.flush()  # 立即刷新到磁盘
                    chunks.append(chunk)
                    chunk_count += 1

                    # 显示进度
                    if show_progress and chunk_count % 10 == 0:
                        now = time.time()
                        if now - last_log_time >= 1.0:  # 每秒最多更新一次
                            elapsed = now - start_time
                            logger.info(f"生成中... 已生成 {chunk_count} 块，用时 {elapsed:.1f}秒")
                            last_log_time = now

            # 生成完成，重命名为正式文件
            content = "".join(chunks)

            if self._interrupted:
                # 中断状态，保留 .partial.md 后缀
                final_path = temp_path
                logger.info(f"生成被中断，部分结果已保存: {final_path}")
            else:
                # 正常完成，重命名为正式文件
                if temp_path.exists():
                    # 如果目标文件已存在，先删除
                    if output_path.exists():
                        output_path.unlink()
                    temp_path.rename(output_path)
                final_path = output_path
                logger.info(f"生成完成，结果已保存: {final_path}")

            elapsed = time.time() - start_time
            input_tokens = TokenEstimator.estimate(
                "\n".join(m.get("content", "") for m in messages)
            )
            output_tokens = TokenEstimator.estimate(content)

            return GenerationResult(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                generation_time=elapsed,
                is_partial=self._interrupted,
                interrupt_reason="用户中断" if self._interrupted else None
            )

        except Exception as e:
            # 发生错误，尝试保存已生成的内容
            if chunks:
                try:
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.write("".join(chunks))
                    logger.info(f"错误发生时，已保存部分结果: {temp_path}")
                except Exception as save_error:
                    logger.error(f"保存部分结果失败: {save_error}")
            raise

    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        估算消息列表的 token 数量

        【参数】
            messages: 消息列表

        【返回】
            int: 估算的 token 数
        """
        all_content = "\n".join(m.get("content", "") for m in messages)
        return TokenEstimator.estimate(all_content)


# =============================================================================
# 便捷函数
# =============================================================================

def create_client(model: str) -> LLMClient:
    """
    创建指定模型的 LLM 客户端

    【参数】
        model: 模型名称（qwen/qwen-plus/qwen-max 等）

    【返回】
        LLMClient: 客户端实例
    """
    config = get_config().get_client_config(model)
    return LLMClient(config)


def quick_generate(messages: List[Dict[str, str]],
                   model: str = "qwen",
                   output_file: Optional[Path] = None) -> str:
    """
    快速生成内容（便捷函数）

    【参数】
        messages: 消息列表
        model: 模型名称
        output_file: 输出文件路径（可选）

    【返回】
        str: 生成的内容
    """
    client = create_client(model)

    if output_file:
        result = client.generate_to_file(messages, output_file)
    else:
        result = client.generate(messages)

    return result.content
