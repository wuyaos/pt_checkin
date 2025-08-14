#!/usr/bin/env python3
"""
调试open.py站点签到问题的测试脚本
"""

import sys
import os
sys.path.insert(0, 'src')

from pt_checkin.sites.open import MainClass
from pt_checkin.core.entry import SignInEntry
from pt_checkin.utils import net_utils

def test_open_signin():
    """测试open站点签到"""
    
    # 从配置文件读取cookie
    import yaml
    with open('test/config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    cookie = config['sites']['open']
    print(f"使用cookie: {cookie[:50]}...")
    
    # 创建签到条目
    entry = SignInEntry('open', 'https://open.cd/')
    entry['site_name'] = 'open'
    entry['cookie'] = cookie
    entry['headers'] = {
        'user-agent': config.get('user_agent', 'Mozilla/5.0'),
        'referer': 'https://open.cd/',
        'accept-encoding': 'gzip, deflate, br',
    }
    
    # 创建站点实例
    site = MainClass()
    
    # 测试访问签到页面
    print("\n=== 测试访问签到页面 ===")
    response = site.request(entry, 'get', 'https://open.cd/plugin_sign-in.php')
    
    if response:
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")

        # 尝试多种解码方式
        content_netutils = net_utils.decode(response)
        content_text = response.text

        print(f"\n=== net_utils.decode结果 ===")
        print(f"内容长度: {len(content_netutils) if content_netutils else 0}")
        if content_netutils:
            print(f"前500字符: {content_netutils[:500]}")

        print(f"\n=== response.text结果 ===")
        print(f"内容长度: {len(content_text)}")
        print(f"前500字符: {content_text[:500]}")

        # 使用response.text作为主要内容
        content = content_text
        print("\n" + "="*50)
        
        # 检查是否包含登录相关内容
        login_indicators = ['未登錄!', '錯誤: 該頁面必須在登錄後才能訪問', '登錄', '用戶名', '密碼']
        found_indicators = [indicator for indicator in login_indicators if indicator in content]
        if found_indicators:
            print(f"❌ 检测到登录页面指示器: {found_indicators}")
        else:
            print("✅ 未检测到登录页面指示器")
        
        # 检查是否包含签到相关内容
        signin_indicators = ['imagehash', 'img src', '签到', '簽到', 'plugin_sign-in']
        found_signin = [indicator for indicator in signin_indicators if indicator in content]
        if found_signin:
            print(f"✅ 检测到签到页面指示器: {found_signin}")
        else:
            print("❌ 未检测到签到页面指示器")
            
        # 尝试查找imagehash和img src
        import re
        image_hash_re = re.search('(?<=imagehash=).*?(?=")', content)
        img_src_re = re.search('(?<=img src=").*?(?=")', content)
        
        if image_hash_re:
            print(f"✅ 找到imagehash: {image_hash_re.group()}")
        else:
            print("❌ 未找到imagehash")
            
        if img_src_re:
            print(f"✅ 找到img src: {img_src_re.group()}")
        else:
            print("❌ 未找到img src")
            
    else:
        print("❌ 请求失败")
        if entry.failed:
            print(f"失败原因: {entry.reason}")

if __name__ == '__main__':
    test_open_signin()
