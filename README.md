# Video2Text (V2T) - 视频语音转文本工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Whisper](https://img.shields.io/badge/Whisper-OpenAI-orange.svg)](https://github.com/openai/whisper)

> 基于 OpenAI Whisper 的本地视频语音识别工具，支持多种输出格式，纯离线运行，保护隐私。

---

## 简介

Video2Text 是一个命令行工具，能够从视频文件中提取音频并使用 OpenAI 的 Whisper 模型进行语音识别，将语音转换为文本。所有处理都在本地完成，无需联网（首次下载模型除外），确保数据隐私安全。

**核心特点：**
- 纯本地处理，视频数据不上传云端
- 支持多语言自动识别
- 多种输出格式满足不同场景需求
- 自动清理临时文件，不污染系统
- 详细的日志输出，便于排查问题

---

## 功能特性

### 核心功能

| 功能 | 说明 |
|------|------|
| 视频转录 | 支持 MP4/MKV/AVI/MOV 等常见视频格式 |
| 音频提取 | 自动提取并重采样为 16kHz/16bit WAV |
| 多语言支持 | 多语言自动检测或手动指定 |
| 多格式输出 | TXT/JSON 两种格式 |
| 批量处理 | 支持单个文件处理（批量处理开发中）|

### 输出格式对比

| 格式 | 适用场景 | 特点 |
|------|----------|------|
| TXT | 阅读、编辑、搜索引擎索引 | 纯文本，段落分隔 |
| JSON | 程序化处理、数据分析 | 完整数据，含时间戳和置信度 |

### Whisper 模型选择

| 模型 | 大小 | 速度 | 准确度 | 适用场景 |
|------|------|------|--------|----------|
| tiny | 39 MB | 最快 | 一般 | 快速测试 |
| base | 74 MB | 快 | 良好 | **日常使用（推荐）** |
| small | 244 MB | 中等 | 较好 | 质量优先 |
| medium | 769 MB | 较慢 | 好 | 高质量要求 |
| large | 1550 MB | 最慢 | 最好 | 专业用途 |

---

## 技术栈

### 核心依赖

```
Python 3.8+
├── openai-whisper    # OpenAI 语音识别模型
├── ffmpeg-python     # FFmpeg Python 封装
├── torch             # PyTorch 深度学习框架
├── numpy             # 数值计算
└── tqdm              # 进度条显示
```

### 系统依赖

- **FFmpeg 4.0+**: 用于音频提取和格式转换
- **CPU**: 支持 SSE4.1 的 x86 处理器（Intel/AMD）
- **内存**: 基础模型需 2GB+，大型模型需 8GB+
- **磁盘**: 模型缓存约 1.5GB（使用 large 模型时）

---

## 部署与安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd Video2Text
```

### 2. 安装 FFmpeg

FFmpeg 是必需的系统依赖，用于从视频提取音频。

**Windows:**
```powershell
# 使用 Chocolatey
choco install ffmpeg

# 或手动安装
# 1. 从 https://ffmpeg.org/download.html 下载
# 2. 解压到你期望的目录
# 3. 将 bin 目录添加到系统 PATH
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install ffmpeg
```

**验证安装:**
```bash
ffmpeg -version
```

### 3. 项目内 FFmpeg 配置（推荐）

为了实现项目的独立运行，可以将 FFmpeg 放在项目目录内：

1. 下载 FFmpeg 可执行文件（Windows: `ffmpeg.exe`，Linux/Mac: `ffmpeg`）
2. 将可执行文件放入项目根目录的 `tools/` 文件夹
3. 程序会自动检测并使用该 FFmpeg

```
Video2Text/
├── tools/
│   └── ffmpeg.exe      # 放置 FFmpeg 可执行文件
├── temp/               # 临时文件目录（自动创建）
└── ...
```

**优势：**
- 无需配置系统 PATH
- 项目可以整体打包移植
- 避免与系统 FFmpeg 版本冲突

### 4. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 5. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

首次运行时会自动下载 Whisper 模型到项目根目录的 `models/` 文件夹。

---

## 使用说明

### 快速开始

```bash
# 基础用法 - 只需指定输入文件
python transcribe.py -i video.mp4

# 完整参数 - 指定输出目录、语言、模型、格式
python transcribe.py -i video.mp4 -o ./output/ -l zh -m base -f srt

# 调试模式 - 保留临时文件，显示详细日志
python transcribe.py -i video.mp4 -v --keep-temp
```

### 命令行参数

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | `-i` | 是 | - | 输入视频文件路径 |
| `--output` | `-o` | 否 | output | 输出目录路径 |
| `--language` | `-l` | 否 | auto | 语言代码（如 zh, en, ja）|
| `--model` | `-m` | 否 | base | 模型大小（tiny/base/small/medium/large）|
| `--format` | `-f` | 否 | txt | 输出格式（txt/json）|
| `--ffmpeg-path` | - | 否 | ffmpeg | FFmpeg 可执行文件路径 |
| `--keep-temp` | - | 否 | False | 保留临时音频文件 |
| `--verbose` | `-v` | 否 | False | 显示详细日志 |

### 使用示例

**示例 1: 转录中文视频为 TXT**
```bash
python transcribe.py -i meeting.mp4 -o ./output/ -l zh -f txt
```

**示例 2: 生成 JSON 格式文件**
```bash
python transcribe.py -i movie.mkv -o ./subtitles/ -l en -m small -f json
```

**示例 3: 使用指定 FFmpeg 路径**
```bash
python transcribe.py -i video.mp4 -o ./output/ --ffmpeg-path "your_path/ffmpeg.exe"
```

**示例 4: 调试模式（保留临时文件）**
```bash
python transcribe.py -i video.mp4 -o ./output/ -v --keep-temp
```

### 输出文件

转录完成后，输出文件将保存在指定目录，文件名基于输入视频：

```
output/
├── video.txt      # 纯文本格式
└── video.json     # JSON 完整数据
```

如果文件已存在，会自动添加序号后缀（如 `video_1.txt`）。

### Python API 使用

```python
from pathlib import Path
from audio_extractor import AudioExtractor
from transcriber import WhisperTranscriber
from output_writer import OutputWriter

# 1. 提取音频
extractor = AudioExtractor()
audio_path = extractor.extract(Path("video.mp4"))

# 2. 转录音频
transcriber = WhisperTranscriber(model_name="base")
transcriber.load_model()
result = transcriber.transcribe(audio_path, language="zh")

# 3. 保存结果
writer = OutputWriter(output_dir=Path("./output"))
output_file = writer.write(result, "video.mp4", format_type="srt")

print(f"转录完成: {output_file}")
```

---

## 项目结构

```
Video2Text/
├── transcribe.py           # 主入口脚本，命令行参数解析和流程编排
├── audio_extractor.py      # 音频提取模块，FFmpeg 封装
├── transcriber.py          # Whisper 转录模块，语音识别
├── output_writer.py        # 输出写入模块，支持多种格式
├── utils/                  # 工具函数包（按功能分类）
│   ├── __init__.py         # 包入口，导出常用工具函数
│   ├── path_util.py        # 路径相关工具
│   ├── file_util.py        # 文件操作工具
│   ├── log_util.py         # 日志配置工具
│   ├── format_util.py      # 格式化工具
│   ├── video_util.py       # 视频文件工具
│   └── ffmpeg_util.py      # FFmpeg 相关工具
├── requirements.txt        # Python 依赖清单
├── README.md               # 项目说明文档
├── .gitignore              # Git 忽略配置
├── models/                 # Whisper 模型存放目录（gitignore，自动创建）
├── output/                 # 转录结果输出目录（gitignore）
├── temp/                   # 临时文件目录（gitignore，自动创建）
├── tools/                  # FFmpeg 存放目录（gitignore，可选）
└── test.mp4                # 测试视频文件（可选）
```

### 模块说明

| 模块/目录 | 职责 | 关键类/函数 |
|-----------|------|-------------|
| `transcribe.py` | 流程编排、CLI 接口 | `main()`, `parse_arguments()` |
| `audio_extractor.py` | FFmpeg 音频提取 | `AudioExtractor` |
| `transcriber.py` | Whisper 模型加载和转录 | `WhisperTranscriber` |
| `output_writer.py` | 多格式结果输出 | `OutputWriter` |
| `utils/` | 工具函数包 | 按功能分类的工具模块 |
| `models/` | Whisper 模型存放目录 | 自动创建，首次运行时下载 |
| `temp/` | 临时音频文件目录 | 自动创建，运行后自动清理 |
| `tools/` | FFmpeg 存放目录（可选） | 放置 `ffmpeg.exe` 实现项目独立运行 |
| `output/` | 转录结果输出目录 | 需在运行时通过 `-o` 指定 |

### utils 工具包说明

工具函数按功能分类在 `utils/` 目录下：

| 模块 | 功能 | 主要函数 |
|------|------|----------|
| `path_util.py` | 路径管理 | `get_project_root()`, `get_models_dir()`, `get_temp_dir()` |
| `file_util.py` | 文件操作 | `validate_input_file()`, `cleanup_temp_files()`, `safe_remove()` |
| `log_util.py` | 日志配置 | `setup_logging()`, `get_logger()` |
| `format_util.py` | 格式化 | `format_duration()`, `truncate_text()`, `pluralize()` |
| `video_util.py` | 视频文件 | `is_video_file()`, `get_video_extensions()` |
| `ffmpeg_util.py` | FFmpeg | `get_default_ffmpeg_path()`, `check_ffmpeg_available()` |

使用示例：
```python
# 方式1：从包直接导入常用函数
from utils import setup_logging, get_project_root

# 方式2：从具体模块导入特定功能
from utils.path_util import get_models_dir
from utils.ffmpeg_util import get_default_ffmpeg_path
```

---

## 常见问题

### 1. FFmpeg 未找到

**错误:** `RuntimeError: FFmpeg 未找到`

**解决:**
- 方式一：将 FFmpeg 可执行文件放入项目 `tools/` 目录
- 方式二：将 FFmpeg 安装并添加到系统 PATH
- 方式三：使用 `--ffmpeg-path` 指定完整路径

### 2. 模型下载失败

**错误:** `模型加载失败: Connection timeout`

**解决:**
- 首次下载模型需要网络连接
- 模型下载位置：项目根目录的 `models/` 文件夹
- 可手动下载模型文件放置到该目录，文件名为 `<模型名>.pt`（如 `base.pt`）

### 3. 内存不足

**现象:** 程序被系统终止或报错 `CUDA out of memory`

**解决:**
- 使用更小的模型（tiny/base）
- 关闭其他占用内存的程序
- 使用 CPU 模式（默认自动检测）

### 4. 中文显示乱码

**解决:**
- 确保使用 UTF-8 编码打开输出文件
- Windows 记事本可能需要手动选择编码

---

## 作者

**开发团队:** Video2Text Project

---

## 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

```
MIT License

Copyright (c) 2026 Video2Text Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 更新日志

### v1.0.0 (2024-XX-XX)

**Phase 1 - 基础功能完成**

- 实现核心转录流程：视频 → 音频 → 文本
- 支持 2 种输出格式：TXT、JSON
- 集成 FFmpeg 音频提取（16kHz/16bit/单声道）
- 集成 OpenAI Whisper 语音识别
- 支持 5 种模型规模选择
- 命令行界面完整支持
- 自动清理临时文件
- 详细的错误处理和日志输出
- 完整的文档和注释

**待开发功能:**
- [ ] 批量文件处理
- [ ] 人声活动检测（VAD）过滤静音
- [ ] 进度条显示
- [ ] 配置文件支持
- [ ] GPU 加速优化
- [ ] 多线程并行处理

---

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 强大的开源语音识别模型
- [FFmpeg](https://ffmpeg.org/) - 业界标准的音视频处理工具
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) - FFmpeg 的 Python 封装

---

<p align="center">
  Made with ❤️ by Video2Text Project
</p>
