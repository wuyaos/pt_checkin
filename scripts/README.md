# 项目脚本

本目录包含项目开发和维护相关的脚本。

## 📋 脚本列表

### `test-build.py`
**用途**: 本地构建测试脚本  
**功能**: 验证GitHub Actions构建流程是否能正常工作  
**使用方法**:
```bash
python scripts/test-build.py
```

**测试内容**:
- 安装构建依赖
- 清理旧构建文件
- 构建wheel和源码包
- 检查包完整性
- 测试包导入
- 测试CLI功能

## 🚀 使用指南

### 发布前测试
在创建新版本标签前，建议运行构建测试：

```bash
# 1. 本地构建测试
python scripts/test-build.py

# 2. 如果测试通过，创建版本标签
git tag v1.2.0
git push origin v1.2.0
```

### 开发环境设置
```bash
# 安装开发依赖
pip install -e .
pip install build twine wheel pytest

# 运行测试
python scripts/test-build.py
```

## 📝 维护说明

### 添加新脚本
1. 在此目录创建脚本文件
2. 添加适当的文档注释
3. 更新此README文件
4. 确保脚本具有可执行权限

### 脚本规范
- 使用Python 3.8+兼容语法
- 包含详细的文档字符串
- 提供清晰的错误信息
- 支持命令行参数（如需要）
