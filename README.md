# Video2Note (V2N) - 视频转笔记工具

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python"></a>
  <a href="https://github.com/openai/whisper"><img src="https://img.shields.io/badge/Whisper-OpenAI-orange.svg" alt="Whisper"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="#vibe-coding"><img src="https://img.shields.io/badge/Built%20with-Vibe%20Coding-purple.svg" alt="Vibe Coding"></a>
</p>

<p align="center">视频转笔记工具，支持视频转文本(v2t)、文本转笔记(t2n)、视频转笔记(v2n)三种模式。</p>

---

## 简介

> **本项目是一个纯 Vibe Coding 项目 —— 没有敲一行代码，完全通过与 AI 对话完成开发。**

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

---

## 部署与安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd Video2Note
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
Video2Note/
├── tools/
│   └── ffmpeg.exe      # 放置 FFmpeg 可执行文件
└── ...
```

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

### 命令行参数

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--mode` | `-m` | 是 | - | 工作模式：v2t/t2n/v2n |
| `--input` | `-i` | 是 | - | 输入文件路径 |
| `--output` | `-o` | 否 | output | 输出根目录 |
| `--verbose` | `-v` | 否 | False | 显示详细日志 |

**v2t 模式参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--whisper-model` | base | Whisper模型（tiny/base/small/medium/large）|
| `--language` | auto | 语言代码（zh/en/ja）|
| `--text-format` | txt | 输出格式（txt/json）|

**t2n 模式参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--note-format` | note | 笔记格式（note/weekly/diary）|
| `--llm-model` | qwen3-max | 大模型选择 |
| `--temperature` | 自动 | 生成温度（0.0-2.0）|
| `--preview` | False | 预览模式，不保存文件 |

**v2n 模式参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--keep-text` | False | 保留中间文本文件 |

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

### 输出文件

```
output/
├── text/              # v2t 输出
│   └── video.txt
├── notes/             # t2n/v2n 输出
│   └── video_note.md
└── temp/              # v2n 中间文件（自动清理）
```

---

## 开源协议

本项目基于 [MIT](LICENSE) License 开源。

Copyright (C) 2026 - present by Yd Wen

---

## 作者

- **Yd Wen** 
  - [GitHub](https://github.com/Yd-Wen)
  - [Gitee](https://gitee.com/yindong-wen)
  - [个人主页](https://yindongwen.top)

---

## Vibe Coding 开发历程

> **什么是 Vibe Coding？**
> 
> Vibe Coding 是一种全新的开发方式 —— 开发者通过自然语言与 AI 对话，描述需求和想法，由 AI 生成代码并完成实现。开发者专注于产品思维、架构设计和需求表达，而具体的编码工作交给 AI 完成。

本项目从零开始，完全采用 Vibe Coding 方式开发。以下是三个核心特性的诞生过程：

### v2t 特性：视频转文本

**需求描述**：将视频中的语音提取并转录成文本

**开发过程**：
1. **技术选型阶段**：与 AI 讨论技术方案，确定使用 OpenAI Whisper 进行本地语音识别
2. **架构设计阶段**：设计视频→音频→文本的处理流程
3. **实现阶段**：通过多轮对话，逐步完善音频提取、Whisper 调用、输出格式化等功能
4. **迭代优化**：添加多语言支持、多种输出格式（TXT/JSON）、模型选择等特性

**关键决策**：
- 使用 FFmpeg 进行音频提取，确保兼容性
- 音频统一转换为 16kHz/16bit/单声道，优化 Whisper 识别效果
- 纯本地处理，保护数据隐私

### t2n 特性：文本转笔记

**需求描述**：将转录的文本通过大模型加工成结构化笔记

**开发过程**：
1. **设计 Prompt 模板**：与 AI 协作设计技术笔记、周报、日记三种笔记格式的提示词模板
2. **LLM 客户端开发**：封装通义千问 API 调用，支持流式输出和错误处理
3. **模板引擎实现**：实现 Markdown 模板的动态加载和变量替换
4. **参数调优**：通过多轮测试确定最优的 temperature 等生成参数

**关键决策**：
- 采用 Markdown 文件作为提示词模板，便于维护和扩展
- 支持三种笔记格式：技术笔记（note）、周报（weekly）、日记（diary）
- 添加预览模式，方便调试 Prompt 效果

### v2n 特性：视频转笔记（一键完成）

**需求描述**：将 v2t 和 t2n 串联，实现视频直接生成笔记

**开发过程**：
1. **架构整合**：设计统一的入口脚本 `main.py`，支持三种工作模式
2. **流程串联**：实现 v2t → t2n 的自动化流水线
3. **参数透传**：设计优雅的参数传递机制，保持各脚本的独立性
4. **资源管理**：添加自动清理机制，避免中间文件污染

**关键决策**：
- 复用已有的 `transcribe.py` 和 `generate.py`，不重复造轮子
- 统一的命令行参数风格，降低用户学习成本
- v2n 模式自动清理中间文件，保持输出目录整洁
- 提供 `--keep-text` 选项，允许保留中间文本文件

### Vibe Coding 的体验与感悟

**优势**：
- **开发效率极高**：3 天内完成从想法到可用产品的全过程
- **专注设计而非实现**：将精力集中在产品逻辑和用户体验上
- **代码质量稳定**：AI 生成的代码风格一致，结构清晰
- **快速迭代**：通过对话即可修改功能，无需手动改代码

**挑战**：
- **需求表达要清晰**：需要准确描述想要的功能，模糊的需求会导致偏差
- **上下文管理**：长对话中需要不断回顾和确认之前的决策
- **技术债务**：需要主动要求 AI 进行重构和优化，避免代码臃肿

**给想尝试 Vibe Coding 的开发者**：
1. 从明确的小需求开始，逐步扩展
2. 保持对话的连贯性，让 AI 理解项目的整体架构
3. 不要害怕重构，定期要求 AI 优化代码结构
4. 保存好提示词模板，它们是可以复用的资产

---

## 更新日志

### v1.1.0 (2026-04-05)

**V2T + T2N 合并完成**

- 新增统一入口 `main.py`，支持三种工作模式：
  - `v2t` 模式：视频转文本
  - `t2n` 模式：文本转笔记
  - `v2n` 模式：视频直接转笔记（一键完成）
- 复用 `transcribe.py` 和 `generate.py`
- 参数透传设计，保持各脚本独立性
- 自动清理 v2n 模式中间文件

### v1.0.0 (2026-04-04)

**基础功能完成**

- 实现核心转录流程：视频 → 音频 → 文本
- 支持 2 种输出格式：TXT、JSON
- 集成 FFmpeg 音频提取（16kHz/16bit/单声道）
- 集成 OpenAI Whisper 语音识别
- 支持 5 种模型规模选择

---

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 强大的开源语音识别模型
- [FFmpeg](https://ffmpeg.org/) - 业界标准的音视频处理工具
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) - FFmpeg 的 Python 封装

---

<p align="center">
Made with ❤️ by Video2Note Project
</p>
