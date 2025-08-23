# PT签到工具项目概览

## 项目架构

PT签到工具是一个基于Python的自动化签到系统，专门为Private Tracker站点设计。项目采用模块化架构，移除了FlexGet依赖，提供独立的签到解决方案。

### 核心模块结构

```text
src/pt_checkin/
├── cli.py                    # 命令行界面入口
├── core/                     # 核心功能模块
│   ├── config_manager.py     # 配置管理器
│   ├── scheduler.py          # 任务调度器
│   ├── executor.py           # 签到执行器
│   ├── entry.py             # 签到条目类
│   └── signin_status.py     # 签到状态管理
├── base/                     # 基础抽象类
│   ├── request.py           # HTTP请求基类
│   ├── sign_in.py           # 签到基类和状态检查
│   ├── work.py              # 工作流定义
│   ├── detail.py            # 用户详情获取
│   └── message.py           # 站内消息获取
├── schema/                   # 站点架构模板
│   ├── private_torrent.py   # PT站点基类
│   ├── nexusphp.py          # NexusPHP架构
│   ├── gazelle.py           # Gazelle架构
│   └── unit3d.py            # Unit3D架构
├── sites/                    # 具体站点实现
│   ├── siqi.py              # 思齐站点
│   ├── hdsky.py             # HDSky站点
│   └── ...                  # 其他100+站点
└── utils/                    # 工具模块
    ├── net_utils.py         # 网络工具
    ├── flaresolverr.py      # Cloudflare绕过
    └── baidu_ocr.py         # 验证码识别
```

## 执行流程

### 1. 命令行入口 (cli.py)

- 解析命令行参数
- 初始化配置管理器
- 设置日志系统
- 调用任务调度器

### 2. 任务调度 (scheduler.py)

- 加载站点配置
- 创建签到条目
- 过滤已签到站点
- 多线程执行签到任务
- 记录签到状态

### 3. 签到执行 (executor.py)

- 动态加载站点类
- 构建签到工作流
- 执行签到、消息、详情获取
- 处理异常和状态记录

### 4. 站点实现 (sites/*.py)

- 继承基础架构类
- 定义签到工作流
- 处理验证码、登录等特殊情况
- 返回签到结果

## 核心概念

### SignInEntry (签到条目)

```python
class SignInEntry:
    def __init__(self, title: str, url: str = ''):
        self.data = {'title': title, 'url': url}
        self.failed = False
        self.reason = ''
```

- 封装单次签到任务的所有信息
- 包含站点配置、Cookie、请求头等
- 记录签到状态和失败原因

### Work (工作流)

```python
class Work:
    def __init__(self, url: str, method: Callable,
                 succeed_regex: list = None,
                 fail_regex: str = None):
```

- 定义单个HTTP请求的完整配置
- 包含URL、请求方法、成功/失败正则表达式
- 支持链式工作流执行

### 签到状态检查

```python
def check_sign_in_state(entry, work, response, content) -> SignState:
    # 1. 检查网络状态
    # 2. 匹配成功正则表达式
    # 3. 检查失败模式
    # 4. 返回签到状态
```


## 站点架构体系

### 1. PrivateTorrent (基类)

- 所有PT站点的基础类
- 提供HTTP请求、Cookie管理
- 定义签到、消息、详情获取接口

### 2. NexusPHP架构

```python
class Attendance(AttendanceHR, ABC):
    # GET /attendance.php 签到
    # 支持验证码处理
    # 标准成功消息匹配
```

### 3. Gazelle架构

```python
class Gazelle(PrivateTorrent, ABC):
    # 模拟登录方式
    # JSON API响应
    # 特殊Cookie处理
```

### 4. Unit3D架构

```python
class Unit3D(PrivateTorrent, ABC):
    # 现代化界面
    # CSRF Token处理
    # API端点签到
```

## 请求处理机制

### 1. 普通HTTP请求

- 使用requests.Session
- 自动Cookie管理
- 重试机制
- 编码检测

### 2. FlareSolverr集成

- 绕过Cloudflare保护
- 浏览器环境模拟
- JavaScript渲染支持
- 自动验证码处理

这个架构设计确保了系统的可扩展性、可维护性和稳定性，为PT站点自动签到提供了完整的解决方案。

## 配置系统

### 基础配置

```yaml
max_workers: 1                    # 并发线程数
user_agent: 'Mozilla/5.0...'      # 浏览器标识
get_messages: true                # 获取站内消息
get_details: true                 # 获取用户详情
cookie_backup: true               # Cookie备份
```

### 站点配置

```yaml
sites:
  # 简单配置
  hdchina: 'cookie_string_here'

  # 详细配置
  siqi:
    cookie: 'cookie_string_here'
    username: 'username'
    comment: 'daily_comment'
```

### 高级功能配置

```yaml
# 百度OCR验证码识别
aipocr:
  app_id: 'your_app_id'
  api_key: 'your_api_key'
  secret_key: 'your_secret_key'

# FlareSolverr配置
flaresolverr:
  server_url: 'http://localhost:8191'
  timeout: 120
  enabled_sites: ['open', 'hdtime']


```

## 状态管理

### 签到状态记录

- 每日签到状态跟踪
- 失败次数统计
- 重试间隔控制
- 历史记录清理

### 状态文件格式

```json
{
  "2025-08-15": {
    "siqi": {
      "status": "success",
      "result": "签到成功",
      "time": "14:05:45",
      "messages": "",
      "details": {...}
    }
  },
  "failed_counts": {
    "siqi": 0
  }
}
```

## 错误处理

### 网络错误

- 连接超时重试
- HTTP状态码检查
- Cloudflare检测
- 重定向处理

### 签到错误

- 正则匹配失败
- 验证码识别失败
- Cookie过期处理
- 站点维护检测

### 异常恢复

- 自动重试机制
- 失败次数限制
- 状态回滚
- 日志记录

## 扩展机制

### 添加新站点

1. 确定站点架构类型
2. 创建站点实现文件
3. 定义签到工作流
4. 配置成功/失败模式
5. 测试和调试

### 自定义功能

- 继承基础类
- 重写关键方法
- 添加特殊处理逻辑
- 集成到执行流程

这个架构设计确保了系统的可扩展性、可维护性和稳定性，为PT站点自动签到提供了完整的解决方案。
