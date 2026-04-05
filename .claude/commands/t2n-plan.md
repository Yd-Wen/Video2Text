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

---

# 项目规划

## 功能拆解（按新特性逐步开发）

### Phase 1: 基础框架（MVP）
- [ ] 搭建项目结构，创建 `generate.py` 主入口
- [ ] 实现命令行参数解析（argparse）：input, output, format, model, preview
- [ ] 实现基础文本读取和编码检测（utf-8/gbk容错）
- [ ] 实现基础预处理：去除时间戳 `[00:12:34]`、合并断行、去除多余空行
- [ ] 实现文件输出：`笔记类型（note/weekly/diary）_文件名.md`

**验收标准**：`python generate.py --input test.txt --output ./out/` 能读取文件并输出空模板MD

### Phase 2: 提示词系统
- [ ] 创建 `prompts.py`，定义三种格式的完整提示词模板
  - `NOTE_TEMPLATE`：技术笔记结构（概念表/对比/案例/洞察）
  - `WEEKLY_TEMPLATE`：周报结构（成果/进展/问题/计划）
  - `DIARY_TEMPLATE`：日记结构（事件/感受/学到/反思）
- [ ] 每个模板包含：系统角色设定 + 词汇表注入位置 + 输出格式规范 + Few-shot示例
- [ ] 实现 `PromptBuilder` 类，根据format类型组装最终提示词

**验收标准**：三种格式的提示词能正确组装，打印预览符合预期结构

### Phase 3: 词汇表与预处理
- [ ] 创建 `vocabulary.py`，定义默认词汇表
  - 通用技术词：{"Sai AI": "CLI", "Giu AI": "GUI", "教户": "交互"}
  - 工作场景词：{"进毒": "通读", "晚程": "完成", "暴错": "报错"}
  - 情绪描述词：{"内心等待": "耐心等待", "效果不错": "效果良好"}
- [ ] 实现 `TextCleaner` 类，支持：
  - 正则清洗（时间戳、说话人标识）
  - 词汇表替换（批量纠错）
  - 口语化净化（去除填充词）
- [ ] 支持加载自定义词汇表JSON文件

**验收标准**：输入含"Sai AI"的文本，输出前被自动替换为"CLI"

### Phase 4: 大模型集成
- [ ] 创建 `config.py`，管理环境变量读取
  - `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / `QWEN_API_KEY`
  - 默认模型映射：`deepseek`→`deepseek-chat`, `gpt4`→`gpt-4-turbo`
- [ ] 实现 `LLMClient` 类，统一封装：
  - 支持DeepSeek/OpenAI/通义千问（OpenAI兼容格式）
  - 流式响应处理，实时写入文件（避免内存溢出）
  - 超时重试机制（3次指数退避）
  - Token估算预警（输入>32K时警告）
- [ ] 实现中断处理：Ctrl+C时已完成内容保存为 `.partial.md`

**验收标准**：配置API密钥后，能成功调用模型并流式生成笔记

### Phase 5: 格式优化与扩展
- [ ] 添加 `--temperature` 参数控制创造性（日记可调高，周报调低）
- [ ] 添加 `--max-length` 参数控制输出长度（摘要模式）
- [ ] 支持输入JSON格式（视频转录工具的标准输出，含segments）
- [ ] 实现智能分段：超长文本自动切分，多轮调用后合并
- [ ] 添加 `--lang` 参数控制输出语言（中文/英文/双语）

**验收标准**：能处理1小时视频转录的完整JSON，生成连贯长笔记

### Phase 6: 工具化与文档
- [ ] 添加 `setup.py` 支持 `pip install -e .`
- [ ] 创建 `Makefile` 简化常用命令
- [ ] 编写完整README：安装、配置、使用示例、故障排查
- [ ] 提供示例文件：`example_transcript.txt`, `example_vocab.json`
- [ ] 编写词汇表扩展指南（如何为垂直领域定制）

**验收标准**：新用户能在10分钟内完成安装并生成第一份笔记

---

## 性能优化

### 瓶颈点分析与方案

| 瓶颈点 | 影响 | 优化方案 |
|--------|------|---------|
| **大模型API延迟** | 用户等待时间长，体验差 | 1. 流式响应，首Token到达即开始显示<br>2. 添加进度动画（tqdm模拟）<br>3. 支持本地缓存已生成笔记，避免重复调用 |
| **超长文本超限** | 超出模型上下文限制 | 1. 输入前Token估算（tiktoken）<br>2. 超长文本自动语义切分（按段落/主题聚类）<br>3. 多轮生成后智能合并（去重+衔接） |
| **API调用成本** | 频繁使用费用高 | 1. 提供 `--preview` 模式，先输出前500字确认格式<br>2. 支持本地轻量模型兜底（Ollama接口，可选）<br>3. 结果缓存：相同输入MD5直接返回缓存 |
| **词汇表遗漏** | 专业术语未纠正，笔记质量差 | 1. 支持自定义词汇表热加载<br>2. 记录未匹配的高频错词，提示用户补充<br>3. 提供领域模板（前端/AI/医疗/法律） |
| **文件IO阻塞** | 大文件读取卡顿 | 1. 流式读取大文本（生成器模式）<br>2. 异步写入输出文件<br>3. 临时文件原子写入，完成后rename |

### 关键设计决策

1. **流式生成优先**：不等待完整响应，收到首块内容即写入文件，降低内存占用
2. **失败降级策略**：主模型失败→尝试备用模型→本地模型（如配置）→输出预处理后的原文+错误提示
3. **幂等性保障**：相同输入+相同参数=相同输出（温度设为0时），便于测试和缓存

---

## 产出

规划完成后，将规则文档输出到 `.plan/t2n-plan.md` 文件中，包含：
- 项目目标与技术约束
- 项目结构与功能范围
- 命令行使用方式与依赖清单
- 分阶段功能拆解（Phase 1-6）
- 性能优化方案
- 交付标准与验收条件

后续开发严格按Phase推进，每阶段完成后更新计划状态。
```

---

这份需求文档保持了与 `v2t-plan.md` 一致的风格：简洁实用、约束明确、阶段清晰。需要我补充任何特定领域的词汇表示例，或者调整技术选型吗？