# V2N (Video-to-Note) 项目规划

## 项目概述

将视频转文本（v2t）和文本转笔记（t2n）合并为一个统一工具 Video2Note，提供三种工作模式：
- **v2t**: 视频转文本
- **t2n**: 文本转笔记
- **v2n**: 视频转笔记（一键完成）

---

## Phase 1: 基础架构搭建

### 1.1 项目结构整理

**目标**: 建立清晰的项目目录结构

```
Video2Note/
├── main.py                 # 统一入口（新增）
├── transcribe.py           # v2t 入口（复用）
├── generate.py             # t2n 入口（复用）
├── audio_extractor.py      # 音频提取（复用）
├── transcriber.py          # Whisper转录（复用）
├── output_writer.py        # 输出写入（复用）
├── prompts_loader.py       # 提示词加载（复用）
├── llm_client.py           # 大模型客户端（复用）
├── config.py               # 配置管理（复用）
├── utils/                  # 工具函数包（复用）
│   ├── __init__.py
│   ├── file_util.py
│   ├── text_util.py
│   ├── log_util.py
│   ├── path_util.py
│   ├── format_util.py
│   ├── video_util.py
│   └── ffmpeg_util.py
├── prompts/                # 提示词模板（复用）
│   ├── note.md
│   ├── weekly.md
│   ├── diary.md
│   └── system.md
├── vocab/                  # 词汇表目录（复用）
├── output/                 # 输出根目录
│   ├── text/               # v2t 输出
│   ├── notes/              # t2n 输出
│   └── temp/               # v2n 中间文件
├── models/                 # Whisper模型缓存
├── tools/                  # FFmpeg可执行文件
├── requirements.txt        # 依赖清单
└── README.md               # 项目文档
```

**验收标准**:
- [ ] 目录结构符合上述规范
- [ ] output/text/、output/notes/、output/temp/ 目录存在（可自动创建）

### 1.2 依赖整合

**文件**: `requirements.txt`

**核心依赖**:
```txt
openai-whisper>=20231117    # 语音识别
ffmpeg-python>=0.2.0        # 音频提取
dashscope>=1.20.0           # 百炼平台SDK
tqdm>=4.65.0                # 进度条
```

**验收标准**:
- [ ] 所有依赖可正常安装
- [ ] 无版本冲突

---

## Phase 2: main.py 核心开发

### 2.1 参数解析设计

**目标**: 实现统一的命令行参数解析

**必需参数**:
```python
--mode, -m          # 工作模式：v2t / t2n / v2n
--input, -i         # 输入文件路径
```

**可选参数**:
```python
--output, -o        # 输出目录（默认：./output/）
--verbose, -v       # 详细日志
```

**v2t 专用参数**:
```python
--whisper-model     # Whisper模型（tiny/base/small/medium/large）
--language, -l      # 语言代码
--text-format       # 输出格式（txt/json）
--keep-temp         # 保留临时音频文件
```

**t2n 专用参数**:
```python
--note-format, -nf  # 笔记格式（note/weekly/diary）
--llm-model         # LLM模型（默认qwen3-max）
--vocab             # 词汇表路径
--temperature, -t   # 生成温度
--preview           # 预览模式
```

**v2n 专用参数**:
```python
--keep-text         # 保留中间文本文件
```

**验收标准**:
- [ ] 所有参数解析正确
- [ ] 参数冲突检测（如 v2t 模式使用 --note-format 应警告）
- [ ] 帮助信息完整清晰

### 2.2 模式调度实现

**核心逻辑**:
```python
def main():
    args = parse_arguments()
    
    if args.mode == "v2t":
        return run_v2t_mode(args)
    elif args.mode == "t2n":
        return run_t2n_mode(args)
    elif args.mode == "v2n":
        return run_v2n_mode(args)
```

**v2t 模式**:
- 构建 transcribe.py 命令行参数
- 调用 subprocess 执行 transcribe.py
- 返回执行结果

**t2n 模式**:
- 构建 generate.py 命令行参数
- 调用 subprocess 执行 generate.py
- 返回执行结果

**v2n 模式**:
- 步骤1: 调用 v2t 生成临时文本文件到 output/temp/
- 步骤2: 调用 t2n 生成笔记到 output/notes/
- 步骤3: 如未指定 --keep-text，删除临时文本文件

**验收标准**:
- [ ] 三种模式均可正常调用
- [ ] 参数正确透传给子脚本
- [ ] 退出码正确传递

### 2.3 错误处理与清理

**错误场景**:
- 输入文件不存在 → 退出码 2
- v2t 执行失败 → 退出码 3
- t2n 执行失败 → 退出码 4
- 用户中断 (Ctrl+C) → 退出码 130

**清理逻辑**:
- v2n 模式下，即使 t2n 失败，保留临时文本以便调试
- 正常完成且未指定 --keep-text 时，自动清理临时文件

**验收标准**:
- [ ] 各种错误场景处理正确
- [ ] 临时文件清理逻辑正确
- [ ] 中断时保留已生成内容

---

## Phase 3: 参数兼容处理

### 3.1 参数映射表

| main.py 参数 | transcribe.py 参数 | generate.py 参数 |
|-------------|-------------------|-----------------|
| --input | --input | --input |
| --output | --output | --output |
| --whisper-model | --model | - |
| --language | --language | - |
| --text-format | --format | - |
| --keep-temp | --keep-temp | - |
| --note-format | - | --format |
| --llm-model | - | --model |
| --vocab | - | --vocab |
| --temperature | - | --temperature |
| --preview | - | --preview |
| --verbose | --verbose | --verbose |

### 3.2 构建命令函数

**build_v2t_command()**:
```python
def build_v2t_command(args, output_dir):
    cmd = [
        sys.executable, "transcribe.py",
        "-i", args.input,
        "-o", output_dir,
        "-m", args.whisper_model,
        "-l", args.language,
        "-f", args.text_format,
    ]
    # 添加可选参数
    if args.keep_temp:
        cmd.append("--keep-temp")
    if args.verbose:
        cmd.append("-v")
    return cmd
```

**build_t2n_command()**:
```python
def build_t2n_command(args, input_file, output_dir):
    cmd = [
        sys.executable, "generate.py",
        "-i", input_file,
        "-o", output_dir,
        "-f", args.note_format,
        "-m", args.llm_model,
    ]
    # 添加可选参数
    if args.vocab:
        cmd.extend(["--vocab", args.vocab])
    if args.temperature is not None:
        cmd.extend(["-t", str(args.temperature)])
    if args.preview:
        cmd.append("--preview")
    if args.verbose:
        cmd.append("-v")
    return cmd
```

**验收标准**:
- [ ] 参数映射正确
- [ ] 所有参数正确透传
- [ ] 未使用的参数不传递

---

## Phase 4: v2n 模式实现

### 4.1 流程设计

```
输入视频 → FFmpeg提取音频 → Whisper转录 → 
保存临时文本 → LLM生成笔记 → 清理临时文件
```

### 4.2 关键实现点

**临时文件命名**:
```python
temp_text_file = temp_dir / f"{input_stem}.txt"
```

**v2n 模式核心代码**:
```python
def run_v2n_mode(args):
    # 步骤1: 视频转文本
    temp_output_dir = Path(args.output) / "temp"
    v2t_args = argparse.Namespace(**vars(args))
    v2t_args.text_format = "txt"  # 强制使用txt格式
    
    cmd_v2t = build_v2t_command(v2t_args, str(temp_output_dir))
    exit_code = run_subprocess(cmd_v2t)
    if exit_code != 0:
        return exit_code
    
    # 查找生成的文本文件
    temp_text_file = find_generated_text(temp_output_dir, args.input)
    
    # 步骤2: 文本转笔记
    notes_output_dir = Path(args.output) / "notes"
    cmd_t2n = build_t2n_command(args, str(temp_text_file), str(notes_output_dir))
    exit_code = run_subprocess(cmd_t2n)
    if exit_code != 0:
        return exit_code
    
    # 步骤3: 清理临时文件
    if not args.keep_text:
        temp_text_file.unlink()
    
    return 0
```

**验收标准**:
- [ ] 流程串联正确
- [ ] 临时文件路径正确
- [ ] 清理逻辑正确
- [ ] 失败时保留调试文件

---

## Phase 5: 测试验证

### 5.1 单元测试

**测试场景**:
1. v2t 模式调用
   ```bash
   python main.py --mode v2t -i test.mp4
   ```

2. t2n 模式调用
   ```bash
   python main.py --mode t2n -i test.txt -nf note
   ```

3. v2n 模式调用
   ```bash
   python main.py --mode v2n -i test.mp4 -nf weekly
   ```

4. 完整参数测试
   ```bash
   python main.py --mode v2n -i test.mp4 -o ./output/ \
       -nf note --whisper-model base --keep-text -v
   ```

### 5.2 边界情况测试

- [ ] 输入文件不存在
- [ ] 输出目录无写入权限
- [ ] 无效的模式参数
- [ ] 无效的笔记格式
- [ ] 用户中断 (Ctrl+C)
- [ ] 子进程失败时的错误传递

**验收标准**:
- [ ] 所有测试场景通过
- [ ] 错误信息清晰
- [ ] 退出码正确

---

## Phase 6: 文档完善

### 6.1 README.md 更新

**必需内容**:
- [ ] 三种模式简介
- [ ] 快速开始示例
- [ ] 完整参数说明
- [ ] 使用示例
- [ ] 项目结构说明
- [ ] 常见问题

### 6.2 使用示例

**v2t 模式**:
```bash
python main.py --mode v2t -i video.mp4 -o ./output/
```

**t2n 模式**:
```bash
python main.py --mode t2n -i transcript.txt -nf weekly
```

**v2n 模式**:
```bash
python main.py --mode v2n -i lecture.mp4 -nf note --keep-text
```

**验收标准**:
- [ ] README 内容完整
- [ ] 示例可运行
- [ ] 参数说明准确

---

## 开发顺序建议

```
Phase 1: 基础架构
  └── 1.1 项目结构整理
  └── 1.2 依赖整合

Phase 2: main.py 核心
  └── 2.1 参数解析设计
  └── 2.2 模式调度实现
  └── 2.3 错误处理与清理

Phase 3: 参数兼容
  └── 3.1 参数映射表
  └── 3.2 构建命令函数

Phase 4: v2n 模式
  └── 4.1 流程设计
  └── 4.2 关键实现点

Phase 5: 测试验证
  └── 5.1 单元测试
  └── 5.2 边界情况测试

Phase 6: 文档完善
  └── 6.1 README.md 更新
  └── 6.2 使用示例
```

---

## 交付清单

- [ ] main.py 主入口脚本
- [ ] 参数解析正确
- [ ] 三种模式均可运行
- [ ] v2n 模式自动清理临时文件
- [ ] 错误处理完善
- [ ] README.md 文档更新
- [ ] 所有测试通过

---

## 附录：退出码定义

| 退出码 | 含义 |
|-------|------|
| 0 | 成功 |
| 1 | 参数错误 |
| 2 | 文件不存在 |
| 3 | v2t 执行失败 |
| 4 | t2n 执行失败 |
| 130 | 用户中断 (Ctrl+C) |
