# FlareSolverr 配置指南

## 概述

FlareSolverr 是一个代理服务器，用于绕过 Cloudflare 和其他反机器人保护。本项目支持通过 FlareSolverr 访问受保护的 PT 站点。

## 配置方式

### 推荐配置（全局配置）

```yaml
# FlareSolverr 全局配置
flaresolverr:
  server_url: 'http://localhost:8191'    # FlareSolverr 服务器地址
  timeout: 60                            # 请求超时时间（秒）
  enable_all: false                      # 是否对所有站点启用（不推荐）
  enabled_sites:                        # 指定启用 FlareSolverr 的站点
    - open                               # open.cd 站点
    - other_site                         # 其他需要的站点

# 站点配置
sites:
  open:
    cookie: 'your_cookie_here'
    # 不需要 use_flaresolverr 配置，由全局 enabled_sites 控制
  
  other_site:
    cookie: 'your_cookie_here'
```

### 配置说明

| 配置项 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `server_url` | FlareSolverr 服务器地址 | - | ✅ |
| `timeout` | 请求超时时间（秒） | 60 | ❌ |
| `enable_all` | 对所有站点启用 FlareSolverr | false | ❌ |
| `enabled_sites` | 启用 FlareSolverr 的站点列表 | [] | ❌ |

### 启用逻辑

FlareSolverr 的启用遵循以下优先级：

1. **全局启用**：如果 `enable_all: true`，所有站点都使用 FlareSolverr
2. **站点列表**：如果站点名在 `enabled_sites` 列表中，该站点使用 FlareSolverr
3. **默认行为**：其他情况下不使用 FlareSolverr

### 部署 FlareSolverr

#### Docker 部署（推荐）

```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```

#### Docker Compose

```yaml
version: '3'
services:
  flaresolverr:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    environment:
      - LOG_LEVEL=info
    ports:
      - "8191:8191"
    restart: unless-stopped
```

### 测试配置

启动 FlareSolverr 后，可以通过以下方式测试：

```bash
# 测试 FlareSolverr 服务
curl -X POST http://localhost:8191/v1 \
  -H "Content-Type: application/json" \
  -d '{"cmd": "request.get", "url": "https://open.cd/"}'

# 测试签到功能
pt-checkin -c config.yml run --site open --force
```

### 故障排除

#### 常见问题

1. **连接失败**
   - 检查 FlareSolverr 服务是否运行
   - 确认端口 8191 是否可访问
   - 检查防火墙设置

2. **请求超时**
   - 增加 `timeout` 配置值
   - 检查网络连接
   - 确认目标站点是否可访问

3. **验证码识别失败**
   - 验证码图片下载使用普通 requests，不经过 FlareSolverr
   - 检查百度 OCR 配置是否正确

#### 日志分析

启用调试模式查看详细日志：

```bash
pt-checkin -c config.yml debug --site open
```

关键日志信息：
- `Using FlareSolverr for {url}` - 确认使用 FlareSolverr
- `FlareSolverr client initialized` - 客户端初始化成功
- `Config has flaresolverr: True` - 配置加载正确

### 性能优化

1. **合理设置超时时间**：根据网络环境调整 `timeout` 值
2. **选择性启用**：只对需要的站点启用 FlareSolverr
3. **监控资源使用**：FlareSolverr 会消耗较多内存和 CPU

### 安全注意事项

1. **网络隔离**：建议在内网环境部署 FlareSolverr
2. **访问控制**：限制对 FlareSolverr 服务的访问
3. **定期更新**：保持 FlareSolverr 版本更新

## 版本兼容性

- **FlareSolverr v2.x**：完全支持（推荐）
- **FlareSolverr v1.x**：部分支持（不推荐）

本项目已针对 FlareSolverr v2 进行优化，移除了已废弃的 `headers` 参数。
