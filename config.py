#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# 默认配置常量
# =============================================================================

# 模型默认配置 (DashScope)
DEFAULT_MODEL_CONFIGS = {
    "qwen3-max": {
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url_env": "DASHSCOPE_BASE_URL",
        "default_base_url": "https://dashscope.aliyuncs.com/api/v1",
        "model_name": "qwen3-max",  # 通义千问3 Max
        "max_tokens": 8192,
        "temperature": 0.7,
    },
}

# 默认模型
DEFAULT_MODEL = "qwen"

# 支持的模型列表
SUPPORTED_MODELS = list(DEFAULT_MODEL_CONFIGS.keys())


# =============================================================================
# 配置类
# =============================================================================

@dataclass
class ModelConfig:
    """模型配置数据结构"""
    name: str                    # 模型标识名
    api_key: str                 # API 密钥
    base_url: str                # API 基础 URL
    model_name: str              # 具体模型名称
    max_tokens: int              # 最大生成 Token 数
    temperature: float           # 温度参数


class Config:
    """
    配置管理器

    从 .env 文件加载环境变量，提供配置获取接口。
    """

    def __init__(self, env_file: Optional[Path] = None):
        """
        初始化配置管理器

        【参数】
            env_file: .env 文件路径，默认为项目根目录下的 .env
        """
        self._config: Dict[str, str] = {}
        self._env_file = env_file or self._find_env_file()
        self._load_env()

    def _find_env_file(self) -> Optional[Path]:
        """
        查找 .env 文件

        按以下顺序查找：
        1. 当前工作目录
        2. 项目根目录（包含 generate.py 的目录）
        3. 父目录

        【返回】
            Path: .env 文件路径，或 None
        """
        # 查找路径列表
        search_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent / ".env",
        ]

        for path in search_paths:
            if path.exists():
                logger.debug(f"找到 .env 文件: {path}")
                return path

        logger.warning("未找到 .env 文件，将使用环境变量")
        return None

    def _load_env(self) -> None:
        """
        加载 .env 文件内容

        解析 .env 文件，将非注释行加载到配置字典中。
        同时也会保留已有的环境变量。
        """
        # 先加载当前环境变量
        for key, value in os.environ.items():
            self._config[key] = value

        # 如果存在 .env 文件，解析并加载
        if self._env_file and self._env_file.exists():
            try:
                with open(self._env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过空行和注释行
                        if not line or line.startswith('#'):
                            continue
                        # 解析 KEY=VALUE 格式
                        if '=' in line:
                            # 只分割第一个等号，值中可能包含等号
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # 去除可能的引号包裹
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            # 只有环境变量不存在时才覆盖（环境变量优先级更高）
                            if key not in os.environ:
                                self._config[key] = value
                                os.environ[key] = value

                logger.info(f"已加载 .env 文件: {self._env_file}")
            except Exception as e:
                logger.warning(f"加载 .env 文件失败: {e}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置项

        【参数】
            key: 配置项名称
            default: 默认值

        【返回】
            str: 配置项值，或默认值
        """
        return self._config.get(key, default)

    def get_api_key(self, model: str) -> Optional[str]:
        """
        获取指定模型的 API 密钥

        【参数】
            model: 模型名称（deepseek/openai/qwen）

        【返回】
            str: API 密钥，或 None（未配置）
        """
        model = model.lower()
        if model not in DEFAULT_MODEL_CONFIGS:
            logger.error(f"不支持的模型: {model}")
            return None

        env_key = DEFAULT_MODEL_CONFIGS[model]["api_key_env"]
        api_key = self.get(env_key)

        if not api_key:
            logger.warning(f"未配置 {model} 的 API 密钥，请设置 {env_key}")

        return api_key

    def get_base_url(self, model: str) -> str:
        """
        获取指定模型的 API 基础 URL

        【参数】
            model: 模型名称

        【返回】
            str: API 基础 URL
        """
        model = model.lower()
        if model not in DEFAULT_MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model}")

        config = DEFAULT_MODEL_CONFIGS[model]
        env_key = config["base_url_env"]
        default_url = config["default_base_url"]

        return self.get(env_key, default_url)

    def get_model_name(self, model: str) -> str:
        """
        获取指定模型的具体模型名称

        【参数】
            model: 模型标识名

        【返回】
            str: 模型名称（如 deepseek-chat）
        """
        model = model.lower()
        if model not in DEFAULT_MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model}")

        return DEFAULT_MODEL_CONFIGS[model]["model_name"]

    def get_client_config(self, model: str) -> ModelConfig:
        """
        获取完整的客户端配置

        【参数】
            model: 模型名称

        【返回】
            ModelConfig: 完整的模型配置

        【异常】
            ValueError: 模型不支持
            RuntimeError: API 密钥未配置
        """
        model = model.lower()

        if model not in DEFAULT_MODEL_CONFIGS:
            available = ", ".join(SUPPORTED_MODELS)
            raise ValueError(f"不支持的模型: {model}。可用模型: {available}")

        api_key = self.get_api_key(model)
        if not api_key:
            env_key = DEFAULT_MODEL_CONFIGS[model]["api_key_env"]
            raise RuntimeError(
                f"未配置 {model} 的 API 密钥\n"
                f"请在 .env 文件中设置: {env_key}=your_api_key"
            )

        config = DEFAULT_MODEL_CONFIGS[model]

        return ModelConfig(
            name=model,
            api_key=api_key,
            base_url=self.get_base_url(model),
            model_name=self.get_model_name(model),
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )

    def is_model_configured(self, model: str) -> bool:
        """
        检查指定模型是否已配置 API 密钥

        【参数】
            model: 模型名称

        【返回】
            bool: 是否已配置
        """
        return self.get_api_key(model) is not None

    def list_configured_models(self) -> list:
        """
        列出所有已配置 API 密钥的模型

        【返回】
            list: 已配置模型名称列表
        """
        return [m for m in SUPPORTED_MODELS if self.is_model_configured(m)]


# =============================================================================
# 便捷函数
# =============================================================================

def get_config(env_file: Optional[Path] = None) -> Config:
    """
    获取配置管理器实例（单例模式）

    【参数】
        env_file: .env 文件路径（可选）

    【返回】
        Config: 配置管理器实例
    """
    if not hasattr(get_config, '_instance'):
        get_config._instance = Config(env_file)
    return get_config._instance


def get_default_model() -> str:
    """
    获取默认模型名称

    【返回】
        str: 默认模型名称
    """
    config = get_config()
    default = config.get("DEFAULT_MODEL", DEFAULT_MODEL)
    # 检查默认模型是否已配置
    if config.is_model_configured(default):
        return default
    # 如果没有配置默认模型，返回第一个已配置的模型
    configured = config.list_configured_models()
    if configured:
        return configured[0]
    return default
