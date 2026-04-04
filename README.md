# Video2Text (V2T) - 视频语音转文本工具

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Video2Text (V2T) 是一个轻量级命令行工具，基于 OpenAI Whisper 实现视频语音转文本。纯本地处理，无需网络服务，保护隐私。

### 核心特性

- 🎯 **简单易用**：单命令完成视频转文本
- 🔒 **本地处理**：无需上传，保护隐私
- 🌍 **多语言支持**：支持 99 种语言自动检测
- 📄 **多格式输出**：TXT、SRT、VTT、JSON
- ⚡ **高效处理**：CPU 即可运行，支持长视频
- 🧹 **自动清理**：临时文件自动删除

---

## 快速开始

### 环境要求

- Python 3.8+
- FFmpeg 4.0+

### 安装 FFmpeg

**Windows:**
```bash
# 使用 chocolatey
choco install ffmpeg

# 或手动下载：https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

### 安装工具

```bash
# 克隆项目
git clone <repository-url>
cd Video2Text

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 首次运行

```bash
# 基础用法
python transcribe.py --input /path/to/video.mp4 --output ./output/

# 指定语言
python transcribe.py --input video.mp4 --output ./output/ --language zh

# 指定模型大小
python transcribe.py --input video.mp4 --output ./output/ --model base

# 输出字幕格式
python transcribe.py --input video.mp4 --output ./output/ --format srt
```

---

## 使用指南

### 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--input` | `-i` | 输入视频文件路径（必填） | - |
| `--output` | `-o` | 输出目录路径（必填） | - |
| `--language` | `-l` | 语言代码（如 zh, en, ja） | auto |
| `--model` | `-m` | 模型大小（tiny/base/small/medium/large） | base |
| `--format` | `-f` | 输出格式（txt/srt/vtt/json） | txt |
| `--keep-temp` | - | 保留临时音频文件 | False |

### 模型选择建议

| 模型 | 显存/RAM | 速度 | 准确度 | 适用场景 |
|------|----------|------|--------|----------|
| tiny | ~1GB | 最快 | 一般 | 快速测试 |
| base | ~1GB | 快 | 良好 | 日常使用 |
| small | ~2GB | 中等 | 较好 | 质量优先 |
| medium | ~5GB | 较慢 | 好 | 高质量要求 |
| large | ~10GB | 最慢 | 最好 | 专业用途 |

> **注意**：CPU 运行建议选择 tiny/base，medium/large 需要较长处理时间。

### 语言代码参考

常用语言代码：
- `zh` - 中文
- `en` - 英语
- `ja` - 日语
- `ko` - 韩语
- `fr` - 法语
- `de` - 德语
- `es` - 西班牙语

完整列表见 [Whisper 语言支持](https://github.com/openai/whisper#available-models-and-languages)

---

## 项目结构

```
Video2Text/
├── transcribe.py          # 主入口脚本
├── audio_extractor.py     # 音频提取模块
├── transcriber.py         # Whisper转录模块
├── output_writer.py       # 输出格式模块
├── utils.py               # 工具函数
├── requirements.txt       # Python依赖
├── README.md              # 使用文档
├── .gitignore
└── output/                # 默认输出目录（gitignore）
```

---

## 示例

### 基础转录

```bash
python transcribe.py -i ./videos/meeting.mp4 -o ./output/
```

输出：`./output/meeting.txt`

### 生成中文字幕

```bash
python transcribe.py -i ./videos/movie.mp4 -o ./output/ -l zh -f srt
```

输出：`./output/movie.srt`

### 高质量转录

```bash
python transcribe.py -i ./videos/lecture.mp4 -o ./output/ -m small -l en
```

### 批量处理（使用 shell）

```bash
# Bash
for f in ./videos/*.mp4; do
    python transcribe.py -i "$f" -o ./output/ -l zh
done

# PowerShell
Get-ChildItem ./videos/*.mp4 | ForEach-Object {
    python transcribe.py -i $_.FullName -o ./output/ -l zh
}
```

---

## 常见问题

### 1. FFmpeg 未找到

**错误**：`FFmpeg not found. Please install FFmpeg first.`

**解决**：
- 确认 FFmpeg 已安装：`ffmpeg -version`
- 确认 FFmpeg 在系统 PATH 中
- 或使用 `--ffmpeg-path` 指定路径

### 2. 模型下载失败

**错误**：模型下载超时或失败

**解决**：
- 检查网络连接
- 设置代理环境变量
- 手动下载模型放到 `~/.cache/whisper/`

### 3. 内存不足

**错误**：`CUDA out of memory` 或系统卡顿

**解决**：
- 使用更小的模型（tiny/base）
- 关闭其他占用内存的程序
- 添加 `--device cpu` 强制使用 CPU

### 4. 转录质量不佳

**建议**：
- 尝试更大的模型（small/medium）
- 明确指定语言 `--language`
- 确保视频音频清晰

---

## 开发计划

- [x] 基础转录功能
- [x] 多格式输出支持
- [ ] 长视频分段处理优化
- [ ] 批处理模式
- [ ] 说话人分离
- [ ] 图形界面（可选）

查看 [详细规划](./.plan/v2t-simple-cli-plan.md) 了解更多。

---

## 性能参考

在 Intel i7-10700 / 16GB RAM 环境下测试：

| 视频时长 | 模型 | 处理时间 | 内存占用 |
|----------|------|----------|----------|
| 5 分钟 | tiny | ~30 秒 | ~1GB |
| 5 分钟 | base | ~60 秒 | ~1GB |
| 30 分钟 | base | ~6 分钟 | ~1.5GB |
| 2 小时 | base | ~25 分钟 | ~2GB |

---

## 许可证

[MIT License](./LICENSE)

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 开源语音识别模型
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具
