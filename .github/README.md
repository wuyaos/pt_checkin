# GitHub Actions 工作流说明

本项目使用GitHub Actions实现自动化构建、发布和配置同步。

## 🔄 工作流概览

### 构建发布工作流 (`build-release.yml`)
- **触发条件**: 手动执行，项目更新时执行(已注释)
- **功能**:
  1. **编译打包**: 构建wheel文件和源码包
  2. **发布到Release**: 创建GitHub Release并上传构建产物
  3. **上传PyPI**: 自动发布到Python包索引
  4. **同步配置**: 将master分支的config_example.yml同步到ql分支
- **手动参数**:
  - `version`: 发布版本号 (例如: 1.2.0)
  - `prerelease`: 是否为预发布版本

## 🚀 使用指南

### 发布新版本

#### 手动执行 (推荐)
1. 进入GitHub仓库的Actions页面
2. 选择"Build and Release"工作流
3. 点击"Run workflow"
4. 输入版本号 (例如: 1.2.0)
5. 选择是否为预发布版本
6. 点击"Run workflow"执行

#### 自动执行 (已注释)
```bash
# 当前已注释，如需启用请修改工作流文件
# 推送到master分支或创建版本标签时自动执行
git tag v1.2.0
git push origin v1.2.0
```

### 工作流执行步骤

1. **更新版本号**: 自动更新pyproject.toml中的版本
2. **构建包**: 生成wheel文件和源码包
3. **创建Release**: 在GitHub创建发布页面并上传构建产物
4. **发布PyPI**: 自动上传到Python包索引
5. **同步配置**: 将config_example.yml同步到ql分支

## 🔧 配置要求

### PyPI发布配置
- 在GitHub仓库设置中配置PyPI的可信发布
- 或者在仓库Secrets中添加`PYPI_API_TOKEN`

### 权限要求
- `contents: write` - 用于创建GitHub Release
- `id-token: write` - 用于PyPI可信发布

## 📋 工作流状态

| 工作流 | 状态 | 描述 |
|--------|------|------|
| Build and Release | ✅ 启用 | 手动执行，包含完整发布流程 |

## 🔍 故障排除

### 常见问题

- **PyPI发布失败**: 检查版本号是否重复，确保PyPI配置正确
- **配置同步失败**: 检查ql分支是否存在，验证仓库权限
- **构建失败**: 检查pyproject.toml配置，确保依赖正确

### 调试方法

- 查看GitHub Actions日志详情
- 检查工作流文件语法
- 验证仓库权限和Secrets配置

## 📝 维护说明

### 版本管理

- 遵循语义化版本规范 (major.minor.patch)
- 手动执行工作流时输入正确的版本号
- 确保版本号递增，避免重复发布

### 定期维护

- 定期更新GitHub Actions版本
- 检查依赖包的安全性更新
- 监控PyPI发布状态
