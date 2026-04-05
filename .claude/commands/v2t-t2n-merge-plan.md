# 项目需求

## 项目目标

将视频转文本（v2t）和文本转笔记（t2n）合并为一个统一工具，提供三种工作模式：
- **模式1**：视频转文本（v2t）
- **模式2**：文本转笔记（t2n）
- **模式3**：视频转文本转笔记（v2n，一键完成）

无网络服务、无数据库、纯本地处理，通过参数灵活控制流程。

## 技术约束

- 纯Python脚本，无Web框架（不用FastAPI/Flask）
- 无数据库（不用SQLite/PostgreSQL）
- 本地文件直接处理，不保存中间状态（除非用户指定保留中间文件）
- 使用 Whisper base 模型（CPU可运行），支持模型大小选择
- 支持多格式笔记（note/weekly/diary），通过参数选择
- 单文件脚本或最多5个模块
- 输出到本地文件，不提供服务
- 支持主流大模型API：暂时只考虑百炼平台的通义千问（通过 `.env` 文件配置）

## 项目结构（基于现有代码复用）

```plaintext
video-to-note/
├── main.py                # 新增：主脚本，统一入口，模式调度
├── transcribe.py          # 现有：视频转文本主脚本（v2t模式直接调用）
├── generate.py            # 现有：文本转笔记主脚本（t2n模式直接调用）
├── config.py              # 现有：配置管理（API密钥、模型配置）
├── llm_client.py          # 现有：大模型调用客户端
├── prompts_loader.py      # 现有：提示词加载器
├── audio_extractor.py     # 现有：音频提取模块
├── transcriber.py         # 现有：Whisper转录模块
├── output_writer.py       # 现有：输出写入模块
├── utils/                 # 现有：工具函数包
│   ├── __init__.py
│   ├── file_util.py
│   ├── text_util.py
│   ├── log_util.py
│   └── ...
├── prompts/               # 现有：提示词模板目录
│   ├── note.md
│   ├── weekly.md
│   └── diary.md
├── vocab/                 # 可选：领域词汇表（语音识别纠错）
│   └── *.json
├── requirements.txt       # 更新：合并依赖
└── output/                # 输出目录（gitignore）
    ├── temp/              # 临时音频文件（自动清理）
    ├── text/              # 视频转文本输出（txt/json）
    └── notes/             # 笔记输出（{格式}_原文件名.md）
```

## 与现有代码的兼容性设计

### 复用策略
- **transcribe.py**：完全复用，作为v2t模式的执行入口
- **generate.py**：完全复用，作为t2n模式的执行入口
- **所有支持模块**：config.py, llm_client.py, prompts_loader.py 等直接复用

### 参数调整（解决冲突）
- v2t的 `--format` 用于指定输出格式（txt/json）
- t2n的 `--format` 用于指定笔记类型（note/weekly/diary）
- **解决方案**：
  - main.py 中 v2t 相关参数保持原意
  - t2n 的笔记格式参数改为 `--note-format`（简写 `-nf`）

### 输出路径对齐
- v2t 默认输出：`output/text/`
- t2n 默认输出：`output/notes/`
- v2n 中间文本默认保存到 `output/temp/`，完成后自动清理（除非 `--keep-text`）

## 功能范围

### 核心功能
1. **模式调度**：通过 `--mode` 参数控制 v2t / t2n / v2n
2. **视频转文本（v2t）**：复用 transcribe.py，FFmpeg提取音频 → Whisper转录 → 保存文本
3. **文本转笔记（t2n）**：复用 generate.py，预处理 → 组装提示词 → LLM生成 → 保存Markdown
4. **一键流程（v2n）**：视频直接生成笔记，中间文本可选保留或自动清理

### 辅助功能
5. **格式选择**：笔记类型 note/weekly/diary（模式2、3可用）
6. **词汇表**：复用 generate.py 的词汇表加载逻辑
7. **流式生成**：复用 llm_client.py 的流式响应处理
8. **进度反馈**：复用现有日志和进度显示

## 命令行使用方式

```bash
# ========== 模式1：视频转文本（v2t）==========
python main.py --mode v2t --input video.mp4 --output ./output/text/

# 指定Whisper模型大小
python main.py --mode v2t --input video.mp4 --whisper-model tiny

# 保留临时音频文件（默认自动删除）
python main.py --mode v2t --input video.mp4 --keep-temp


# ========== 模式2：文本转笔记（t2n）==========
python main.py --mode t2n --input ./output/text/transcript.txt --note-format note

# 指定笔记格式（默认note）
python main.py --mode t2n --input meeting.txt --note-format weekly
python main.py --mode t2n --input diary.txt --note-format diary

# 指定LLM模型（默认qwen3-max）
python main.py --mode t2n --input text.txt --llm-model qwen3-max

# 自定义词汇表（复用generate.py逻辑）
python main.py --mode t2n --input tech.txt --vocab ./custom_vocab.json

# 预览模式（不保存，打印到终端）
python main.py --mode t2n --input draft.txt --preview


# ========== 模式3：视频直接转笔记（v2n）==========
python main.py --mode v2n --input video.mp4 --note-format note

# 保留中间文本文件（默认自动删除）
python main.py --mode v2n --input video.mp4 --note-format weekly --keep-text


# 完整参数示例
python main.py \
    --mode v2n \
    --input ./videos/lecture.mp4 \
    --output ./output/ \
    --note-format note \
    --whisper-model base \
    --llm-model qwen3-max \
    --language zh \
    --keep-text
```

## main.py 参数设计

```python
# 核心参数
--mode, -m          # 工作模式：v2t / t2n / v2n（必需）
--input, -i         # 输入文件路径（必需）
--output, -o        # 输出目录（默认：./output/）

# v2t 相关参数
--whisper-model     # Whisper模型：tiny/base/small/medium/large（默认base）
--language, -l      # 语言代码，如zh/en/ja（默认auto）
--text-format       # 文本输出格式：txt/json（默认txt）
--keep-temp         # 保留临时音频文件

# t2n 相关参数
--note-format, -nf  # 笔记格式：note/weekly/diary（默认note）
--llm-model         # LLM模型（默认qwen3-max）
--vocab             # 自定义词汇表路径
--temperature, -t   # 生成温度
--preview           # 预览模式

# v2n 专用参数
--keep-text         # 保留中间文本文件（默认自动清理）

# 通用参数
--verbose, -v       # 详细日志
```

## 依赖清单

```plaintext
# 核心依赖（合并原有依赖）
openai-whisper          # 本地语音识别
ffmpeg-python           # 音频提取
dashscope               # 百炼平台通义千问API

# 辅助依赖
tqdm                    # 进度条
python-dotenv           # 环境变量加载
```

## 配置方式（.env文件）

```bash
# .env 文件示例
# API密钥
DASHSCOPE_API_KEY=sk-b01fa56960e0483ab12dff7a7577129f
```

## 交付标准

1. **单命令运行**：三种模式均可通过一条命令完成
2. **模式隔离**：各模式独立可用，不强制依赖其他模式
3. **代码复用**：完全复用现有 transcribe.py 和 generate.py，不做重复实现
4. **输出规范**：
   - 文本输出：`output/text/原文件名.txt` 或 `.json`
   - 笔记输出：`output/notes/{格式}_原文件名.md`（如 `note_lecture.md`）
   - v2n中间文件：`output/temp/原文件名.txt`（默认自动清理）
5. **自动清理**：临时音频、中间文本（除非指定保留）自动删除
6. **错误处理**：
   - 文件不存在、FFmpeg未安装
   - Whisper模型加载失败
   - API密钥缺失、网络超时、模型限流
   - 中断恢复（Ctrl+C时已完成内容保留）
7. **README包含**：
   - 三种模式完整使用示例
   - FFmpeg安装指引
   - API密钥配置说明
   - 词汇表扩展指南
   - 故障排查（常见问题）

## 实现要点

1. **main.py 逻辑**：
   - 解析 `--mode` 参数
   - 根据不同模式组装参数并调用对应脚本
   - v2n模式：先调用 transcribe.py 流程生成文本，再调用 generate.py 流程生成笔记

2. **v2n 模式流程**：
   ```
   输入视频 → FFmpeg提取音频 → Whisper转录 → 保存临时文本 → LLM生成笔记 → 清理临时文件
   ```

3. **参数透传**：
   - main.py 将各模式的专属参数原样传递给对应脚本
   - 保持 transcribe.py 和 generate.py 的独立性
