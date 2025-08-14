# GitHub Actions 工作流说明

本项目使用GitHub Actions实现自动化构建、测试、发布和配置同步。

## 🔄 工作流概览

### 1. 测试工作流 (`test.yml`)
- **触发条件**: 推送到master/ql分支，PR，手动执行
- **功能**: 
  - 多Python版本测试 (3.8-3.12)
  - 导入测试
  - CLI命令测试
  - 代码覆盖率上传

### 2. 构建发布工作流 (`build-and-publish.yml`)
- **触发条件**: 手动执行，项目更新时执行(已注释)
- **功能**:
  - 编译打包为wheel文件
  - 上传到PyPI (可选)
  - 同步配置文件到ql分支
- **手动参数**:
  - `publish_to_pypi`: 是否发布到PyPI
  - `sync_config`: 是否同步配置文件

### 3. 配置同步工作流 (`sync-config.yml`)
- **触发条件**: config_example.yml变更，手动执行
- **功能**:
  - 自动同步master分支的配置文件到ql分支
  - 如果ql分支不存在则自动创建
- **手动参数**:
  - `force_sync`: 强制同步(即使文件无变化)

### 4. 发布工作流 (`release.yml`)
- **触发条件**: 推送版本标签 (v*)，手动执行
- **功能**:
  - 自动更新版本号
  - 构建并发布到PyPI
  - 创建GitHub Release
  - 生成变更日志
  - 同步配置到ql分支

## 🚀 使用指南

### 日常开发
1. 推送代码到master分支会自动触发测试
2. 修改`config_example.yml`会自动同步到ql分支

### 手动构建测试
1. 进入Actions页面
2. 选择"Build and Publish"工作流
3. 点击"Run workflow"
4. 设置参数并执行

### 发布新版本
#### 方法1: 推送标签 (推荐)
```bash
git tag v1.2.0
git push origin v1.2.0
```

#### 方法2: 手动执行
1. 进入Actions页面
2. 选择"Release"工作流
3. 输入版本标签 (如: v1.2.0)
4. 执行工作流

### 同步配置文件
#### 自动同步
- 修改`config_example.yml`并推送到master分支

#### 手动同步
1. 进入Actions页面
2. 选择"Sync Config to QL Branch"
3. 可选择强制同步
4. 执行工作流

## 🔧 配置要求

### PyPI发布配置
1. 在GitHub仓库设置中配置PyPI的可信发布
2. 或者在仓库Secrets中添加`PYPI_API_TOKEN`

### 分支保护
- 建议为master分支设置保护规则
- 要求通过测试才能合并

## 📋 工作流状态

| 工作流 | 状态 | 描述 |
|--------|------|------|
| Test | ✅ 启用 | 自动测试 |
| Build and Publish | ✅ 启用 | 手动执行 |
| Sync Config | ✅ 启用 | 自动+手动 |
| Release | ✅ 启用 | 标签触发 |

## 🔍 故障排除

### 常见问题
1. **PyPI发布失败**: 检查版本号是否重复
2. **配置同步失败**: 检查ql分支权限
3. **测试失败**: 检查依赖安装和代码质量

### 调试方法
1. 查看Actions日志
2. 检查工作流文件语法
3. 验证仓库权限设置

## 📝 维护说明

### 定期维护
- 更新GitHub Actions版本
- 检查依赖安全性
- 优化工作流性能

### 版本管理
- 遵循语义化版本规范
- 及时更新CHANGELOG
- 保持分支同步
