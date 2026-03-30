"""
配置验证模块

使用 Pydantic 验证配置文件
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class PriorityLevelConfig(BaseModel):
    """优先级级别配置"""
    priority: int = Field(..., ge=1, le=9, description="优先级级别 (1-9)")
    label: str = Field(..., min_length=1, description="标签名称")
    description: str = Field(..., min_length=1, description="描述")
    retention_days: Optional[int] = Field(None, ge=-1, description="保留天数 (-1=永久)")
    search_weight: float = Field(..., gt=0, description="搜索权重")
    path_patterns: List[str] = Field(default_factory=list, description="路径模式列表")
    sub_categories: List[Dict[str, Any]] = Field(default_factory=list, description="子分类")

    @validator('retention_days')
    def validate_retention_days(cls, v):
        """验证保留天数"""
        if v is not None and v != -1 and v < 0:
            raise ValueError('保留天数必须为正数或 -1 (永久保留)')
        return v


class DefaultConfig(BaseModel):
    """默认配置"""
    priority: int = Field(3, ge=1, le=9, description="默认优先级")
    retention_days: int = Field(365, ge=0, description="默认保留天数")
    search_weight: float = Field(1.0, gt=0, description="默认搜索权重")


class PriorityConfig(BaseModel):
    """优先级配置"""
    priority_levels: List[PriorityLevelConfig] = Field(..., min_items=1, description="优先级级别列表")
    default: DefaultConfig = Field(default_factory=DefaultConfig, description="默认配置")

    @validator('priority_levels')
    def validate_priority_levels(cls, v):
        """验证优先级级别列表"""
        priorities = [level.priority for level in v]
        if len(priorities) != len(set(priorities)):
            raise ValueError('优先级级别不能重复')
        return v


class VaultConfig(BaseModel):
    """Vault 配置"""
    path: str = Field(..., min_length=1, description="Vault 路径")
    name: str = Field(..., min_length=1, description="Vault 名称")
    enabled: bool = Field(True, description="是否启用")


class IndexConfig(BaseModel):
    """索引配置"""
    semantic: Dict[str, Any] = Field(default_factory=dict, description="语义索引配置")
    keyword: Dict[str, Any] = Field(default_factory=dict, description="关键词索引配置")


class SecurityConfig(BaseModel):
    """安全配置"""
    max_read_size: int = Field(1024 * 1024, gt=0, description="最大读取文件大小 (字节)")
    max_batch_size: int = Field(20, gt=0, description="最大批量操作数量")
    require_delete_confirm: bool = Field(True, description="删除前是否需要确认")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field("INFO", description="日志级别")
    log_dir: Optional[str] = Field(None, description="日志目录")
    log_file: Optional[str] = Field(None, description="日志文件名")


class MainConfig(BaseModel):
    """主配置"""
    vaults: List[VaultConfig] = Field(..., min_items=1, description="Vault 配置列表")
    index: IndexConfig = Field(default_factory=IndexConfig, description="索引配置")
    priority: PriorityConfig = Field(..., description="优先级配置")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")

    @validator('vaults')
    def validate_vaults(cls, v):
        """验证 Vault 配置"""
        vault_names = [vault.name for vault in v]
        if len(vault_names) != len(set(vault_names)):
            raise ValueError('Vault 名称不能重复')
        return v


def validate_config(config_dict: Dict[str, Any]) -> MainConfig:
    """
    验证配置字典

    Args:
        config_dict: 配置字典

    Returns:
        MainConfig: 验证后的配置对象

    Raises:
        ValidationError: 配置验证失败
    """
    return MainConfig(**config_dict)


def get_default_priority_config() -> Dict[str, Any]:
    """
    获取默认优先级配置

    Returns:
        Dict[str, Any]: 默认优先级配置字典
    """
    return {
        "priority_levels": [
            {
                "priority": 9,
                "label": "central_gov",
                "description": "中央政府、国务院、国家级文件",
                "retention_days": None,
                "search_weight": 2.0,
                "path_patterns": ["07.项目/国家政策/*", "08.技术/国家标准/*"]
            },
            {
                "priority": 7,
                "label": "ministry_gov",
                "description": "部委、省级政府文件",
                "retention_days": 3650,
                "search_weight": 1.6,
                "path_patterns": ["07.项目/部委文件/*", "08.技术/行业标准/*"]
            },
            {
                "priority": 5,
                "label": "company",
                "description": "公司文档、项目文件",
                "retention_days": 1095,
                "search_weight": 1.2,
                "path_patterns": ["05.工作/*", "07.项目/*"]
            },
            {
                "priority": 3,
                "label": "personal_work",
                "description": "个人工作笔记",
                "retention_days": 365,
                "search_weight": 1.0,
                "path_patterns": ["03.日记/*", "06.学习/*"]
            },
            {
                "priority": 1,
                "label": "web",
                "description": "网络收集、待验证信息",
                "retention_days": 90,
                "search_weight": 0.8,
                "path_patterns": ["02.收集/*", "01.闪念/*"]
            }
        ],
        "default": {
            "priority": 3,
            "retention_days": 365,
            "search_weight": 1.0
        }
    }


if __name__ == "__main__":
    # 测试配置验证
    test_config = {
        "vaults": [
            {
                "path": "~/NanobotMemory",
                "name": "default",
                "enabled": True
            }
        ],
        "index": {},
        "priority": get_default_priority_config(),
        "security": {},
        "logging": {}
    }

    try:
        validated = validate_config(test_config)
        print("✅ 配置验证通过")
        print(f"Vault 数量：{len(validated.vaults)}")
        print(f"优先级级别数量：{len(validated.priority.priority_levels)}")
    except Exception as e:
        print(f"❌ 配置验证失败：{e}")
