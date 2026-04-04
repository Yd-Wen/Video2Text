# 项目需求

## 项目目标

一个命令行/Python脚本工具，读取本地指定视频文件，输出转录文本文件。无网络服务、无数据库、无上传功能。

## 技术约束

- 纯Python脚本，无Web框架（不用FastAPI/Flask）
- 无数据库（不用SQLite/PostgreSQL）
- 本地文件直接处理，不保存中间状态
- 使用 Whisper base 模型（CPU可运行）
- 单文件脚本或最多3个模块
- 输出到本地文本文件，不提供服务

## 项目结构（可调整）

简单结构，可适当调整：
```plaintext
video-to-text/
├── transcribe.py      # 主脚本：解析参数、调用流程
├── audio_extractor.py # FFmpeg音频提取（可选内联到主脚本）
├── requirements.txt   
└── output/            # 转录结果输出目录（gitignore）
```

## 功能范围（严格限制）
1. **读取本地视频**：通过命令行参数指定文件路径
2. **提取音频**：调用FFmpeg，生成临时WAV文件
3. **Whisper转录**：加载模型，转录为文本
4. **保存结果**：输出到指定目录，仅支持TXT格式
5. **自动清理**：转录完成后删除临时音频文件

## 命令行使用方式
```bash
# 基础用法
python transcribe.py --input /path/to/video.mp4 --output ./output/

# 指定语言（可选）
python transcribe.py --input video.mp4 --output ./output/ --language zh

# 指定模型大小（可选，默认base）
python transcribe.py --input video.mp4 --output ./output/ --model tiny
```

## 依赖清单（可补充调整）

```plaintext
openai-whisper
ffmpeg-python
tqdm          # 进度条
```

## 交付标准

1. 单命令运行：python transcribe.py --input test.mp4 --output ./out/
2. 输出纯文本文件，内容准确可读
3. 临时文件自动清理，不污染系统
4. 基础错误处理：文件不存在、FFmpeg未安装、转录失败等
5. README包含：安装步骤、使用示例、FFmpeg安装指引等

# 项目规划

## 功能拆解

尽可能详细，并且按照新特性逐步开发

## 性能优化

在设计需求实现的时候，尽量考虑性能瓶颈点，并且进行优化方案的探讨

## 产出

规划完成后，将规则文档输出到 .plan 文件中
