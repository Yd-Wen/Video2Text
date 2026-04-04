#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频提取模块

功能:
    - 使用FFmpeg从视频文件提取音频
    - 转换为Whisper要求的格式（16kHz, 16bit, 单声道WAV）
    - 提供进度显示和错误处理

设计说明:
    - 使用ffmpeg-python库调用FFmpeg
    - 生成临时WAV文件，供Whisper处理
    - 16kHz采样率是Whisper模型的强制要求
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

import ffmpeg

logger = logging.getLogger(__name__)


class AudioExtractor:
    """
    音频提取器类

    负责从视频文件中提取音频并转换为Whisper兼容的格式。

    Attributes:
        ffmpeg_path (str): FFmpeg可执行文件路径
        sample_rate (int): 输出音频采样率（Whisper要求16kHz）
        channels (int): 输出音频声道数（Whisper要求单声道）
        sample_fmt (str): 采样格式（16bit PCM）
    """

    # Whisper模型要求的音频参数
    REQUIRED_SAMPLE_RATE = 16000  # 16kHz
    REQUIRED_CHANNELS = 1         # 单声道
    REQUIRED_SAMPLE_FMT = "s16"   # 16bit有符号整数

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        sample_rate: int = 16000,
        channels: int = 1
    ):
        """
        初始化音频提取器

        Args:
            ffmpeg_path: FFmpeg可执行文件路径，默认为"ffmpeg"（使用系统PATH）
            sample_rate: 输出采样率，默认16000Hz（Whisper要求）
            channels: 输出声道数，默认1（单声道）
        """
        self.ffmpeg_path = ffmpeg_path
        self.sample_rate = sample_rate
        self.channels = channels

        # 验证FFmpeg可用性
        self._validate_ffmpeg()

    def _validate_ffmpeg(self) -> None:
        """
        验证FFmpeg是否可用

        Raises:
            RuntimeError: 如果FFmpeg未安装或不可执行
        """
        try:
            # 尝试运行ffmpeg -version获取版本信息
            probe = ffmpeg.probe("version", cmd=f"{self.ffmpeg_path} -version")
            logger.debug(f"FFmpeg验证通过: {self.ffmpeg_path}")
        except ffmpeg.Error:
            # 如果version参数不被支持，尝试其他方式验证
            try:
                import subprocess
                result = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0]
                    logger.debug(f"FFmpeg验证通过: {version_line}")
                else:
                    raise RuntimeError(
                        f"FFmpeg返回错误，请检查安装: {self.ffmpeg_path}"
                    )
            except FileNotFoundError:
                raise RuntimeError(
                    f"FFmpeg未找到: {self.ffmpeg_path}\n"
                    "请安装FFmpeg并确保其在系统PATH中，或指定--ffmpeg-path参数\n"
                    "Windows: choco install ffmpeg\n"
                    "macOS: brew install ffmpeg\n"
                    "Ubuntu/Debian: sudo apt install ffmpeg"
                )
            except Exception as e:
                raise RuntimeError(f"FFmpeg验证失败: {e}")

    def extract(
        self,
        video_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        从视频文件提取音频

        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径（可选，默认创建临时文件）

        Returns:
            Path: 提取的WAV音频文件路径

        Raises:
            FileNotFoundError: 视频文件不存在
            RuntimeError: FFmpeg处理失败
        """
        video_path = Path(video_path)

        # 验证输入文件存在
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 如果没有指定输出路径，创建临时文件
        if output_path is None:
            # 使用NamedTemporaryFile创建临时WAV文件
            # delete=False 确保文件在提取完成后仍然存在
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                prefix="v2t_audio_"
            )
            output_path = Path(temp_file.name)
            temp_file.close()
        else:
            output_path = Path(output_path)
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"提取音频: {video_path.name} -> {output_path}")
        logger.debug(f"  格式: {self.sample_rate}Hz, {self.channels}ch, 16bit PCM")

        try:
            # 构建FFmpeg处理流程
            # 1. 读取输入视频
            input_stream = ffmpeg.input(str(video_path))

            # 2. 配置音频输出参数
            output_stream = ffmpeg.output(
                input_stream.audio,  # 只提取音频流
                str(output_path),
                ar=self.sample_rate,      # 采样率: 16kHz
                ac=self.channels,         # 声道数: 单声道
                sample_fmt=self.REQUIRED_SAMPLE_FMT,  # 采样格式: 16bit
                vn=True,                  # 禁用视频输出
                y=True                    # 覆盖已存在的输出文件
            )

            # 3. 执行FFmpeg命令
            # overwrite_output=True 相当于 -y 参数
            ffmpeg.run(
                output_stream,
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True  # 禁用FFmpeg的终端输出，使用日志代替
            )

            # 验证输出文件
            if not output_path.exists():
                raise RuntimeError("FFmpeg执行成功但输出文件不存在")

            file_size = output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError("FFmpeg输出文件为空")

            logger.debug(f"  音频提取成功: {file_size / 1024 / 1024:.2f} MB")
            return output_path

        except ffmpeg.Error as e:
            # FFmpeg执行错误
            error_msg = str(e)
            if e.stderr:
                # 解码FFmpeg的错误输出
                try:
                    stderr = e.stderr.decode('utf-8', errors='ignore')
                    error_msg = stderr.split('\n')[-2] if stderr else error_msg
                except:
                    pass

            # 清理可能不完整的输出文件
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass

            raise RuntimeError(f"FFmpeg处理失败: {error_msg}")

        except Exception as e:
            # 其他异常，清理并重新抛出
            if output_path.exists():
                try:
                    output_path.unlink()
                except:
                    pass
            raise

    def get_video_info(self, video_path: Path) -> dict:
        """
        获取视频文件信息

        Args:
            video_path: 视频文件路径

        Returns:
            dict: 包含视频信息的字典（时长、分辨率、码率等）

        Raises:
            FileNotFoundError: 视频文件不存在
            RuntimeError: 无法解析视频信息
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        try:
            probe = ffmpeg.probe(str(video_path), cmd=f"{self.ffmpeg_path}")

            # 提取视频流信息
            video_info = {
                "filename": video_path.name,
                "format": probe.get("format", {}).get("format_name", "unknown"),
                "duration": float(probe.get("format", {}).get("duration", 0)),
                "size": int(probe.get("format", {}).get("size", 0)),
                "bit_rate": int(probe.get("format", {}).get("bit_rate", 0)),
            }

            # 提取第一个视频流的详细信息
            video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
            if video_streams:
                v = video_streams[0]
                video_info.update({
                    "width": v.get("width"),
                    "height": v.get("height"),
                    "fps": eval(v.get("r_frame_rate", "0/1")),  # 如 "30/1" -> 30
                    "codec": v.get("codec_name"),
                })

            # 提取第一个音频流的信息
            audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
            if audio_streams:
                a = audio_streams[0]
                video_info.update({
                    "audio_codec": a.get("codec_name"),
                    "audio_sample_rate": int(a.get("sample_rate", 0)),
                    "audio_channels": a.get("channels"),
                })

            return video_info

        except ffmpeg.Error as e:
            error_msg = str(e)
            if e.stderr:
                try:
                    error_msg = e.stderr.decode('utf-8', errors='ignore')
                except:
                    pass
            raise RuntimeError(f"无法解析视频信息: {error_msg}")

        except Exception as e:
            raise RuntimeError(f"获取视频信息失败: {e}")
