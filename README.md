# PT站点自动签到工具

用于自动签到PT站点，从项目[madwind/flexget_qbittorrent_mod](https://github.com/madwind/flexget_qbittorrent_mod)迁移而来，移除了FlexGet框架依赖和qBittorrent相关功能，专注于自动签到功能。


## 功能特性

- ✅ 支持100+个PT站点自动签到
- ✅ Cookie自动备份和管理
- ✅ 详细的日志记录和错误处理
- ✅ 支持验证码识别（百度OCR）
- ✅ 命令行界面，易于使用
- ✅ 标准Python包结构，支持pip安装
- ✅ 命令行工具

## 安装说明

### 环境要求

- Python 3.8+

### 方式一：本地安装

```bash
# 克隆项目
git clone https://github.com/your-username/pt-checkin.git
cd pt-checkin

# 安装
pip install .
```

### 方式二：PyPI安装（未来支持）

```bash
# 从PyPI安装（计划中）
pip install pt-checkin

# 验证安装
pt-checkin --help
```

### 配置文件

复制配置示例文件并编辑：

```bash
cp config_example.yml config.yml
```

编辑 `config.yml`，配置你的站点信息。配置示例文件包含了详细的说明和常见站点模板。

## 配置说明

### 基础配置

```yaml
# 基础设置
max_workers: 1                    # 最大并发线程数
user_agent: 'Mozilla/5.0...'      # 浏览器标识
get_messages: true                # 是否获取站内消息
get_details: true                 # 是否获取用户详情
cookie_backup: true               # 是否备份
```

### 站点配置

支持两种配置方式：

#### 简单配置（仅Cookie）
```yaml
sites:
  chdbits: 'your_cookie_string_here'
  hdchina: 'your_cookie_string_here'
```

#### 详细配置
```yaml
sites:
  dmhy:
    cookie: 'your_cookie_string_here'
    username: 'your_username'
    comment: 'daily_sign_in_comment'
  
  skyey2:
    login:
      username: 'your_username'
      password: 'your_password'
```

### 百度OCR配置（可选）

用于验证码识别：

```yaml
baidu_ocr_app_id: 'your_app_id'
baidu_ocr_api_key: 'your_api_key'
baidu_ocr_secret_key: 'your_secret_key'
```

## 使用方法

### 命令行使用（推荐，开发模式安装后可用）

#### 核心命令

```bash
# 执行签到任务（主要命令）
pt-checkin run

# 仅签到指定站点
pt-checkin run -s sjtu

# 强制重新签到
pt-checkin run --force

# 模拟运行（不实际执行）
pt-checkin run --dry-run
```

#### 测试命令

```bash
# 测试配置文件
pt-checkin test

# 测试单个站点
pt-checkin test-site sjtu

# 启用调试模式测试
pt-checkin test-site sjtu --debug
```

#### 状态管理

```bash
# 查看今日签到状态
pt-checkin status

# 显示失败次数统计
pt-checkin status --show-failed

# 清除今日所有签到状态
pt-checkin status --clear

# 清除指定站点状态
pt-checkin status --clear-site sjtu
```

#### 调试功能

```bash
# 显示所有站点概览
pt-checkin debug

# 调试指定站点
pt-checkin debug -s sjtu

# 显示完整配置信息
pt-checkin debug --show-config
```

#### 全局选项

```bash
# 使用自定义配置文件
pt-checkin -c my_config.yml run

# 详细日志输出
pt-checkin -v run
```

#### 通知消息获取

```bash
# 获取签到结果通知消息（简单模式）
pt-checkin get-notification

# 获取详细通知消息（包含详细信息）
pt-checkin get-notification --detailed

# 获取JSON格式通知
pt-checkin get-notification --format json

# 仅获取标题
pt-checkin get-notification --title-only
```

## 青龙面板使用(定时执行)

### 青龙面板安装配置

#### 1. **订阅导入**：使用青龙面板的订阅功能导入脚本
```bash
ql repo https://github.com/wuyaos/pt_checkin.git "ck_" "" "config_example.yml" "ql" "py"
```

#### 2. **配置文件设置**：
- 将 `config_example.yml` 复制为 `config.yml`
- 根据实际情况修改 `config.yml` 中的站点配置信息

#### 3. **依赖安装**：
- 在青龙面板 → 依赖管理 → Python3 中添加依赖：`pt-checkin`
- 确保环境中已安装pt-checkin包


## 项目结构

```text
pt-checkin/
├── src/pt_checkin/              # 主包目录
│   ├── __init__.py              # 包初始化
│   ├── cli.py                   # 命令行界面
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── config_manager.py    # 配置管理
│   │   ├── scheduler.py         # 任务调度
│   │   ├── executor.py          # 执行器
│   │   ├── entry.py             # 签到条目
│   │   └── signin_status.py     # 状态管理
│   ├── base/                    # 基础功能
│   │   ├── __init__.py
│   │   ├── sign_in.py           # 签到基类
│   │   ├── request.py           # 网络请求
│   │   ├── work.py              # 工作流
│   │   ├── message.py           # 消息基类
│   │   └── detail.py            # 详情基类
│   ├── sites/                   # 站点实现（100+个站点）
│   │   ├── __init__.py
│   │   ├── sjtu.py              # 上海交大PT站
│   │   ├── dmhy.py              # 动漫花园
│   │   ├── byr.py               # 北邮人PT
│   │   └── ...                  # 更多站点
│   ├── schema/                  # 站点架构
│   │   ├── __init__.py
│   │   ├── nexusphp.py          # NexusPHP架构
│   │   ├── gazelle.py           # Gazelle架构
│   │   ├── private_torrent.py   # 私有种子基类
│   │   └── ...                  # 更多架构
│   └── utils/                   # 工具类
│       ├── __init__.py
│       ├── net_utils.py         # 网络工具
│       ├── baidu_ocr.py         # 百度OCR
│       └── ...                  # 更多工具
├── qinglong/                    # 青龙面板专用目录
│   ├── ck_ptsites.py            # 青龙面板签到脚本
│   ├── notify.py                # 简化通知模块
│   ├── config.yml               # 青龙面板配置
│   └── README.md                # 青龙面板使用说明
├── config_example.yml           # 配置示例
├── pyproject.toml               # 项目配置
├── LICENSE                      # 许可证
└── README.md                    # 说明文档
```

## 更新日志

### v1.1.0 (青龙面板优化版)
- 🎉 加入青龙面板支持
- ✨ 添加 `get-notification` 命令支持简单/详细模式
- ✨ 添加消息详细程度控制功能
- 📚 完善青龙面板使用文档和示例

### v1.0.0
- 🎉 重构为标准Python包结构
- ✨ 添加pip安装支持
- ✨ 添加全局命令行工具 `pt-checkin`
- ✨ 添加更多命令行选项和状态管理
- 📚 更新文档和使用说明

## 许可证

本项目继承原FlexGet插件的许可证。

## 致谢

- 感谢madwind/flexget_qbittorrent_mod项目的作者