# Video2Note (V2N) - 视频转笔记工具

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="https://github.com/openai/whisper"><img src="https://img.shields.io/badge/Whisper-OpenAI-orange.svg" alt="Whisper"></a>
</p>

<p align="center">统一工具支持视频转文本(v2t)、文本转笔记(t2n)、视频转笔记(v2n)三种模式，纯本地处理，保护隐私。</p>

---

## 简介

Video2Note 是一个统一的命令行工具，支持三种工作模式：
- **v2t 模式**: 视频转文本 (Video to Text)
- **t2n 模式**: 文本转笔记 (Text to Note)
- **v2n 模式**: 视频转笔记 (Video to Note，一键完成)

基于 OpenAI Whisper 进行本地语音识别，调用大模型生成结构化笔记。所有处理都在本地完成，无需联网（首次下载模型和调用大模型除外），确保数据隐私安全。

**核心特点：**
- 三种工作模式灵活切换
- 纯本地语音识别，视频数据不上传云端
- 支持多语言自动识别
- 多种笔记格式（技术笔记/周报/日记）
- 自动清理临时文件，不污染系统
- 详细的日志输出，便于排查问题

---

## 功能特性

### 三种工作模式

| 模式 | 说明 | 命令示例 |
|------|------|----------|
| v2t | 视频转文本 | `python main.py --mode v2t -i video.mp4` |
| t2n | 文本转笔记 | `python main.py --mode t2n -i text.txt -nf weekly` |
| v2n | 视频转笔记 | `python main.py --mode v2n -i video.mp4 -nf note` |

### 核心功能

| 功能 | 说明 |
|------|------|
| 视频转录 | 支持 MP4/MKV/AVI/MOV 等常见视频格式 |
| 音频提取 | 自动提取并重采样为 16kHz/16bit WAV |
| 多语言支持 | 多语言自动检测或手动指定 |
| 大模型笔记 | 调用通义千问生成结构化笔记 |
| 多格式笔记 | note(技术笔记)/weekly(周报)/diary(日记) |
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

**统一入口 (推荐)**
```bash
# 视频转文本
python main.py --mode v2t -i video.mp4

# 文本转笔记
python main.py --mode t2n -i transcript.txt -nf note

# 视频直接转笔记（一键完成）
python main.py --mode v2n -i video.mp4 -nf weekly
```

**原有入口（向下兼容）**
```bash
# v2t 模式
python transcribe.py -i video.mp4

# t2n 模式
python generate.py -i transcript.txt -f note
```

### 命令行参数（main.py）

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--mode` | `-m` | 是 | - | 工作模式：v2t/t2n/v2n |
| `--input` | `-i` | 是 | - | 输入文件路径 |
| `--output` | `-o` | 否 | output | 输出根目录 |
| `--verbose` | `-v` | 否 | False | 显示详细日志 |

**v2t 模式参数：**
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--whisper-model` | - | 否 | base | Whisper模型（tiny/base/small/medium/large）|
| `--language` | `-l` | 否 | auto | 语言代码（zh/en/ja）|
| `--text-format` | - | 否 | txt | 输出格式（txt/json）|
| `--keep-temp` | - | 否 | False | 保留临时音频文件 |

**t2n 模式参数：**
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--note-format` | `-nf` | 否 | note | 笔记格式（note/weekly/diary）|
| `--llm-model` | - | 否 | qwen3-max | 大模型选择 |
| `--vocab` | - | 否 | - | 词汇表JSON文件路径 |
| `--temperature` | `-t` | 否 | 自动 | 生成温度（0.0-2.0）|
| `--preview` | - | 否 | False | 预览模式，不保存文件 |

**v2n 模式参数：**
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--keep-text` | - | 否 | False | 保留中间文本文件 |

### 使用示例

**示例 1: 视频转文本**
```bash
python main.py --mode v2t -i meeting.mp4 -o ./output/ -l zh
```

**示例 2: 文本转周报**
```bash
python main.py --mode t2n -i meeting.txt -o ./output/ -nf weekly
```

**示例 3: 视频直接转技术笔记**
```bash
python main.py --mode v2n -i lecture.mp4 -nf note --keep-text
```

**示例 4: 预览模式（不保存文件）**
```bash
python main.py --mode t2n -i draft.txt -nf diary --preview
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
Video2Note/
├── main.py                 # 统一入口脚本（推荐）
├── transcribe.py           # v2t 入口：视频转文本
├── generate.py             # t2n 入口：文本转笔记
├── audio_extractor.py      # 音频提取模块
├── transcriber.py          # Whisper 转录模块
├── output_writer.py        # 输出写入模块
├── prompts_loader.py       # 提示词模板加载
├── llm_client.py           # 大模型客户端
├── config.py               # 配置管理
├── utils/                  # 工具函数包
├── prompts/                # 提示词模板目录
│   ├── note.md             # 技术笔记模板
│   ├── weekly.md           # 周报模板
│   └── diary.md            # 日记模板
├── vocab/                  # 词汇表目录
├── requirements.txt        # Python 依赖
├── README.md               # 项目文档
├── models/                 # Whisper 模型存放目录
├── output/                 # 输出根目录
│   ├── text/               # v2t 输出目录
│   ├── notes/              # t2n 输出目录
│   └── temp/               # v2n 中间文件目录
├── temp/                   # 临时音频文件目录
└── tools/                  # FFmpeg 存放目录
```

### 模块说明

| 模块/目录 | 职责 | 说明 |
|-----------|------|------|
| `main.py` | 统一入口 | 推荐使用的入口，支持三种模式 |
| `transcribe.py` | v2t 入口 | 视频转文本独立入口（向下兼容）|
| `generate.py` | t2n 入口 | 文本转笔记独立入口（向下兼容）|
| `audio_extractor.py` | 音频提取 | FFmpeg 封装 |
| `transcriber.py` | 语音转录 | Whisper 模型加载和转录 |
| `output_writer.py` | 结果输出 | 多格式输出支持 |
| `prompts_loader.py` | 提示词加载 | 管理笔记模板 |
| `llm_client.py` | 大模型调用 | DashScope/通义千问客户端 |
| `config.py` | 配置管理 | API密钥等配置 |
| `utils/` | 工具函数包 | 按功能分类的工具模块 |
| `models/` | 模型目录 | Whisper模型缓存 |
| `output/` | 输出目录 | 包含 text/、notes/、temp/ 子目录 |
| `temp/` | 临时目录 | 音频文件，运行后自动清理 |
| `tools/` | 工具目录 | FFmpeg 可执行文件（可选）|

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

### v2.0.0 (2026-04-05)

**V2T + T2N 合并完成**

- 新增统一入口 `main.py`，支持三种工作模式：
  - `v2t` 模式：视频转文本
  - `t2n` 模式：文本转笔记
  - `v2n` 模式：视频直接转笔记（一键完成）
- 完全复用现有 `transcribe.py` 和 `generate.py`
- 参数透传设计，保持各脚本独立性
- 自动清理 v2n 模式中间文件
- 更新 README 文档

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
  Made with ❤️ by Video2Note Project
</p>
