# PT站点自动签到工具

一个独立的Python应用程序，用于自动签到PT站点。本项目从FlexGet qBittorrent插件[madwind/flexget_qbittorrent_mod](https://github.com/madwind/flexget_qbittorrent_mod)迁移而来，移除了FlexGet框架依赖和qBittorrent相关功能，专注于自动签到功能。(由大模型驱动优化)

这是一个用于 PT (Private Tracker) 站点自动签到的 Python 脚本，可以帮助你自动完成每日签到任务。

## 功能特性

- ✅ 支持100+个PT站点自动签到
- ✅ 多线程并发签到，提高效率
- ✅ 定时任务调度，每日自动执行
- ✅ Cookie自动备份和管理
- ✅ 详细的日志记录和错误处理
- ✅ 支持验证码识别（百度OCR）
- ✅ 简单的通知系统
- ✅ 命令行界面，易于使用

## 安装说明

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
cd pt_auto_signin
pip install -r requirements.txt
```

### 3. 配置文件

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
cookie_backup: true               # 是否备份Cookie
schedule_time: '08:30'            # 每日签到时间
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

### 1. 测试配置

```bash
python main.py test
```

### 2. 调试模式

```bash
# 显示所有站点概览
python main.py debug

# 调试指定站点
python main.py debug -s dmhy

# 显示完整配置信息
python main.py debug --show-config

# 显示cookie信息（敏感信息会被遮蔽）
python main.py debug -s dmhy --show-cookies
```

### 3. 测试单个站点

```bash
# 普通测试
python main.py test-site dmhy

# 启用调试信息
python main.py test-site dmhy --debug
```

### 4. 立即执行签到

```bash
# 签到所有站点
python main.py once

# 仅签到指定站点
python main.py once -s dmhy

# 模拟运行（不实际执行）
python main.py once --dry-run
```

### 5. 启动定时服务

```bash
# 启动定时服务
python main.py run

# 立即执行一次后启动定时服务
python main.py run --now
```

### 6. 使用自定义配置文件

```bash
python main.py -c my_config.yml run
```

### 7. 详细日志输出

```bash
python main.py -v run
```

## 支持的站点

本工具支持100+个PT站点，包括但不限于：

- CHDBits, HDChina, OurBits, KeepFrds
- DMHY, SkyeY2, SpringSunday, PterClub
- HDArea, HDAtmos, HDCity, HDFans
- 更多站点请参考 `sites/` 目录

## 日志文件

- 日志文件保存在 `logs/` 目录
- 按日期自动分割：`pt_signin_YYYY-MM-DD.log`
- 自动压缩和清理（保留30天）

## 通知系统

默认使用简单的控制台输出通知。你可以修改 `notify.py` 文件来集成其他通知方式：

```python
def send(title: str, content: str):
    # 在这里添加你的通知逻辑
    # 例如：邮件、微信、Telegram等
    print(f"[通知] {title}")
    print(f"内容: {content}")
```

## 故障排除

### 1. 站点签到失败

- 检查Cookie是否过期
- 确认站点是否正常访问
- 查看详细日志了解具体错误

### 2. 验证码问题

- 配置百度OCR服务
- 检查OCR配置是否正确
- 某些站点可能需要手动处理验证码

### 3. 网络问题

- 检查网络连接
- 考虑使用代理
- 调整请求超时时间

## 开发说明

### 项目结构

```
pt_auto_signin/
├── main.py              # 主程序入口
├── config.yml           # 配置文件
├── notify.py           # 通知模块
├── core/               # 核心模块
├── base/               # 基础功能
├── sites/              # 站点实现
├── schema/             # 站点架构
└── utils/              # 工具类
```

### 添加新站点

1. 在 `sites/` 目录创建新的站点文件
2. 继承相应的基类（SignIn, Message, Detail）
3. 实现必要的方法

## 许可证

本项目继承原FlexGet插件的许可证。

## 致谢

- 感谢原FlexGet qBittorrent插件的开发者
- 感谢所有贡献者和用户的支持
