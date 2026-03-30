"""
优先级分类器

根据文件路径推断优先级，计算搜索权重
"""

import os
import fnmatch
from typing import Dict, Optional, Tuple
import yaml


class PriorityClassifier:
    """优先级分类器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化优先级分类器
        
        Args:
            config_path: 优先级配置文件路径
        """
        self.config_path = config_path or "~/.config/secondbrain/priority_config.yaml"
        self.config_path = os.path.expanduser(self.config_path)
        self.config: Optional[Dict] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """加载优先级配置"""
        if not os.path.exists(self.config_path):
            # 如果配置文件不存在，使用默认配置
            self.config = self._get_default_config()
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
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
    
    def infer_priority(self, file_path: str) -> Tuple[int, str, str]:
        """
        根据文件路径推断优先级
        
        Args:
            file_path: 文件路径 (相对于 vault 根目录)
            
        Returns:
            Tuple[int, str, str]: (优先级，来源类型，子分类)
        """
        # 标准化路径
        file_path = file_path.strip("/")
        file_path = file_path.replace("\\", "/")
        
        # 获取文件所在目录
        file_dir = os.path.dirname(file_path)

        # 按优先级从高到低匹配
        priority_levels = (self.config or {}).get("priority_levels") or []

        for level in priority_levels:
            priority = level.get("priority", 0)
            patterns = level.get("path_patterns") or []

            # 检查是否匹配任何模式
            for pattern in patterns:
                if self._match_pattern(file_dir, pattern):
                    # 检查子分类
                    sub_category = self._get_sub_category(file_dir, level)
                    source_type = level.get("label", f"priority_{priority}")

                    return priority, source_type, sub_category

        # 默认优先级
        default = (self.config or {}).get("default") or {}
        return (
            default.get("priority", 3),
            "unknown",
            ""
        )
    
    def _match_pattern(self, file_dir: str, pattern: str) -> bool:
        """
        检查目录是否匹配模式
        
        Args:
            file_dir: 文件目录
            pattern: 模式 (支持 * 通配符)
            
        Returns:
            bool: 是否匹配
        """
        # 将模式转换为 fnmatch 格式
        # 例如: "07.项目/国家政策/*" -> "07.项目/国家政策/*"
        pattern = pattern.replace("\\", "/")
        
        # 检查是否完全匹配或前缀匹配
        if pattern.endswith("/*"):
            # 前缀匹配
            prefix = pattern[:-2]
            return file_dir == prefix or file_dir.startswith(prefix + "/")
        else:
            # 精确匹配
            return file_dir == pattern or fnmatch.fnmatch(file_dir, pattern)
    
    def _get_sub_category(self, file_dir: str, level: Dict) -> str:
        """
        获取子分类
        
        Args:
            file_dir: 文件目录
            level: 优先级级别配置
            
        Returns:
            str: 子分类名称
        """
        sub_categories = level.get("sub_categories", [])
        
        for sub_cat in sub_categories:
            patterns = sub_cat.get("patterns", [])
            for pattern in patterns:
                if self._match_pattern(file_dir, pattern):
                    return sub_cat.get("name", "")
        
        return ""
    
    def get_search_weight(self, priority: int) -> float:
        """
        获取优先级的搜索权重
        
        Args:
            priority: 优先级 (1-9)
            
        Returns:
            float: 搜索权重
        """
        priority_levels = self.config.get("priority_levels", [])
        
        for level in priority_levels:
            if level["priority"] == priority:
                return level.get("search_weight", 1.0)
        
        # 默认权重
        return self.config.get("default") or {}.get("search_weight", 1.0)
    
    def get_retention_days(self, priority: int) -> Optional[int]:
        """
        获取优先级的保留天数
        
        Args:
            priority: 优先级 (1-9)
            
        Returns:
            Optional[int]: 保留天数，None 表示永久保留
        """
        priority_levels = self.config.get("priority_levels", [])
        
        for level in priority_levels:
            if level["priority"] == priority:
                return level.get("retention_days")
        
        # 默认保留天数
        return self.config.get("default") or {}.get("retention_days", 365)
    
    def get_priority_label(self, priority: int) -> str:
        """
        获取优先级的标签
        
        Args:
            priority: 优先级 (1-9)
            
        Returns:
            str: 标签名称
        """
        priority_levels = self.config.get("priority_levels", [])
        
        for level in priority_levels:
            if level["priority"] == priority:
                return level.get("label", f"priority_{priority}")
        
        return "unknown"
    
    def get_priority_description(self, priority: int) -> str:
        """
        获取优先级的描述
        
        Args:
            priority: 优先级 (1-9)
            
        Returns:
            str: 描述文本
        """
        priority_levels = self.config.get("priority_levels", [])
        
        for level in priority_levels:
            if level["priority"] == priority:
                return level.get("description", "")
        
        return ""


# 全局实例
_classifier: Optional[PriorityClassifier] = None


def get_classifier(config_path: Optional[str] = None) -> PriorityClassifier:
    """
    获取全局优先级分类器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        PriorityClassifier: 分类器实例
    """
    global _classifier
    
    if _classifier is None:
        _classifier = PriorityClassifier(config_path)
    
    return _classifier


if __name__ == "__main__":
    # 测试优先级分类器
    classifier = PriorityClassifier()
    
    test_paths = [
        "07.项目/国家政策/国务院文件.md",
        "05.工作/项目 A/需求文档.md",
        "03.日记/2026-03-27.md",
        "02.收集/网页文章.md",
        "unknown/path/file.md",
    ]
    
    print("🔍 优先级分类测试")
    print("-" * 50)
    
    for path in test_paths:
        priority, source_type, sub_cat = classifier.infer_priority(path)
        weight = classifier.get_search_weight(priority)
        label = classifier.get_priority_label(priority)
        
        print(f"📄 {path}")
        print(f"   优先级：{priority} ({label})")
        print(f"   来源：{source_type}")
        print(f"   子分类：{sub_cat or '-'}")
        print(f"   权重：{weight}")
        print()
