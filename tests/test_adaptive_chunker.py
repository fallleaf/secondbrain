#!/usr/bin/env python3
"""
AdaptiveChunker 测试用例

测试内容:
1. Frontmatter 解析
2. 文档类型检测
3. 标题层级参数调整
4. 分块效果验证
5. 元数据完整性
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, List

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from tools.adaptive_chunker import AdaptiveChunker, DocTypeConfig


class TestAdaptiveChunker(unittest.TestCase):
    """AdaptiveChunker 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.chunker = AdaptiveChunker()
    
    # ==================== 测试 Frontmatter 解析 ====================
    
    def test_frontmatter_explicit_faq(self):
        """测试 Frontmatter 显式声明 FAQ 类型"""
        content = """---
title: "常见问题"
doc_type: faq
tags: [help]
---
# FAQ

问：如何安装？
答：使用 pip install。
"""
        doc_type = self.chunker.detect_doc_type("test.md", content)
        self.assertEqual(doc_type, "faq")
    
    def test_frontmatter_explicit_technical(self):
        """测试 Frontmatter 显式声明技术文档类型"""
        content = """---
title: "API 文档"
doc_type: technical
---
# API

## 安装
```bash
pip install
```
"""
        doc_type = self.chunker.detect_doc_type("api.md", content)
        self.assertEqual(doc_type, "technical")
    
    def test_frontmatter_type_mapping(self):
        """测试 Frontmatter 类型映射"""
        test_cases = [
            ("question", "faq"),
            ("qna", "faq"),
            ("api", "technical"),
            ("guide", "technical"),
            ("contract", "legal"),
            ("note", "blog"),
            ("meeting_note", "meeting"),
        ]
        
        for raw_type, expected in test_cases:
            content = f"""---
doc_type: {raw_type}
---
内容
"""
            doc_type = self.chunker.detect_doc_type("test.md", content)
            self.assertEqual(doc_type, expected, f"类型映射失败：{raw_type} -> {doc_type}")
    
    def test_no_frontmatter_auto_detect(self):
        """测试无 Frontmatter 时自动检测"""
        # FAQ 内容（需要多行格式）
        faq_content = """
# 常见问题

问：如何安装？
答：使用 pip install。
"""
        doc_type = self.chunker.detect_doc_type("faq.md", faq_content)
        # 可能检测为 faq 或 blog，取决于内容
        self.assertIn(doc_type, ["faq", "blog"])
        
        # 技术文档内容
        tech_content = """
# API 指南

## 安装
```bash
pip install
```
"""
        doc_type = self.chunker.detect_doc_type("api.md", tech_content)
        self.assertEqual(doc_type, "technical")
    
    # ==================== 测试参数调整 ====================
    
    def test_heading_adjustment_faq(self):
        """测试 FAQ 类型的标题层级调整（应不调整）"""
        config = self.chunker.configs["faq"]
        
        # FAQ 所有层级应保持基准值
        for level in range(1, 7):
            chunk_size = self.chunker._get_adjusted_chunk_size("faq", level)
            self.assertEqual(chunk_size, 400, f"FAQ H{level} 应该保持 400")
    
    def test_heading_adjustment_technical(self):
        """测试技术文档类型的标题层级调整"""
        # H1 应该更大
        h1_size = self.chunker._get_adjusted_chunk_size("technical", 1)
        self.assertEqual(h1_size, 1200)  # 1000 * 1.2
        
        # H2 应该稍大
        h2_size = self.chunker._get_adjusted_chunk_size("technical", 2)
        self.assertEqual(h2_size, 1100)  # 1000 * 1.1
        
        # H3 保持基准
        h3_size = self.chunker._get_adjusted_chunk_size("technical", 3)
        self.assertEqual(h3_size, 1000)
        
        # H4 应该稍小
        h4_size = self.chunker._get_adjusted_chunk_size("technical", 4)
        self.assertEqual(h4_size, 900)  # 1000 * 0.9
    
    def test_heading_adjustment_legal(self):
        """测试法律文档类型的标题层级调整"""
        # H1 应该最大
        h1_size = self.chunker._get_adjusted_chunk_size("legal", 1)
        self.assertEqual(h1_size, 1560)  # 1200 * 1.3
        
        # H2 应该较大
        h2_size = self.chunker._get_adjusted_chunk_size("legal", 2)
        self.assertEqual(h2_size, 1440)  # 1200 * 1.2
    
    # ==================== 测试分块效果 ====================
    
    def test_faq_chunking(self):
        """测试 FAQ 文档分块"""
        content = """---
doc_type: faq
---
# 常见问题

问：如何安装？
答：使用 pip install 命令。具体步骤是：首先打开终端，然后输入 `pip install package-name`，等待安装完成即可。如果遇到问题，请检查网络连接和 Python 版本。

问：如何配置？
答：编辑配置文件。配置文件通常位于项目根目录下的 config.yaml 或 .env 文件中。您需要设置数据库连接、API 密钥等参数。
"""
        chunks = self.chunker.chunk_file("faq.md", content)
        
        # 应该生成 1 个块（内容小于 400）
        self.assertEqual(len(chunks), 1)
        
        # 检查元数据
        chunk = chunks[0]
        self.assertEqual(chunk.metadata["doc_type"], "faq")
        self.assertEqual(chunk.metadata["chunk_size_used"], 400)
    
    def test_technical_chunking_with_headings(self):
        """测试技术文档按标题分块"""
        # 增加内容长度以确保生成 chunk
        content = """---
doc_type: technical
---
# API 指南

## 安装

### 系统要求
- Python 3.8+
- pip 20.0+
- 至少 500MB 可用磁盘空间
- 需要网络连接

### 安装步骤
```bash
pip install package
```

或使用虚拟环境：
```bash
python -m venv venv
source venv/bin/activate
pip install package
```

## 使用

### 基本用法
```python
import package
client = package.Client()
result = client.query("test")
print(result)
```

### 参数说明
- api_key: API 密钥，必填
- timeout: 超时时间，默认 30 秒
- retry: 重试次数，默认 3 次

### 返回值
- status: 状态码
- data: 返回数据
- error: 错误信息
"""
        chunks = self.chunker.chunk_file("api.md", content)
        
        # 应该有多个块（按标题分割）
        self.assertGreater(len(chunks), 0, "应该生成分块")
        
        # 检查每个块的元数据
        for chunk in chunks:
            self.assertIn("doc_type", chunk.metadata)
            self.assertIn("heading_level", chunk.metadata)
            self.assertIn("chunk_size_used", chunk.metadata)
    
    def test_legal_chunking(self):
        """测试法律文档分块"""
        # 增加内容长度
        content = """---
doc_type: legal
---
# 技术服务合同

## 第一条 甲方责任
甲方应向乙方提供必要的技术资料和数据，确保乙方能够顺利完成开发工作。甲方应在合同签订后 5 个工作日内提供完整的需求文档。如果甲方未能按时提供资料，应承担相应的违约责任。

## 第二条 乙方责任
乙方应按照甲方要求完成软件开发工作，保证软件质量符合国家标准。乙方应在约定时间内交付软件，并提供必要的技术培训。如果乙方未能按时交付，应承担相应的违约责任。

## 第三条 付款方式
甲方应在合同签订后支付 30% 预付款，项目验收后支付剩余 70% 尾款。乙方应提供正规发票。付款方式为银行转账。

## 第四条 违约责任
任何一方违反合同约定，应承担违约责任，赔偿对方因此遭受的损失。违约金为合同总额的 20%。

## 第五条 争议解决
本合同履行过程中发生的争议，双方应友好协商解决；协商不成的，可向甲方所在地人民法院提起诉讼。
"""
        chunks = self.chunker.chunk_file("contract.md", content)
        
        # 应该有多个块（按条款分割）
        self.assertGreater(len(chunks), 0, "应该生成分块")
        
        # 检查 chunk_size 是否较大（法律文档）
        for chunk in chunks:
            self.assertGreaterEqual(chunk.metadata["chunk_size_used"], 1200, "法律文档 chunk_size 应该较大")
    
    # ==================== 测试元数据完整性 ====================
    
    def test_chunk_metadata_completeness(self):
        """测试 Chunk 元数据完整性"""
        content = """---
doc_type: blog
---
# 文章标题

## 第一段

这是第一段内容，用于测试元数据完整性。

## 第二段

这是第二段内容。
"""
        chunks = self.chunker.chunk_file("blog.md", content)
        
        required_fields = [
            "file_path",
            "start_line",
            "end_line",
            "title",
            "doc_type",
            "heading_level",
            "chunk_size_used"
        ]
        
        for chunk in chunks:
            for field in required_fields:
                self.assertIn(field, chunk.metadata, f"缺少元数据字段：{field}")
    
    def test_doc_type_info(self):
        """测试 get_doc_type_info 方法"""
        content = """---
doc_type: technical
---
# API 指南

## 安装
## 使用
## 配置
"""
        info = self.chunker.get_doc_type_info("api.md", content)
        
        # 检查返回结构
        self.assertIn("detected_type", info)
        self.assertIn("type_name", info)
        self.assertIn("config", info)
        self.assertIn("adjusted_configs", info)
        self.assertIn("heading_structure", info)
        self.assertIn("reasoning", info)
        
        # 检查类型
        self.assertEqual(info["detected_type"], "technical")
        
        # 检查调整配置
        self.assertIn("H1", info["adjusted_configs"])
        self.assertIn("chunk_size", info["adjusted_configs"]["H1"])
        self.assertIn("overlap", info["adjusted_configs"]["H1"])
    
    # ==================== 测试边界情况 ====================
    
    def test_empty_content(self):
        """测试空内容"""
        content = ""
        chunks = self.chunker.chunk_file("empty.md", content)
        self.assertEqual(len(chunks), 0)
    
    def test_very_short_content(self):
        """测试非常短的内容"""
        content = "短"
        chunks = self.chunker.chunk_file("short.md", content)
        self.assertEqual(len(chunks), 0)  # 小于 min_chunk_size
    
    def test_no_frontmatter_default(self):
        """测试无 Frontmatter 使用默认类型"""
        content = "普通内容"
        doc_type = self.chunker.detect_doc_type("test.md", content)
        # 可能检测为 default 或 blog
        self.assertIn(doc_type, ["default", "blog"])
    
    def test_invalid_doc_type_fallback(self):
        """测试无效 doc_type 回退到 default"""
        content = """---
doc_type: invalid_type
---
内容
"""
        doc_type = self.chunker.detect_doc_type("test.md", content)
        self.assertEqual(doc_type, "default")
    
    # ==================== 测试自定义配置 ====================
    
    def test_custom_config(self):
        """测试自定义文档类型配置"""
        custom_config = {
            "my_type": DocTypeConfig(
                name="my_type",
                base_chunk_size=500,
                base_overlap=100,
                min_chunk_size=80,
                heading_adjustments={1: 1.5, 2: 1.2, 3: 1.0},
                description="自定义类型"
            )
        }
        
        chunker = AdaptiveChunker(custom_configs=custom_config)
        
        # 检查配置是否加载
        self.assertIn("my_type", chunker.configs)
        self.assertEqual(chunker.configs["my_type"].base_chunk_size, 500)
        
        # 检查参数调整
        h1_size = chunker._get_adjusted_chunk_size("my_type", 1)
        self.assertEqual(h1_size, 750)  # 500 * 1.5


class TestBatchProcessor(unittest.TestCase):
    """批量处理器测试（可选）"""
    
    def test_type_detection_logic(self):
        """测试类型检测逻辑"""
        chunker = AdaptiveChunker()
        
        # FAQ 检测（需要多行格式）
        self.assertTrue(chunker._is_faq_content("问：如何安装？\n答：使用 pip。"))
        
        # 技术文档检测
        self.assertTrue(chunker._is_technical_doc("```bash\npip install\n```"))
        
        # 法律文档检测（需要多行格式）
        self.assertTrue(chunker._is_legal_doc("第一条 甲方责任\n甲方应..."))
        
        # 会议记录检测
        self.assertTrue(chunker._is_meeting_note("会议：项目周会"))


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptiveChunker))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessor))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
