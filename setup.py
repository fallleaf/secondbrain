"""
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
        "fastembed>=0.8.0",
        "sqlite-vec>=0.1.7",
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
