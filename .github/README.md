# GitHub Actions 工作流说明

本项目使用GitHub Actions实现自动化构建、发布和配置同步。

## 🔄 工作流概览

### 构建发布工作流 (`build-release.yml`)
- **触发条件**: 手动执行，项目更新时执行(已注释)
- **功能**:
  1. **版本管理**: 自动获取或手动指定版本号
  2. **编译打包**: 构建wheel文件和源码包
  3. **发布到Release**: 可选择创建GitHub Release并上传构建产物
  4. **上传PyPI**: 可选择发布到Python包索引
  5. **同步配置**: 将master分支的config_example.yml同步到ql分支
- **手动参数**:
  - `version`: 发布版本号 (留空则自动从pyproject.toml获取)
  - `create_release`: 是否创建GitHub Release (默认: true)
  - `publish_pypi`: 是否发布到PyPI (默认: true)
  - `prerelease`: 是否为预发布版本 (默认: false)

## 🚀 使用指南

### 发布新版本

#### 手动执行 (推荐)

1. 进入GitHub仓库的Actions页面
2. 选择"Build and Release"工作流
3. 点击"Run workflow"
4. 配置参数：
   - **版本号**: 留空则自动从pyproject.toml获取，或手动输入 (例如: 1.2.0)
   - **创建Release**: 是否创建GitHub Release (默认: 是)
   - **发布PyPI**: 是否发布到PyPI (默认: 是)
   - **预发布版本**: 是否为预发布版本 (默认: 否)
5. 点击"Run workflow"执行

#### 自动执行 (已注释)
```bash
# 当前已注释，如需启用请修改工作流文件
# 推送到master分支或创建版本标签时自动执行
git tag v1.2.0
git push origin v1.2.0
```

### 工作流执行步骤

1. **版本管理**: 自动获取或手动更新pyproject.toml中的版本号
2. **构建包**: 生成wheel文件和源码包，并检查完整性
3. **创建Release**: 可选择在GitHub创建发布页面并上传构建产物
4. **发布PyPI**: 可选择自动上传到Python包索引
5. **同步配置**: 将config_example.yml同步到ql分支
6. **生成总结**: 显示执行结果和相关链接

## 🔧 配置要求

### PyPI发布配置

使用PyPI可信发布（Trusted Publishing），无需管理API Token，更安全便捷。

**配置步骤**:

1. **在PyPI中配置Trusted Publisher**:
   - 登录 [PyPI官网](https://pypi.org/)
   - 进入你的项目管理页面
   - 点击 "Publishing" 标签
   - 点击 "Add a new publisher"
   - 选择 "GitHub Actions"

2. **填写GitHub Actions信息**:
   - **Owner**: 你的GitHub用户名或组织名
   - **Repository name**: 仓库名称
   - **Workflow name**: `build-release.yml`
   - **Environment name**: 留空（可选）

3. **保存配置**:
   - 点击 "Add publisher"
   - 配置完成后，GitHub Actions即可自动发布到PyPI

**优势**:
- 🔒 更安全：无需管理API Token
- 🚀 更便捷：自动认证，无需手动配置密钥
- 🔄 更可靠：由PyPI和GitHub官方维护

### 权限要求

- `contents: write` - 用于创建GitHub Release
- `id-token: write` - 用于PyPI可信发布

## 📋 工作流状态

| 工作流 | 状态 | 描述 |
|--------|------|------|
| Build and Release | ✅ 启用 | 手动执行，包含完整发布流程 |

## 🔍 故障排除

### 常见问题

- **PyPI发布失败**:
  - 检查PyPI Trusted Publisher是否正确配置
  - 确认版本号是否重复（PyPI不允许重复版本）
  - 验证仓库名称、工作流名称是否匹配
- **配置同步失败**: 检查ql分支是否存在，验证仓库权限
- **构建失败**: 检查pyproject.toml配置，确保依赖正确
- **可信发布认证失败**: 确保PyPI中的GitHub Actions配置与实际仓库信息一致

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
