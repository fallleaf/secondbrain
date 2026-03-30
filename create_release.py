"""
SecondBrain 版本发布脚本

自动化创建和发布 SecondBrain 的版本
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages


def create_version():
    """创建版本文件"""
    version_content = '''"""
SecondBrain 版本信息
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
'''
    
    with open("src/version.py", "w") as f:
        f.write(version_content)
    
    print("✅ 版本文件创建完成")


def create_setup_py():
    """创建 setup.py 文件"""
    setup_content = '''"""
SecondBrain setup.py

SecondBrain 的安装配置文件
"""

from setuptools import setup, find_packages

setup(
    name="secondbrain",
    version="1.0.0",
    description="SecondBrain - 基于优先级分类的 Obsidian Vault 管理工具",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourname/secondbrain",
    packages=find_packages("src"),
    package_data={
        "": ["*.md", "*.yaml", "*.yml"],
    },
    install_requires=[
        "mcp>=1.0.0",
        "sentence-transformers>=2.2.0",
        "faiss-cpu>=1.7.4",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "watchdog>=3.0.0",
        "rank-bm25>=0.2.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "secondbrain=src.server:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
'''
    
    with open("setup.py", "w") as f:
        f.write(setup_content)
    
    print("✅ setup.py 文件创建完成")


def create_dockerfile():
    """创建 Dockerfile"""
    dockerfile_content = '''# SecondBrain Docker 镜像

FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install -r requirements.txt

# 安装 SecondBrain
RUN pip install -e .

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["secondbrain"]
'''
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
    
    print("✅ Dockerfile 创建完成")


def create_readme():
    """创建 README.md"""
    readme_content = '''# SecondBrain

**基于优先级分类的 Obsidian Vault 管具**

SecondBrain 是一个基于优先级分类的 Obsidian Vault 管理工具，支持语义搜索、关键词搜索和混合检索。

## 🎯 特性

- 🔍 **混合检索**: Keyword (BM25) + Semantic (向量) + Priority 加权
- 📊 **优先级系统**: 1-9 间隔分级 (中央发文→网络收集)
- ⚡ **增量更新**: checksum 检测 + sqlite-vec 增量索引
- 🗂️ **多 Vault 支持**: 配置文件指定多个目录

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourname/secondbrain.git
cd secondbrain

# 安装依赖
pip install -r requirements.txt

# 安装为可编辑模式
pip install -e .
```

### 配置

```bash
# 创建配置目录
mkdir -p ~/.config/secondbrain

# 复制配置模板
cp config.example.yaml ~/.config/secondbrain/config.yaml
cp priority_config.example.yaml ~/.config/secondbrain/priority_config.yaml
```

### 运行

```bash
# 开发模式
python -m src.server

# 或作为 MCP 服务器
secondbrain
```

## 📋 工具

| 工具 | 功能 | 状态 |
|------|------|------|
| `semantic_search` | 语义搜索 (hybrid/semantic/keyword) | ✅ 可用 |
| `read_note` | 读取笔记 | ✅ 可用 |
| `write_note` | 创建/更新笔记 | ✅ 可用 |
| `list_notes` | 列出目录 | ✅ 可用 |
| `delete_note` | 软删除笔记 | ✅ 可用 |
| `move_note` | 移动/重命名 | ✅ 可用 |
| `search_notes` | 关键词搜索 | ✅ 可用 |
| `get_index_stats` | 索引统计 | ✅ 可用 |
| `rebuild_semantic_index` | 重建索引 | ✅ 可用 |
| `get_priority_config` | 优先级配置 | ✅ 可用 |

## 📊 优先级系统

| 优先级 | 标签 | 描述 | 保留期 | 权重 |
|--------|------|------|--------|------|
| 9 | central_gov | 中央政府、国家级文件 | Permanent | 2.0 |
| 7 | ministry_gov | 部委、省级文件 | 10 年 | 1.6 |
| 5 | company | 公司文档、项目文件 | 3 年 | 1.2 |
| 3 | personal_work | 个人工作笔记 | 1 年 | 1.0 |
| 1 | web | 网络收集、待验证 | 90 天 | 0.8 |

## 📚 文档

- [实施计划](docs/IMPLEMENTATION_PLAN_FULL.md)
- [API 文档](docs/API.md)
- [配置指南](docs/CONFIG.md)
- [部署指南](docs/DEPLOY.md)

## 📝 许可证

MIT License

## 👥 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发指南。
'''
    
    with open("README.md", "w") as f:
        f.write(readme_content)
    
    print("✅ README.md 创建完成")


def main():
    """主函数"""
    print("📦 创建 SecondBrain 发布文件...")
    
    # 创建版本文件
    create_version()
    
    # 创建 setup.py
    create_setup_py()
    
    # 创建 Dockerfile
    create_dockerfile()
    
    # 创建 README.md
    create_readme()
    
    print("✅ 所有发布文件创建完成!")


if __name__ == "__main__":
    main()