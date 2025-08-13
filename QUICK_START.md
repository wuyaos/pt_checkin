# PT自动签到工具 - 快速开始指南

## 🚀 5分钟快速上手

### 1. 复制配置文件
```bash
cp config_example.yml config.yml
```

### 2. 编辑配置文件
打开 `config.yml`，添加你的站点配置：

```yaml
sites:
  # 简单配置：站点名: cookie
  hdchina: 'your_cookie_here'
  
  # 详细配置：站点名: {配置项}
  dmhy:
    cookie: 'your_cookie_here'
    username: 'your_username'
```

### 3. 获取Cookie
1. 浏览器登录PT站点
2. 按F12打开开发者工具
3. 切换到Network标签
4. 刷新页面
5. 找到站点请求，复制Cookie值

### 4. 测试配置
```bash
# 测试配置文件
python run.py test

# 调试单个站点
python run.py debug -s hdchina
```

### 5. 开始签到
```bash
# 立即签到所有站点
python run.py once

# 签到指定站点
python run.py once -s hdchina

# 启动定时服务
python run.py run
```

## 📋 常用命令

| 命令 | 说明 |
|------|------|
| `python run.py test` | 测试配置文件 |
| `python run.py debug` | 查看所有站点状态 |
| `python run.py debug -s 站点名` | 调试指定站点 |
| `python run.py once` | 立即签到所有站点 |
| `python run.py once -s 站点名` | 签到指定站点 |
| `python run.py once --dry-run` | 模拟运行 |
| `python run.py once --force` | 强制重新签到所有站点 |
| `python run.py once --force-site 站点名` | 强制重新签到指定站点 |
| `python run.py status` | 查看今日签到状态 |
| `python run.py status --show-failed` | 显示失败次数统计 |
| `python run.py status --clear` | 清除今日所有签到状态 |
| `python run.py status --clear-site 站点名` | 清除指定站点签到状态 |
| `python run.py status --reset-failed 站点名` | 重置指定站点失败次数 |
| `python run.py run` | 启动定时服务 |
| `python run.py run --now` | 立即执行后启动定时服务 |

## 🔧 常见问题

### Q: 签到失败怎么办？
A: 
1. 检查Cookie是否过期：`python run.py debug -s 站点名 --show-cookies`
2. 查看详细错误：`python run.py test-site 站点名 --debug`
3. 确认站点是否正常访问

### Q: 如何添加新站点？
A: 在 `config.yml` 的 `sites` 部分添加：
```yaml
sites:
  新站点名: 'cookie_string'
```

### Q: 如何修改签到时间？
A: 修改 `config.yml` 中的 `schedule_time`：
```yaml
schedule_time: '09:00'  # 改为上午9点
```

### Q: 通知内容包含什么？
A:
- 📊 签到统计（总数、成功、失败、跳过）
- ✅ 成功站点及获得的奖励
- ❌ 失败站点及失败原因
- ⏭️ 跳过的已签到站点
- 🕐 执行时间和耗时

### Q: 如何避免重复签到？
A: 系统会自动记录每日签到状态：
- 已签到的站点会被自动跳过
- 使用 `--force` 强制重新签到所有站点
- 使用 `--force-site 站点名` 强制重新签到指定站点
- 使用 `python run.py status` 查看签到状态

### Q: 如何管理签到状态？
A:
- `python run.py status` - 查看今日签到状态
- `python run.py status --show-failed` - 显示失败次数统计
- `python run.py status --clear` - 清除所有签到状态
- `python run.py status --clear-site 站点名` - 清除指定站点状态
- `python run.py status --reset-failed 站点名` - 重置指定站点失败次数

### Q: 什么是失败次数限制？
A: 为了避免某些站点反复失败影响效率：
- 默认连续失败3次后会暂时跳过该站点
- 失败后2小时内不再尝试该站点
- 可在配置文件中调整 `max_failed_attempts` 和 `failed_retry_interval`
- 使用 `--reset-failed` 可以重置失败次数
- 第二天会自动重置失败次数

## 🎯 支持的站点

本工具支持100+个PT站点，包括：
- **中国大陆**：CHDBits, HDChina, OurBits, KeepFrds, PterClub, HDArea, HDAtmos, HDFans, HDSky, JoyHD, M-Team, TTG
- **教育网**：SJTU, TJUPT, BYR, NYPT
- **国外站点**：PrivateHD, Blutopia, Beyond-HD, Torrentleech, IPTorrents
- **专业站点**：Redacted, MyAnonamouse, GazelleGames

完整列表请查看 `sites/` 目录。

## 📞 获取帮助

- 查看详细文档：`README.md`
- 查看配置示例：`config_example.yml`
- 查看迁移说明：`MIGRATION_SUMMARY.md`
