# PT站点适配开发指南

## 概述

本指南详细介绍如何为PT签到工具添加新的站点支持。每个站点都需要继承相应的基础架构类，并实现特定的签到逻辑。

## 站点架构选择

### 1. NexusPHP架构 (最常见)
适用于大多数PT站点，特征：
- 使用 `/attendance.php` 签到页面
- 标准的签到成功消息格式
- 可能包含验证码

**基类选择：**
- `Attendance` - 标准签到，无H&R显示
- `AttendanceHR` - 显示H&R信息的签到

### 2. Gazelle架构
适用于音乐类PT站点，特征：
- 基于JSON API
- 需要模拟登录
- 特殊的Cookie处理

### 3. Unit3D架构
现代化PT站点，特征：
- 使用CSRF Token
- RESTful API设计
- 现代前端框架

### 4. 自定义架构
对于特殊站点，直接继承 `PrivateTorrent`

## 创建新站点适配

### 步骤1：创建站点文件

在 `src/pt_checkin/sites/` 目录下创建站点文件，文件名使用站点域名：

```python
# src/pt_checkin/sites/example.py
from typing import Final
from ..schema.nexusphp import Attendance

class MainClass(Attendance):
    URL: Final = 'https://example.com/'
    USER_CLASSES: Final = {
        'downloaded': [1073741824000],  # 1TB
        'share_ratio': [2.0],           # 分享率要求
        'days': [30]                    # 天数要求
    }
```

### 步骤2：定义签到工作流

#### 简单GET签到（继承默认）
如果站点使用标准的NexusPHP签到，无需重写方法：

```python
class MainClass(Attendance):
    URL: Final = 'https://example.com/'
    # 使用默认的 sign_in_build_workflow
```

#### 自定义签到工作流
```python
def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
    return [
        Work(
            url='/attendance.php',
            method=self.sign_in_by_get,
            succeed_regex=[
                '这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?魔力值',
                '您今天已经签到过了',
                '签到成功'
            ],
            assert_state=(check_final_state, SignState.SUCCEED),
            is_base_content=True
        ),
    ]
```

### 步骤3：处理验证码签到

对于需要验证码的站点（如siqi）：

```python
def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
    return [
        Work(
            url='/attendance.php',
            method=self.sign_in_by_captcha,
            succeed_regex=[
                '这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?个魔力值',
                '您今天已经签到过了',
                '签到成功'
            ],
            assert_state=(check_final_state, SignState.SUCCEED),
        ),
    ]

def sign_in_by_captcha(self, entry: SignInEntry, config: dict,
                       work: Work, last_content: str) -> Response | None:
    # 1. 获取签到页面
    response = self.request(entry, 'get', work.url)
    if not response:
        entry.fail_with_prefix('无法获取签到页面')
        return None

    # 2. 检查是否已签到
    success_patterns = [
        r'这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?个魔力值',
        r'您今天已经签到过了'
    ]

    for pattern in success_patterns:
        if re.search(pattern, response.text):
            return response

    # 3. 处理验证码
    # 提取imagehash
    imagehash_match = re.search(r'name="imagehash" value="([^"]+)"', response.text)
    if not imagehash_match:
        entry.fail_with_prefix('页面没有验证码表单')
        return None

    # 4. 获取验证码图片并OCR识别
    # 5. 提交表单
    # ... 具体实现
```

## 正则表达式配置

### 成功匹配模式 (succeed_regex)
```python
succeed_regex = [
    # 标准NexusPHP格式
    '这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?魔力值',
    '您今天已经签到过了，请勿重复刷新',

    # 简化格式
    '签到成功',
    '签到已得\\d+',

    # 英文站点
    'Attendance successful',
    'You have already signed in today',

    # 特殊格式（使用元组指定捕获组）
    ('签到获得 (\\d+) 魔力值', 1),  # 捕获第1组
]
```

### 失败匹配模式 (fail_regex)
```python
fail_regex = '验证码错误|Captcha error|签到失败'
```

## 请求方法类型选择

### 新架构说明
从v2.0开始，系统采用了全新的Request架构：
- **BaseRequest**: 抽象基类，定义请求接口
- **StandardRequest**: 标准HTTP请求实现
- **FlareSolverrRequest**: FlareSolverr代理请求实现
- **BrowserAutomationRequest**: 浏览器自动化请求实现（预留）
- **RequestFactory**: 工厂类，根据配置自动创建合适的Request实例

### 配置驱动的请求方式选择

#### 1. 全局配置
在config.yml中设置全局默认请求方式：
```yaml
# 全局请求方法配置
request_method: 'auto'  # 可选值: default, flaresolverr, browser, auto
```

#### 2. 站点特定配置
为特定站点设置请求方式：
```yaml
sites:
  # 字符串格式（使用全局或AUTO模式）
  site1: 'cookie_string_here'

  # 字典格式（可指定请求方式）
  site2:
    cookie: 'cookie_string_here'
    request_method: 'default'  # 强制使用标准requests

  site3:
    cookie: 'cookie_string_here'
    request_method: 'flaresolverr'  # 强制使用FlareSolverr
```

#### 3. 站点代码中的使用
站点代码无需修改，仍然使用相同的接口：
```python
# 系统会根据配置自动选择合适的请求方式
response = self.request(entry, 'get', work.url)

# 对于验证码图片等特殊场景，可强制使用标准requests
response = self.request(entry, 'get', captcha_url, force_default=True)
```

### 请求方式说明
- **default**: 使用标准requests，速度最快，适合无保护的站点
- **browser**: 使用浏览器自动化，适合复杂交互（暂未实现）
- **auto**: 系统自动判断，根据站点配置和检测结果选择最佳方式

## 特殊情况处理

### 1. 需要登录的站点
```python
def sign_in_build_login_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
    return [
        Work(
            url='/login.php',
            method=self.sign_in_by_login,
            succeed_regex=['欢迎回来', 'Welcome back'],
            assert_state=(check_final_state, SignState.SUCCEED),
        )
    ]

def sign_in_build_login_data(self, login: dict, last_content: str) -> dict:
    return {
        'username': login['username'],
        'password': login['password'],
        'csrf_token': self.extract_csrf_token(last_content)
    }
```


### 3. 需要浏览器自动化的站点
```python
def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
    return [
        Work(
            url='/attendance.php',
            method=self._sign_in_with_browser,
            succeed_regex=['签到成功'],
            assert_state=(check_final_state, SignState.SUCCEED),
        ),
    ]

def _sign_in_with_browser(self, entry: SignInEntry, config: dict,
                         work: Work, last_content: str) -> Response | None:
    # 使用浏览器自动化处理复杂交互
    return self.request(entry, 'get', work.url,
                       method_type=RequestMethod.BROWSER)
```

## 最佳实践

### 1. 优先使用AUTO模式
除非有特殊需求，建议使用默认的AUTO模式，让系统自动选择最合适的请求方式。

### 2. 性能考虑
- 标准requests速度最快，适合简单站点
- FlareSolverr有额外开销，仅在必要时使用
- 浏览器自动化开销最大，用于最复杂的场景

### 3. 错误处理
不同请求方式的错误处理机制不同，确保在站点实现中正确处理各种异常情况。

### 4. 测试建议
在开发新站点适配时，建议测试不同的method_type以找到最佳方案。