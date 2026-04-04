#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Text (V2T) - Whisper 转录模块 (transcriber.py)

【模块用途】
    负责加载 OpenAI Whisper 模型并执行语音识别转录。

    核心功能：
    1. 自动下载和缓存 Whisper 模型
    2. 加载模型到内存（支持 CPU/GPU）
    3. 执行音频文件转录
    4. 支持多语言和自动语言检测
    5. 标准化转录结果格式

【技术说明】
    - 使用 openai-whisper 官方库
    - 模型首次加载时自动下载到 ~/.cache/whisper/
    - 支持 5 种模型规模：tiny/base/small/medium/large
    - CPU 运行使用 fp16=False 提升稳定性

【模型信息】
    | 模型    | 大小   | 速度     | 准确度 | 适用场景       |
    |---------|--------|----------|--------|----------------|
    | tiny    | 39 MB  | 最快     | 一般   | 快速测试       |
    | base    | 74 MB  | 快       | 良好   | 日常使用（默认）|
    | small   | 244 MB | 中等     | 较好   | 质量优先       |
    | medium  | 769 MB | 较慢     | 好     | 高质量要求     |
    | large   | 1550 MB| 最慢     | 最好   | 专业用途       |

【依赖要求】
    - Python: openai-whisper, torch, numpy
    - 模型文件：自动下载，首次使用需网络连接

【使用示例】
    from transcriber import WhisperTranscriber

    # 创建转录器实例
    transcriber = WhisperTranscriber(model_name="base")

    # 加载模型（首次会下载）
    transcriber.load_model()

    # 执行转录
    result = transcriber.transcribe(Path("audio.wav"), language="zh")

    # 使用结果
    print(result["text"])           # 完整文本
    for seg in result["segments"]:  # 分段信息
        print(f"[{seg['start']:.2f}] {seg['text']}")
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

# Whisper 核心库
import whisper
import numpy as np

# 获取模块级日志记录器
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    【Whisper 转录器类】

    封装 Whisper 模型的加载和转录功能。

    【属性】
        model_name (str): 模型名称（tiny/base/small/medium/large）
        model (whisper.Model): 加载后的模型实例
        device (str): 运行设备（cpu/cuda）
        download_root (Optional[str]): 模型下载目录

    【设计原则】
        - 延迟加载：模型在首次 transcribe() 或显式 load_model() 时加载
        - 自动设备检测：有 GPU 用 GPU，否则 CPU
        - CPU 优化：自动禁用 fp16 提升稳定性
    """

    # 【支持的模型列表】与 Whisper 官方一致
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None,
        download_root: Optional[str] = None
    ):
        """
        【初始化转录器】

        【参数】
            model_name: 模型名称，默认 "base"
                       可选: tiny, base, small, medium, large
            device: 运行设备，None 表示自动检测
                   "cuda" 强制使用 GPU，"cpu" 强制使用 CPU
            download_root: 模型下载目录，默认使用 Whisper 缓存目录
                          通常为 ~/.cache/whisper/

        【异常】
            ValueError: 模型名称不支持

        【示例】
            # 默认配置
            transcriber = WhisperTranscriber()

            # 使用 small 模型，强制 CPU
            transcriber = WhisperTranscriber(
                model_name="small",
                device="cpu"
            )
        """
        # 【验证模型名称】
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"不支持的模型: {model_name}\n"
                f"支持的模型: {', '.join(self.SUPPORTED_MODELS)}"
            )

        self.model_name = model_name
        self.device = device or self._auto_select_device()
        self.download_root = download_root
        self.model: Optional[whisper.Whisper] = None

        logger.debug(
            f"转录器初始化: model={model_name}, device={self.device}"
        )

    def load_audio_with_ffmpeg(
        self,
        audio_path: Path,
        ffmpeg_path: str = "ffmpeg",
        sr: int = 16000
    ) -> np.ndarray:
        """
        【使用指定 FFmpeg 加载音频】

        【功能】
            使用指定的 FFmpeg 可执行文件加载音频，转换为 numpy 数组。
            这样可以让 Whisper 直接处理 numpy 数组，而不需要调用系统 FFmpeg。

        【参数】
            audio_path: 音频文件路径
            ffmpeg_path: FFmpeg 可执行文件路径
            sr: 目标采样率，默认 16000Hz

        【返回】
            np.ndarray: 音频波形数组，float32 类型，范围 [-1.0, 1.0]

        【异常】
            RuntimeError: FFmpeg 执行失败
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        cmd = [
            ffmpeg_path,
            "-nostdin",
            "-threads", "0",
            "-i", str(audio_path),
            "-f", "s16le",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-ar", str(sr),
            "-"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True
            )
            audio_data = np.frombuffer(result.stdout, np.int16)
            # 转换为 float32，范围 [-1.0, 1.0]
            return audio_data.flatten().astype(np.float32) / 32768.0
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "未知错误"
            raise RuntimeError(f"FFmpeg 加载音频失败: {stderr}") from e
        except Exception as e:
            raise RuntimeError(f"加载音频失败: {e}") from e

    def _auto_select_device(self) -> str:
        """
        【私有方法】自动选择运行设备

        【逻辑】
            1. 检查 PyTorch CUDA 是否可用
            2. 可用返回 "cuda"，否则返回 "cpu"

        【返回】
            str: "cuda" 或 "cpu"
        """
        try:
            import torch
            if torch.cuda.is_available():
                logger.debug("检测到 CUDA，使用 GPU 加速")
                return "cuda"
        except ImportError:
            pass

        logger.debug("未检测到 CUDA，使用 CPU")
        return "cpu"

    def load_model(self) -> None:
        """
        【加载 Whisper 模型】

        【功能】
            - 下载模型（如果本地不存在）
            - 加载模型到指定设备（CPU/GPU）
            - 首次下载可能需要几分钟，取决于网络速度

        【模型缓存位置】
            - Linux/macOS: ~/.cache/whisper/
            - Windows: %USERPROFILE%\.cache\whisper\

        【异常】
            RuntimeError: 模型加载失败

        【注意】
            - 此方法可重复调用，模型已加载时会跳过
            - 模型加载后会占用内存（base 模型约 150MB）
        """
        # 【避免重复加载】
        if self.model is not None:
            logger.debug("模型已加载，跳过")
            return

        logger.info(f"正在加载 Whisper 模型: {self.model_name}")
        logger.info(f"设备: {self.device}")

        # 【显示模型大小提示】
        model_size_mb = self.estimate_model_size(self.model_name)
        if model_size_mb > 0:
            logger.info(f"模型大小约: {model_size_mb} MB")

        try:
            # 【加载模型】
            # download_root: 指定模型下载/缓存目录
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
        audio_input: Union[Path, str, np.ndarray],
        language: Optional[str] = None,
        task: str = "transcribe",
        ffmpeg_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        【转录音频】

        【功能】
            使用 Whisper 模型将音频转换为文本。

        【参数】
            audio_input: 音频输入，可以是：
                        - 文件路径 (Path 或 str)
                        - numpy 数组 (已加载的音频数据)
            language: 语言代码，如 "zh", "en", "ja"
                     None 表示自动检测语言
            task: 任务类型
                 "transcribe" - 转录原语言（默认）
                 "translate"  - 翻译成英文
            ffmpeg_path: FFmpeg 可执行文件路径
                        如果提供且 audio_input 是路径，则使用此 FFmpeg 加载音频
            **kwargs: 额外参数传递给 whisper.transcribe()
                     如: temperature, best_of, beam_size 等

        【返回】
            dict: 标准化后的转录结果，包含：
                - text: 完整转录文本
                - language: 检测到的语言代码
                - segments: 段落列表，每个段落包含:
                    - id: 段落序号
                    - start: 开始时间（秒）
                    - end: 结束时间（秒）
                    - text: 段落文本
                    - confidence: 置信度（avg_logprob）

        【异常】
            RuntimeError: 转录失败
            FileNotFoundError: 音频文件不存在

        【示例】
            # 自动检测语言
            result = transcriber.transcribe(Path("audio.wav"))

            # 指定中文
            result = transcriber.transcribe(
                Path("audio.wav"),
                language="zh"
            )

            # 使用指定 FFmpeg 路径
            result = transcriber.transcribe(
                Path("audio.wav"),
                ffmpeg_path="./tools/ffmpeg.exe"
            )

            # 直接传入 numpy 数组
            audio_array = transcriber.load_audio_with_ffmpeg(Path("audio.wav"), "./tools/ffmpeg.exe")
            result = transcriber.transcribe(audio_array)
        """
        # 【处理输入类型】
        if isinstance(audio_input, (Path, str)):
            # 文件路径 - 需要使用 FFmpeg 加载
            audio_path = Path(audio_input)
            if not audio_path.exists():
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")

            # 如果提供了 ffmpeg_path，使用它加载音频
            if ffmpeg_path:
                logger.debug(f"使用指定 FFmpeg 加载音频: {ffmpeg_path}")
                audio_data = self.load_audio_with_ffmpeg(audio_path, ffmpeg_path)
            else:
                # 没有提供 ffmpeg_path，让 Whisper 自己处理（会找系统 PATH）
                audio_data = str(audio_path)

            logger.info(f"开始转录: {audio_path.name}")
        elif isinstance(audio_input, np.ndarray):
            # 已经是 numpy 数组
            audio_data = audio_input
            logger.info(f"开始转录: numpy 数组 (长度={len(audio_input)})")
        else:
            raise TypeError(f"不支持的音频输入类型: {type(audio_input)}")

        # 【确保模型已加载】
        if self.model is None:
            self.load_model()

        # 【准备转录参数】
        # fp16: 半精度浮点，GPU 可用，CPU 建议关闭
        use_fp16 = (self.device == "cuda")

        # 【显示语言设置】
        if language:
            logger.info(f"指定语言: {language}")
        else:
            logger.info("语言: 自动检测")

        try:
            # 【执行转录】
            # 这是核心 Whisper API 调用
            # audio_data 可以是文件路径(str)或 numpy 数组
            result = self.model.transcribe(
                audio_data,
                language=language,
                task=task,
                fp16=use_fp16,
                verbose=False,  # 使用我们的日志系统
                **kwargs
            )

            # 【标准化结果格式】
            formatted_result = self._format_result(result)

            # 【输出统计信息】
            num_segments = len(formatted_result["segments"])
            detected_lang = formatted_result["language"]
            logger.info(f"转录完成: 检测到语言={detected_lang}")
            logger.info(f"  总段落数: {num_segments}")

            return formatted_result

        except Exception as e:
            raise RuntimeError(f"转录失败: {e}")

    def _format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        【私有方法】标准化转录结果格式

        【目的】
            将 Whisper 原始输出转换为统一的内部格式，
            便于后续处理和输出模块使用。

        【输入格式】
            Whisper 原始结果包含：
            - text: 完整文本
            - language: 检测到的语言
            - segments: 原始段落列表

        【输出格式】
            标准化的字典，字段更友好
        """
        formatted = {
            "text": result.get("text", "").strip(),
            "language": result.get("language", "unknown"),
            "segments": []
        }

        # 【处理每个段落】
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
        【获取当前模型信息】

        【返回】
            dict: 包含模型名称、设备、加载状态等信息

        【示例】
            info = transcriber.get_model_info()
            print(f"模型: {info['model_name']}")
            print(f"设备: {info['device']}")
            print(f"已加载: {info['loaded']}")
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "loaded": self.model is not None,
        }

        # 【尝试获取模型维度信息】
        if self.model is not None and hasattr(self.model, 'dims'):
            try:
                info["dims"] = self.model.dims.__dict__
            except Exception:
                pass

        return info

    @staticmethod
    def list_supported_languages() -> Dict[str, str]:
        """
        【静态方法】获取支持的语言列表

        【返回】
            dict: 语言代码到语言名称的映射
                  如: {"zh": "chinese", "en": "english", ...}

        【示例】
            languages = WhisperTranscriber.list_supported_languages()
            for code, name in sorted(languages.items()):
                print(f"{code}: {name}")
        """
        return whisper.tokenizer.LANGUAGES

    @classmethod
    def get_available_models(cls) -> List[str]:
        """
        【类方法】获取可用模型列表

        【返回】
            list: 支持的模型名称列表

        【示例】
            models = WhisperTranscriber.get_available_models()
            print(f"可用模型: {', '.join(models)}")
        """
        return cls.SUPPORTED_MODELS.copy()

    @classmethod
    def estimate_model_size(cls, model_name: str) -> int:
        """
        【类方法】估算模型大小

        【参数】
            model_name: 模型名称

        【返回】
            int: 模型大小（MB），未知模型返回 0

        【说明】
            这是近似值，实际下载大小可能略有差异
        """
        sizes = {
            "tiny": 39,
            "base": 74,
            "small": 244,
            "medium": 769,
            "large": 1550
        }
        return sizes.get(model_name, 0)
