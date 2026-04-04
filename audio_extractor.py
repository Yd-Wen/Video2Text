#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2Text (V2T) - 音频提取模块 (audio_extractor.py)

【模块用途】
    负责从视频文件中提取音频并转换为 Whisper 模型要求的格式。

    核心功能：
    1. 检测系统 FFmpeg 安装并验证可用性
    2. 从视频文件提取音频流
    3. 重采样为 16kHz 单声道 16bit PCM 格式
    4. 管理临时音频文件生命周期

【技术说明】
    - 使用 ffmpeg-python 库调用 FFmpeg
    - 输出格式严格遵循 Whisper 要求：16kHz、16bit、单声道 WAV
    - 临时文件使用 Python tempfile 模块管理，确保安全清理

【依赖要求】
    - 系统必须安装 FFmpeg（4.0+ 版本）
    - Python 依赖：ffmpeg-python

【使用示例】
    from audio_extractor import AudioExtractor

    extractor = AudioExtractor()  # 自动检测 FFmpeg
    audio_path = extractor.extract(Path("video.mp4"))
    # 使用音频文件...
    # 临时文件在不再需要时应由调用方删除
"""

import os
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

# 导入 ffmpeg-python 用于构建 FFmpeg 命令
import ffmpeg

# 获取模块级日志记录器
logger = logging.getLogger(__name__)


class AudioExtractor:
    """
    【音频提取器类】

    封装从视频提取音频的完整流程，包括 FFmpeg 验证、音频提取、格式转换。

    【属性】
        ffmpeg_path (str): FFmpeg 可执行文件路径
        sample_rate (int): 输出音频采样率（Whisper 要求 16kHz）
        channels (int): 输出音频声道数（Whisper 要求单声道）
        sample_fmt (str): 采样格式（16bit PCM）

    【设计原则】
        - 延迟验证：FFmpeg 检测在初始化时进行，快速失败
        - 格式标准化：强制使用 Whisper 要求的音频参数
        - 临时文件管理：使用 tempfile 确保文件安全创建
    """

    # 【Whisper 模型要求的音频参数】
    # 这些参数是 OpenAI Whisper 模型的硬性要求，不可修改
    REQUIRED_SAMPLE_RATE = 16000  # 16kHz 采样率
    REQUIRED_CHANNELS = 1         # 单声道（mono）
    REQUIRED_SAMPLE_FMT = "s16"   # 16bit 有符号整数 PCM

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        sample_rate: int = 16000,
        channels: int = 1
    ):
        """
        【初始化音频提取器】

        【参数】
            ffmpeg_path: FFmpeg 可执行文件路径，默认 "ffmpeg"（使用系统 PATH）
            sample_rate: 输出采样率，默认 16000Hz（Whisper 要求）
            channels: 输出声道数，默认 1（单声道）

        【异常】
            RuntimeError: FFmpeg 未安装或不可执行

        【示例】
            # 使用系统 PATH 中的 FFmpeg
            extractor = AudioExtractor()

            # 指定 FFmpeg 路径（Windows 示例）
            extractor = AudioExtractor(ffmpeg_path="C:/ffmpeg/bin/ffmpeg.exe")
        """
        self.ffmpeg_path = ffmpeg_path
        self.sample_rate = sample_rate
        self.channels = channels

        # 【初始化时验证 FFmpeg 可用性】
        # 快速失败原则：在构造时就检测，避免在提取时才发现问题
        self._validate_ffmpeg()

    def _validate_ffmpeg(self) -> None:
        """
        【私有方法】验证 FFmpeg 是否可用

        【验证方式】
            1. 尝试执行 `ffmpeg -version` 命令
            2. 检查返回码和输出内容

        【异常】
            RuntimeError: FFmpeg 未找到或无法执行，包含安装提示

        【设计说明】
            使用 subprocess 直接调用而非 ffmpeg-python，
            避免在验证阶段引入额外的抽象层问题
        """
        try:
            # 执行 ffmpeg -version 命令，5秒超时防止卡死
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,      # 捕获 stdout/stderr
                text=True,                # 以文本而非字节返回
                timeout=5,                # 5秒超时
                encoding='utf-8',         # 明确编码
                errors='ignore'           # 忽略解码错误
            )

            # 检查返回码：0 表示成功
            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg 返回错误码 {result.returncode}"
                )

            # 提取版本信息（第一行通常包含版本号）
            version_line = result.stdout.split('\n')[0] if result.stdout else "未知版本"
            logger.debug(f"FFmpeg 验证通过: {version_line}")

        except FileNotFoundError:
            # FFmpeg 可执行文件未找到
            raise RuntimeError(
                f"FFmpeg 未找到: {self.ffmpeg_path}\n\n"
                "请安装 FFmpeg 并确保其在系统 PATH 中，或指定 --ffmpeg-path 参数\n\n"
                "【安装指南】\n"
                "  Windows:   choco install ffmpeg\n"
                "             或从 https://ffmpeg.org/download.html 下载\n"
                "  macOS:     brew install ffmpeg\n"
                "  Ubuntu:    sudo apt update && sudo apt install ffmpeg\n"
                "  CentOS:    sudo yum install ffmpeg"
            )

        except subprocess.TimeoutExpired:
            # 命令执行超时
            raise RuntimeError(
                f"FFmpeg 验证超时（>{5}秒），请检查 FFmpeg 安装状态"
            )

        except Exception as e:
            # 其他异常
            raise RuntimeError(f"FFmpeg 验证失败: {e}")

    def extract(
        self,
        video_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        【从视频文件提取音频】

        【功能】
            从指定视频文件提取音频，转换为 16kHz/16bit/单声道 WAV 格式。

        【参数】
            video_path: 输入视频文件路径（Path 对象）
            output_path: 输出音频文件路径（可选）
                        - 提供：保存到指定位置
                        - 省略：创建临时文件，返回路径

        【返回】
            Path: 提取的 WAV 音频文件路径

        【异常】
            FileNotFoundError: 视频文件不存在
            RuntimeError: FFmpeg 处理失败，包含错误详情

        【示例】
            # 提取到临时文件
            audio_path = extractor.extract(Path("video.mp4"))
            # 处理完成后记得删除临时文件

            # 提取到指定路径
            audio_path = extractor.extract(
                Path("video.mp4"),
                Path("output/audio.wav")
            )
        """
        video_path = Path(video_path)

        # 【前置验证】确保输入文件存在
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 【确定输出路径】
        if output_path is None:
            # 创建临时文件
            # suffix: 文件扩展名
            # delete=False: 关闭后不自动删除（我们需要在转录后使用）
            # prefix: 文件名前缀，便于识别
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                prefix="v2t_audio_"
            )
            output_path = Path(temp_file.name)
            temp_file.close()  # 立即关闭，FFmpeg 将覆盖此文件
        else:
            output_path = Path(output_path)
            # 【自动创建输出目录】确保父目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"开始提取音频: {video_path.name}")
        logger.debug(f"  输出: {output_path}")
        logger.debug(f"  格式: {self.sample_rate}Hz, {self.channels}ch, 16bit PCM")

        try:
            # 【构建 FFmpeg 处理流程】
            # 使用 ffmpeg-python 的流式 API 构建命令

            # Step 1: 定义输入
            input_stream = ffmpeg.input(str(video_path))

            # Step 2: 定义音频输出参数
            output_stream = ffmpeg.output(
                input_stream.audio,       # 只取音频流
                str(output_path),         # 输出文件路径
                ar=self.sample_rate,      # 采样率 (audio rate)
                ac=self.channels,         # 声道数 (audio channels)
                sample_fmt=self.REQUIRED_SAMPLE_FMT,  # 采样格式
                vn=True,                  # 禁用视频输出 (no video)
                y=True                    # 覆盖已存在文件 (yes)
            )

            # Step 3: 执行 FFmpeg 命令
            # overwrite_output=True: 等价于 -y 参数
            # quiet=True: 禁用 FFmpeg 的终端输出，使用我们的日志系统
            ffmpeg.run(
                output_stream,
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            # 【验证输出结果】
            if not output_path.exists():
                raise RuntimeError("FFmpeg 执行成功但输出文件不存在")

            file_size = output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError("FFmpeg 输出文件为空")

            logger.debug(f"音频提取成功: {file_size / 1024 / 1024:.2f} MB")
            return output_path

        except ffmpeg.Error as e:
            # 【FFmpeg 执行错误处理】
            # 尝试从 stderr 提取可读的错误信息
            error_msg = self._parse_ffmpeg_error(e)

            # 【清理失败产生的残留文件】
            self._safe_remove(output_path)

            raise RuntimeError(f"FFmpeg 处理失败: {error_msg}")

        except Exception as e:
            # 【其他异常处理】
            self._safe_remove(output_path)
            raise RuntimeError(f"音频提取失败: {e}")

    def _parse_ffmpeg_error(self, error: ffmpeg.Error) -> str:
        """
        【私有方法】解析 FFmpeg 错误信息

        【参数】
            error: ffmpeg.Error 异常对象

        【返回】
            str: 人类可读的错误描述
        """
        # ffmpeg-python 的错误通常包含 stderr 属性
        if hasattr(error, 'stderr') and error.stderr:
            try:
                # 尝试解码错误输出
                stderr = error.stderr.decode('utf-8', errors='ignore')
                # 提取最后一行（通常包含关键错误信息）
                lines = [line.strip() for line in stderr.split('\n') if line.strip()]
                if lines:
                    # 返回最后几行，通常包含关键错误
                    return ' | '.join(lines[-3:])
            except Exception:
                pass

        # 返回默认错误信息
        return str(error)

    def _safe_remove(self, file_path: Path) -> None:
        """
        【私有方法】安全删除文件（忽略错误）

        【用途】
            在异常处理中清理残留文件，即使删除失败也不抛出异常
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.debug(f"已清理残留文件: {path}")
        except Exception:
            pass  # 静默忽略删除失败

    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """
        【获取视频文件信息】

        【功能】
            使用 ffprobe 探测视频文件的元数据。

        【参数】
            video_path: 视频文件路径

        【返回】
            dict: 包含视频信息的字典，可能包含：
                - filename: 文件名
                - format: 容器格式
                - duration: 时长（秒）
                - size: 文件大小（字节）
                - bit_rate: 总码率
                - width/height: 视频分辨率
                - fps: 视频帧率
                - audio_codec: 音频编码
                - audio_sample_rate: 音频采样率
                - audio_channels: 音频声道数

        【异常】
            FileNotFoundError: 视频文件不存在
            RuntimeError: 无法解析视频信息

        【示例】
            info = extractor.get_video_info(Path("video.mp4"))
            print(f"视频时长: {info['duration']} 秒")
            print(f"分辨率: {info['width']}x{info['height']}")
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        try:
            # 使用 ffprobe 探测文件（ffmpeg-python 封装）
            probe = ffmpeg.probe(str(video_path))

            # 提取容器格式信息
            format_info = probe.get("format", {})

            # 【构建基础信息】
            info: Dict[str, Any] = {
                "filename": video_path.name,
                "format": format_info.get("format_name", "unknown"),
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bit_rate": int(format_info.get("bit_rate", 0)),
            }

            # 【提取视频流信息】
            video_streams = [
                s for s in probe.get("streams", [])
                if s.get("codec_type") == "video"
            ]
            if video_streams:
                v = video_streams[0]
                info.update({
                    "width": v.get("width"),
                    "height": v.get("height"),
                    # r_frame_rate 通常是 "30/1" 或 "30000/1001" 格式
                    "fps": self._parse_fps(v.get("r_frame_rate", "0/1")),
                    "video_codec": v.get("codec_name"),
                })

            # 【提取音频流信息】
            audio_streams = [
                s for s in probe.get("streams", [])
                if s.get("codec_type") == "audio"
            ]
            if audio_streams:
                a = audio_streams[0]
                info.update({
                    "audio_codec": a.get("codec_name"),
                    "audio_sample_rate": int(a.get("sample_rate", 0)),
                    "audio_channels": a.get("channels"),
                })

            return info

        except ffmpeg.Error as e:
            error_msg = self._parse_ffmpeg_error(e)
            raise RuntimeError(f"无法解析视频信息: {error_msg}")

        except Exception as e:
            raise RuntimeError(f"获取视频信息失败: {e}")

    def _parse_fps(self, fps_str: str) -> float:
        """
        【私有方法】解析帧率字符串

        【参数】
            fps_str: 形如 "30/1" 或 "30000/1001" 的帧率字符串

        【返回】
            float: 帧率数值
        """
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
