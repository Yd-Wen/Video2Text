# 项目需求

## 项目目标

一个命令行/Python脚本工具，读取本地文本文件（视频转录结果、会议记录、文章等），调用大模型生成结构化笔记。无网络服务、无数据库、纯本地处理。

可以直接读取文本生成笔记；也可以在视频转文本功能完成后读取生成的文本再生成笔记；通过参数控制视频转文本、文本转笔记、视频转文本转笔记三种模式。

## 技术约束

- 纯Python脚本，无Web框架（不用FastAPI/Flask）
- 无数据库（不用SQLite/PostgreSQL）
- 本地文件直接处理，不保存中间状态
- 支持多格式切换（笔记/周报/日记，可扩展），通过命令行参数选择
- 单文件脚本或最多4个模块
- 输出到本地Markdown文件，不提供服务
- 支持主流大模型API：DeepSeek/通义千问等（通过 env 文件配置，不考虑环境变量），可扩展

## 项目结构（可调整）

简单结构，可适当调整：
```plaintext
text-to-note/
├── generate.py         # 主脚本：解析参数、调用流程
├── prompts/            # 提示词模板（笔记/周报/日记）
│   ├── note.md         # 笔记提示词模板（包含示例）
│   ├── weekly.md       # 周报提示词模板（包含示例）
│   └── diary.md        # 日记提示词模板（包含示例）
├── vocabulary.py       # 领域词汇表（语音识别纠错映射）
├── config.py           # 配置管理（API密钥、模型选择）
├── requirements.txt    
└── output/             # 输出目录（gitignore）
    ├──text/            # 视频转文本输出目录
    └──notes/           # 文本转笔记输出目录（笔记类型（note/weekly/diary）_文件名.md）
```

## 功能范围（严格限制）

1. **读取本地文本**：通过命令行参数指定文件路径，支持txt/json（视频转录结果）
2. **格式选择**：通过参数选择笔记类型（note/weekly/diary）
3. **预处理**：基础清洗（去除时间戳、合并断行、加载专用词汇表纠错）
4. **大模型调用**：组装提示词，流式生成笔记内容
5. **保存结果**：输出Markdown文件
6. **错误处理**：文件不存在、API密钥缺失、模型调用失败等

## 命令行使用方式

```bash
# 基础用法（默认技术笔记格式，默认输出到/output/notes）
python generate.py --input ./output/text/test.txt --output ./output/notes/

# 指定格式
python generate.py --input meeting.txt --output ./output/notes/ --format weekly
python generate.py --input podcast.txt --output ./output/notes/ --format diary

# 指定模型（可选，默认deepseek-chat）
python generate.py --input lecture.txt --output ./output/notes/ --model deepseek

# 自定义词汇表（可选）
python generate.py --input tech_talk.txt --output ./output/notes/ --vocab ./custom_vocab.json

# 预览模式（不保存，直接打印到终端）
python generate.py --input draft.txt --preview
```

## 依赖清单（可补充调整）

```plaintext
openai>=1.0.0          # 兼容OpenAI格式API（DeepSeek/通义千问兼容）
tqdm                   # 进度条（流式响应模拟）
```

## 交付标准

1. 单命令运行：`python generate.py --input transcript.txt --output ./output/notes/`
2. 输出标准Markdown文件，结构清晰、可直接阅读
3. 自动识别并修正转录文本中的语音识别错误
4. 基础错误处理：文件不存在、API密钥缺失、网络超时、模型限流等
5. 支持Ctrl+C中断，已生成内容不丢失（流式写入）
6. README包含：安装步骤、API密钥配置、使用示例、格式说明、词汇表扩展指南
