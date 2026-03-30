"""
配置加载模块

负责加载、验证和管理 SecondBrain 配置文件
"""

import os
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class VaultIndexConfig(BaseModel):
    """Vault 独立索引配置"""
    semantic_db: Optional[str] = None  # 如果为 None，使用全局索引
    keyword_db: Optional[str] = None   # 如果为 None，使用全局索引

    @field_validator('semantic_db', 'keyword_db')
    @classmethod
    def expand_path(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return os.path.expanduser(v)
        return v


class VaultConfig(BaseModel):
    """Vault 配置"""
    path: str
    name: str
    enabled: bool = True
    index: VaultIndexConfig = Field(default_factory=VaultIndexConfig)

    @field_validator('path')
    @classmethod
    def expand_path(cls, v: str) -> str:
        """展开 ~ 符号"""
        return os.path.expanduser(v)


class SemanticIndexConfig(BaseModel):
    """语义索引配置"""
    enabled: bool = True
    model: str = "BAAI/bge-small-zh-v1.5"
    chunk_size: int = 800
    chunk_overlap: int = 150
    db_path: str = "~/.local/share/secondbrain/semantic_index.db"

    @field_validator('db_path')
    @classmethod
    def expand_db_path(cls, v: str) -> str:
        return os.path.expanduser(v)


class KeywordIndexConfig(BaseModel):
    """关键词索引配置"""
    enabled: bool = True
    backend: str = "sqlite_fts5"  # 或 "bm25"
    db_path: str = "~/.local/share/secondbrain/keyword_index.db"

    @field_validator('db_path')
    @classmethod
    def expand_db_path(cls, v: str) -> str:
        return os.path.expanduser(v)


class IndexConfig(BaseModel):
    """索引配置"""
    semantic: SemanticIndexConfig = Field(default_factory=SemanticIndexConfig)
    keyword: KeywordIndexConfig = Field(default_factory=KeywordIndexConfig)


class PriorityConfig(BaseModel):
    """优先级配置"""
    config_path: str = "~/.config/secondbrain/priority_config.yaml"
    enabled: bool = True
    default_priority: int = 3

    @field_validator('config_path')
    @classmethod
    def expand_config_path(cls, v: str) -> str:
        return os.path.expanduser(v)


class SecurityConfig(BaseModel):
    """安全配置"""
    max_read_size: int = 1048576  # 1MB
    max_batch_size: int = 20
    require_confirm_delete: bool = True
    excluded_dirs: List[str] = Field(default_factory=lambda: [".obsidian", ".trash", ".git"])


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    file: str = "~/.local/share/secondbrain/mcp.log"
    max_size: int = 10485760  # 10MB
    backup_count: int = 5

    @field_validator('file')
    @classmethod
    def expand_log_path(cls, v: str) -> str:
        return os.path.expanduser(v)


class Settings(BaseModel):
    """主配置类"""
    vaults: List[VaultConfig] = Field(default_factory=list)
    index: IndexConfig = Field(default_factory=IndexConfig)
    priority: PriorityConfig = Field(default_factory=PriorityConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator('vaults')
    @classmethod
    def validate_vaults(cls, v: List[VaultConfig]) -> List[VaultConfig]:
        if not v:
            raise ValueError("至少需要配置一个 Vault")
        return v

    def get_enabled_vaults(self) -> List[VaultConfig]:
        """获取启用的 Vault 列表"""
        return [v for v in self.vaults if v.enabled]

    def get_vault_by_name(self, name: str) -> Optional[VaultConfig]:
        """根据名称获取 Vault"""
        for vault in self.vaults:
            if vault.name == name:
                return vault
        return None


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径

    Returns:
        Settings: 配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
        ValueError: 配置验证失败
    """
    # 默认配置路径
    if config_path is None:
        config_path = os.environ.get(
            "SECOND_BRAIN_CONFIG",
            "~/.config/secondbrain/config.yaml"
        )

    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在：{config_path}")

    # 读取 YAML 文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    # 环境变量覆盖
    config_data = _apply_env_overrides(config_data)

    # 验证并创建配置对象
    return Settings(**config_data)


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用环境变量覆盖

    支持的环境变量:
        SECOND_BRAIN_VAULT_PATH: 覆盖第一个 Vault 路径
        SECOND_BRAIN_LOG_LEVEL: 覆盖日志级别
        SECOND_BRAIN_INDEX_MODEL: 覆盖嵌入模型
    """
    # Vault 路径覆盖
    if 'vaults' not in config:
        config['vaults'] = []

    vault_path = os.environ.get('SECOND_BRAIN_VAULT_PATH')
    if vault_path and config['vaults']:
        config['vaults'][0]['path'] = vault_path

    # 日志级别覆盖
    log_level = os.environ.get('SECOND_BRAIN_LOG_LEVEL')
    if log_level:
        if 'logging' not in config:
            config['logging'] = {}
        config['logging']['level'] = log_level

    # 嵌入模型覆盖
    index_model = os.environ.get('SECOND_BRAIN_INDEX_MODEL')
    if index_model:
        if 'index' not in config:
            config['index'] = {}
        if 'semantic' not in config['index']:
            config['index']['semantic'] = {}
        config['index']['semantic']['model'] = index_model

    return config


def create_default_config(output_path: Optional[str] = None) -> str:
    """
    创建默认配置文件

    Args:
        output_path: 输出路径，如果为 None 则使用默认路径

    Returns:
        str: 创建的配置文件路径
    """
    if output_path is None:
        output_path = "~/.config/secondbrain/config.yaml"

    output_path = os.path.expanduser(output_path)

    # 创建目录
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 默认配置
    default_config = {
        "vaults": [
            {
                "path": "~/NanobotMemory",
                "name": "personal",
                "enabled": True
            }
        ],
        "index": {
            "semantic": {
                "enabled": True,
                "model": "BAAI/bge-small-zh-v1.5",
                "chunk_size": 800,
                "chunk_overlap": 150,
                "db_path": "~/.local/share/secondbrain/semantic_index.db"
            },
            "keyword": {
                "enabled": True,
                "backend": "sqlite_fts5"
            }
        },
        "priority": {
            "config_path": "~/.config/secondbrain/priority_config.yaml",
            "enabled": True,
            "default_priority": 3
        },
        "security": {
            "max_read_size": 1048576,
            "max_batch_size": 20,
            "require_confirm_delete": True,
            "excluded_dirs": [".obsidian", ".trash", ".git"]
        },
        "logging": {
            "level": "INFO",
            "file": "~/.local/share/secondbrain/mcp.log",
            "max_size": 10485760,
            "backup_count": 5
        }
    }

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)

    return output_path


if __name__ == "__main__":
    # 测试配置加载
    import sys

    # 如果没有配置文件，创建默认配置
    default_path = "~/.config/secondbrain/config.yaml"
    if not os.path.exists(os.path.expanduser(default_path)):
        print(f"📝 创建默认配置文件：{default_path}")
        create_default_config()

    # 加载配置
    try:
        config = load_config()
        print("✅ 配置加载成功!")
        print(f"📁 Vault 数量：{len(config.vaults)}")
        print(f"🔍 语义索引：{config.index.semantic.enabled}")
        print(f"🔑 关键词索引：{config.index.keyword.enabled}")
        print(f"🔒 最大文件大小：{config.security.max_read_size / 1024 / 1024:.1f}MB")
        print(f"📊 日志级别：{config.logging.level}")
    except Exception as e:
        print(f"❌ 配置加载失败：{e}")
        sys.exit(1)
