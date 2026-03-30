# 贡献指南

欢迎为 SecondBrain 项目贡献代码！🎉

## 开发流程

### 1. Fork 项目
点击 GitHub 页面右上角的 "Fork" 按钮。

### 2. 克隆项目
```bash
git clone https://github.com/your-username/secondbrain.git
cd secondbrain
```

### 3. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 4. 安装依赖
```bash
pip install -e ".[dev]"
```

### 5. 创建特性分支
```bash
git checkout -b feature/amazing-feature
```

### 6. 开发并测试
- 遵循 PEP 8 代码规范
- 为新增功能编写测试
- 确保所有测试通过：`pytest`

### 7. 提交变更
```bash
git add .
git commit -m "feat: 添加新功能"
```

**提交信息规范**：
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档变更
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 8. 推送到分支
```bash
git push origin feature/amazing-feature
```

### 9. 创建 Pull Request
在 GitHub 上创建 Pull Request，描述变更内容和测试情况。

## 代码规范

### Python 风格
- 遵循 PEP 8
- 使用 4 空格缩进
- 函数和类使用 `snake_case`
- 常量使用 `UPPER_CASE`
- 类使用 `PascalCase`

### 文档
- 所有公共函数和类必须有 docstring
- 使用 Google 风格 docstring
- 中文注释使用简体中文

### 测试
- 新增功能必须包含单元测试
- 测试覆盖率不低于 80%
- 使用 `pytest` 运行测试

## 问题反馈

遇到问题或有建议？请创建 Issue：
- 描述问题或建议
- 提供复现步骤（如果是 bug）
- 附上相关日志或截图

## 许可证

贡献代码即表示您同意代码以 MIT 许可证发布。

感谢贡献！🙏
