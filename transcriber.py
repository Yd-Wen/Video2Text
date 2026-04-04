#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper转录模块

功能:
    - 加载和管理Whisper模型
    - 执行语音识别转录
    - 支持多语言和自动语言检测

设计说明:
    - 延迟加载模型（首次使用时下载和加载）
    - 模型缓存于 ~/.cache/whisper/ 目录
    - 支持CPU运行（无需GPU）
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import whisper
import numpy as np

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Whisper转录器类

    负责加载Whisper模型并执行语音转录。

    Attributes:
        model_name (str): 模型名称（tiny/base/small/medium/large）
        model (whisper.Model): 加载后的模型实例
        device (str): 运行设备（cpu/cuda）

    模型大小参考:
        - tiny:  39MB, 最快, 准确度一般
        - base:  74MB, 快速, 准确度良好（默认）
        - small: 244MB, 中等速度, 准确度较好
        - medium: 769MB, 较慢, 准确度好
        - large: 1550MB, 最慢, 准确度最佳
    """

    # 支持的模型列表
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None,
        download_root: Optional[str] = None
    ):
        """
        初始化转录器

        Args:
            model_name: 模型名称，默认"base"
            device: 运行设备，None表示自动选择（有GPU用GPU，否则CPU）
            download_root: 模型下载目录，默认使用whisper的默认缓存目录

        Raises:
            ValueError: 模型名称不支持
        """
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"不支持的模型: {model_name}\n"
                f"支持的模型: {', '.join(self.SUPPORTED_MODELS)}"
            )

        self.model_name = model_name
        self.device = device or ("cuda" if self._check_cuda() else "cpu")
        self.download_root = download_root
        self.model: Optional[whisper.Whisper] = None

        logger.debug(f"转录器初始化: model={model_name}, device={self.device}")

    def _check_cuda(self) -> bool:
        """
        检查CUDA是否可用

        Returns:
            bool: True if CUDA is available
        """
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self) -> None:
        """
        加载Whisper模型

        说明:
            - 首次加载时会自动下载模型文件
            - 模型缓存于 ~/.cache/whisper/ 目录
            - 下载进度会显示在终端

        Raises:
            RuntimeError: 模型加载失败
        """
        if self.model is not None:
            logger.debug("模型已加载，跳过")
            return

        logger.info(f"正在加载Whisper模型: {self.model_name}")
        logger.info(f"设备: {self.device}")

        try:
            # 加载模型
            # fp16=False 在CPU上更稳定，虽然速度稍慢
            self.model = whisper.load_model(
                self.model_name,
                device=self.device,
                download_root=self.download_root
            )

            logger.info(f"模型加载完成: {self.model_name}")

        except Exception as e:
            raise RuntimeError(f"模型加载失败: {e}")

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe",
        **kwargs
    ) -> Dict[str, Any]:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径（WAV格式）
            language: 语言代码，如"zh", "en", "ja"等。None表示自动检测
            task: 任务类型，"transcribe"（转录）或"translate"（翻译成英文）
            **kwargs: 额外的转录参数传递给whisper

        Returns:
            dict: 转录结果，包含以下关键字段:
                - text: 完整转录文本
                - segments: 段落列表，每个包含:
                    - id: 段落ID
                    - start: 开始时间（秒）
                    - end: 结束时间（秒）
                    - text: 段落文本
                    - confidence: 置信度（avg_logprob）
                - language: 检测到的语言代码

        Raises:
            RuntimeError: 转录失败
            FileNotFoundError: 音频文件不存在
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 确保模型已加载
        if self.model is None:
            self.load_model()

        logger.info(f"开始转录: {audio_path.name}")

        try:
            # 执行转录
            # fp16=False 在CPU上运行更稳定
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                task=task,
                fp16=(self.device == "cuda"),  # 只在GPU上使用fp16
                verbose=False,  # 我们使用日志系统，禁用whisper的进度输出
                **kwargs
            )

            # 标准化结果格式
            formatted_result = self._format_result(result)

            logger.info(f"转录完成: 检测到语言={formatted_result['language']}")
            logger.info(f"  总段落数: {len(formatted_result['segments'])}")

            return formatted_result

        except Exception as e:
            raise RuntimeError(f"转录失败: {e}")

    def _format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化转录结果格式

        Args:
            result: Whisper原始输出

        Returns:
            dict: 标准化后的结果
        """
        formatted = {
            "text": result.get("text", "").strip(),
            "language": result.get("language", "unknown"),
            "segments": []
        }

        # 处理段落信息
        for seg in result.get("segments", []):
            formatted_segment = {
                "id": seg.get("id", 0),
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": seg.get("text", "").strip(),
                "confidence": seg.get("avg_logprob", 0.0),
            }
            formatted["segments"].append(formatted_segment)

        return formatted

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息

        Returns:
            dict: 模型信息字典
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "loaded": self.model is not None,
        }

        if self.model is not None:
            # 尝试获取模型维度信息
            try:
                info["dims"] = self.model.dims.__dict__ if hasattr(self.model, 'dims') else None
            except:
                pass

        return info

    @staticmethod
    def list_supported_languages() -> Dict[str, str]:
        """
        获取支持的语言列表

        Returns:
            dict: 语言代码到语言名称的映射
        """
        return whisper.tokenizer.LANGUAGES

    @classmethod
    def get_available_models(cls) -> List[str]:
        """
        获取可用模型列表

        Returns:
            list: 模型名称列表
        """
        return cls.SUPPORTED_MODELS.copy()

    @classmethod
    def estimate_model_size(cls, model_name: str) -> float:
        """
        估算模型大小

        Args:
            model_name: 模型名称

        Returns:
            float: 模型大小（MB）
        """
        sizes = {
            "tiny": 39,
            "base": 74,
            "small": 244,
            "medium": 769,
            "large": 1550
        }
        return sizes.get(model_name, 0)
