#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

# Windows控制台UTF-8编码设置
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
Prompts Loader - 动态提示词加载模块

支持从 prompts/ 文件夹加载提示词模板文件：
- system.md - 基础系统提示词
- note.md - 技术笔记提示词
- weekly.md - 周报提示词
- diary.md - 日记提示词

用户可以添加自定义提示词文件，通过 --format 参数指定
"""

import re
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# 默认提示词目录
DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class PromptTemplate:
    """提示词模板数据结构"""
    name: str                    # 模板名称（如 note, weekly, diary）
    system_prompt: str           # 系统提示词
    format_instruction: str      # 格式说明
    few_shot_example: str        # Few-shot 示例
    task_template: str           # 任务模板（包含 {{text}} 占位符）
    has_vocab_placeholder: bool  # 是否包含词汇表占位符


class PromptLoader:
    """
    提示词加载器

    从 prompts/ 目录加载 .md 格式的提示词文件
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        初始化提示词加载器

        【参数】
            prompts_dir: 提示词目录，默认为项目根目录下的 prompts/
        """
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self._cache: Dict[str, PromptTemplate] = {}

    def _parse_prompt_file(self, content: str) -> PromptTemplate:
        """
        解析提示词文件内容

        【格式约定】
        - 以 # 开头的一级标题表示模板名称
        - ## 角色设定 部分作为 system_prompt
        - ## 输出格式 部分作为 format_instruction
        - ## Few-shot 示例 部分作为 few_shot_example
        - ## 任务 部分作为 task_template

        【参数】
            content: 文件内容

        【返回】
            PromptTemplate: 解析后的模板
        """
        # 提取模板名称（第一个一级标题）
        name_match = re.search(r'^#\s+(.+?)\s+Prompt', content, re.MULTILINE)
        name = name_match.group(1).lower() if name_match else "unknown"

        # 提取各个部分 - 使用更精确的模式匹配
        system_prompt = self._extract_section(content, "角色设定")
        format_instruction = self._extract_section(content, "输出格式")
        few_shot_example = self._extract_section(content, "Few-shot")
        task_template = self._extract_section(content, "任务")

        # 如果提取失败，尝试备用方案
        if not system_prompt:
            # 尝试匹配 ## 角色设定 到 ## 输出格式
            match = re.search(r'##\s*角色设定\s*\n(.*?)(?=##\s*输出格式)', content, re.DOTALL)
            if match:
                system_prompt = match.group(1).strip()

        if not format_instruction:
            match = re.search(r'##\s*输出格式\s*\n(.*?)(?=##\s*Few-shot|##\s*任务|$)', content, re.DOTALL)
            if match:
                format_instruction = match.group(1).strip()

        if not few_shot_example:
            match = re.search(r'##\s*Few-shot.*?\n(.*?)(?=##\s*任务|$)', content, re.DOTALL)
            if match:
                few_shot_example = match.group(1).strip()

        if not task_template:
            match = re.search(r'##\s*任务\s*\n(.*)', content, re.DOTALL)
            if match:
                task_template = match.group(1).strip()

        # 检查是否包含词汇表占位符
        has_vocab_placeholder = "{{vocab}}" in task_template or "{{#if vocab}}" in task_template

        return PromptTemplate(
            name=name,
            system_prompt=system_prompt,
            format_instruction=format_instruction,
            few_shot_example=few_shot_example,
            task_template=task_template,
            has_vocab_placeholder=has_vocab_placeholder
        )

    def _extract_section(self, content: str, section_name: str) -> str:
        """
        提取指定章节的内容

        【参数】
            content: 完整内容
            section_name: 章节名称

        【返回】
            str: 章节内容（不包含章节标题本身）
        """
        # 将内容按行分割
        lines = content.split('\n')

        # 查找章节开始行
        start_line = -1
        header_pattern = f"## {section_name}"

        for i, line in enumerate(lines):
            if line.strip().lower().startswith(header_pattern.lower()):
                start_line = i + 1  # 内容从标题下一行开始
                break

        if start_line < 0:
            return ""

        # 查找下一个一级章节标题（## 开头但不是 ### 开头）
        # 注意：需要跳过代码块内的标题
        end_line = len(lines)
        in_code_block = False

        for i in range(start_line, len(lines)):
            line = lines[i].strip()

            # 检测代码块边界
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue

            # 只在代码块外检测章节标题
            if not in_code_block and line.startswith('## ') and not line.startswith('### '):
                # 检查是否是另一个主要章节
                if not line.lower().startswith(f'## {section_name}'.lower()):
                    end_line = i
                    break

        # 提取内容
        section_lines = lines[start_line:end_line]
        return '\n'.join(section_lines).strip()

    def load_template(self, format_type: str) -> PromptTemplate:
        """
        加载指定类型的提示词模板

        【参数】
            format_type: 笔记类型（note/weekly/diary 或自定义名称）

        【返回】
            PromptTemplate: 提示词模板

        【异常】
            FileNotFoundError: 模板文件不存在
        """
        # 检查缓存
        if format_type in self._cache:
            return self._cache[format_type]

        # 构建文件路径
        file_path = self.prompts_dir / f"{format_type}.md"

        if not file_path.exists():
            available = self.list_available_templates()
            raise FileNotFoundError(
                f"提示词模板不存在: {file_path}\n"
                f"可用模板: {', '.join(available)}"
            )

        # 读取并解析文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            template = self._parse_prompt_file(content)

            # 如果没有单独的系统提示词，尝试加载 system.md
            if not template.system_prompt:
                system_path = self.prompts_dir / "system.md"
                if system_path.exists():
                    with open(system_path, 'r', encoding='utf-8') as f:
                        template.system_prompt = f.read()

            # 缓存模板
            self._cache[format_type] = template

            logger.debug(f"已加载提示词模板: {format_type}")
            return template

        except Exception as e:
            logger.error(f"加载提示词模板失败: {file_path} - {e}")
            raise

    def list_available_templates(self) -> List[str]:
        """
        列出所有可用的提示词模板

        【返回】
            List[str]: 模板名称列表（不含 .md 扩展名）
        """
        if not self.prompts_dir.exists():
            return []

        templates = []
        for f in self.prompts_dir.glob("*.md"):
            # 排除 system.md（基础提示词，不是完整模板）
            if f.stem != "system":
                templates.append(f.stem)

        return sorted(templates)

    def build_prompt(self, format_type: str, text: str,
                     vocab: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        构建完整的提示词

        【参数】
            format_type: 笔记类型
            text: 原始文本内容
            vocab: 词汇表（可选）

        【返回】
            Dict[str, str]: 包含 system 和 user 的提示词字典
        """
        template = self.load_template(format_type)

        # 构建系统提示词
        system_parts = [
            template.system_prompt,
            template.format_instruction,
            template.few_shot_example
        ]
        system_prompt = "\n\n".join(filter(None, system_parts))

        # 构建用户提示词
        user_prompt = template.task_template

        # 替换 {{text}} 占位符
        user_prompt = user_prompt.replace("{{text}}", text)

        # 处理词汇表
        if vocab and template.has_vocab_placeholder:
            vocab_text = self._format_vocab(vocab)
            # 替换 {{vocab}} 或 {{#if vocab}}...{{/if}}
            user_prompt = re.sub(
                r'\{\{#if\s+vocab\}\}(.*?)\{\{/if\}\}',
                lambda m: m.group(1) if vocab else "",
                user_prompt,
                flags=re.DOTALL
            )
            user_prompt = user_prompt.replace("{{vocab}}", vocab_text)
        else:
            # 移除条件块
            user_prompt = re.sub(
                r'\{\{#if\s+vocab\}\}.*?\{\{/if\}\}',
                '',
                user_prompt,
                flags=re.DOTALL
            )
            user_prompt = user_prompt.replace("{{vocab}}", "")

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def _format_vocab(self, vocab: Dict[str, str]) -> str:
        """
        格式化词汇表

        【参数】
            vocab: 词汇表字典

        【返回】
            str: 格式化后的词汇表文本
        """
        lines = ["### 词汇表纠错参考\n"]
        lines.append("在理解以下文本时，请注意这些可能的语音识别错误：\n")

        for wrong, correct in vocab.items():
            lines.append(f'- "{wrong}" → "{correct}"')

        lines.append("\n请根据上下文自动纠正常见的语音识别错误。\n")

        return "\n".join(lines)

    def build_messages(self, format_type: str, text: str,
                       vocab: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        构建完整的对话消息列表（用于OpenAI兼容API）

        【参数】
            format_type: 笔记类型
            text: 原始文本内容
            vocab: 词汇表（可选）

        【返回】
            List[Dict[str, str]]: 消息列表
        """
        prompts = self.build_prompt(format_type, text, vocab)

        return [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]


# =============================================================================
# 便捷函数
# =============================================================================

def get_prompt_loader(prompts_dir: Optional[Path] = None) -> PromptLoader:
    """
    获取提示词加载器实例

    【参数】
        prompts_dir: 提示词目录（可选）

    【返回】
        PromptLoader: 提示词加载器实例
    """
    return PromptLoader(prompts_dir)


def list_templates(prompts_dir: Optional[Path] = None) -> List[str]:
    """
    列出所有可用的提示词模板

    【参数】
        prompts_dir: 提示词目录（可选）

    【返回】
        List[str]: 模板名称列表
    """
    loader = PromptLoader(prompts_dir)
    return loader.list_available_templates()


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PromptLoader 测试")
    print("=" * 60)

    loader = get_prompt_loader()

    # 列出可用模板
    print("\n【可用模板】")
    templates = loader.list_available_templates()
    for t in templates:
        print(f"  - {t}")

    # 测试加载 note 模板
    if "note" in templates:
        print("\n【Note 模板预览】")
        template = loader.load_template("note")
        print(f"  名称: {template.name}")
        print(f"  System长度: {len(template.system_prompt)} 字符")
        print(f"  Format长度: {len(template.format_instruction)} 字符")
        print(f"  Few-shot长度: {len(template.few_shot_example)} 字符")
        print(f"  Task长度: {len(template.task_template)} 字符")
        print(f"  含词汇表占位符: {template.has_vocab_placeholder}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
