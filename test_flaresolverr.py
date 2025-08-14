#!/usr/bin/env python3
"""
测试FlareSolverr集成的脚本
"""

import sys
import os
sys.path.insert(0, 'src')

from pt_checkin.utils.flaresolverr import FlareSolverrClient, get_flaresolverr_client
import yaml

def test_flaresolverr_connection():
    """测试FlareSolverr连接"""
    print("=== 测试FlareSolverr连接 ===")
    
    # 从配置文件读取FlareSolverr配置
    with open('test/config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    client = get_flaresolverr_client(config)
    if not client:
        print("❌ 无法创建FlareSolverr客户端")
        return False
    
    print(f"✅ FlareSolverr客户端创建成功: {client.server_url}")
    
    # 创建会话
    if client.create_session():
        print(f"✅ 会话创建成功: {client.session_id}")
        
        # 销毁会话
        if client.destroy_session():
            print("✅ 会话销毁成功")
            return True
        else:
            print("❌ 会话销毁失败")
            return False
    else:
        print("❌ 会话创建失败")
        return False

def test_flaresolverr_request():
    """测试FlareSolverr请求"""
    print("\n=== 测试FlareSolverr请求 ===")
    
    # 从配置文件读取配置
    with open('test/config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    client = get_flaresolverr_client(config)
    if not client:
        print("❌ 无法创建FlareSolverr客户端")
        return False
    
    # 创建会话
    if not client.create_session():
        print("❌ 会话创建失败")
        return False
    
    try:
        # 测试访问open.cd首页
        print("测试访问 https://open.cd/")
        solution = client.request_get('https://open.cd/')
        
        if solution:
            print(f"✅ 请求成功")
            print(f"状态码: {solution.get('status', 'N/A')}")
            print(f"URL: {solution.get('url', 'N/A')}")
            print(f"响应长度: {len(solution.get('response', ''))}")
            
            # 检查响应内容
            response_text = solution.get('response', '')
            if 'OpenCD' in response_text:
                print("✅ 响应内容包含OpenCD，访问成功")
            else:
                print("⚠️ 响应内容不包含预期内容")
            
            # 测试访问签到页面
            print("\n测试访问签到页面...")
            cookie_str = config['sites']['open']['cookie']
            from pt_checkin.utils.flaresolverr import cookie_str_to_dict
            cookies = cookie_str_to_dict(cookie_str)
            
            solution2 = client.request_get(
                'https://open.cd/plugin_sign-in.php',
                cookies=cookies
            )
            
            if solution2:
                print(f"✅ 签到页面请求成功")
                response_text2 = solution2.get('response', '')
                print(f"签到页面响应长度: {len(response_text2)}")
                
                # 检查是否包含签到相关内容
                signin_indicators = ['imagehash', 'img src', '签到', '簽到']
                found_indicators = [ind for ind in signin_indicators if ind in response_text2]
                if found_indicators:
                    print(f"✅ 找到签到页面指示器: {found_indicators}")
                else:
                    print("❌ 未找到签到页面指示器")
                    print(f"响应内容前500字符: {response_text2[:500]}")
            else:
                print("❌ 签到页面请求失败")
            
            return True
        else:
            print("❌ 请求失败")
            return False
            
    finally:
        # 清理会话
        client.destroy_session()

def test_open_site_with_flaresolverr():
    """测试open站点使用FlareSolverr签到"""
    print("\n=== 测试open站点FlareSolverr签到 ===")
    
    try:
        from pt_checkin.sites.open import MainClass
        from pt_checkin.core.entry import SignInEntry
        import yaml
        
        # 加载配置
        with open('test/config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 创建签到条目
        entry = SignInEntry('open', 'https://open.cd/')
        entry['site_name'] = 'open'
        entry['site_config'] = config['sites']['open']
        entry['config'] = config
        entry['headers'] = {
            'user-agent': config.get('user_agent', 'Mozilla/5.0'),
            'referer': 'https://open.cd/',
            'accept-encoding': 'gzip, deflate, br',
        }
        
        # 创建站点实例
        site = MainClass()
        
        # 测试访问签到页面
        print("使用FlareSolverr访问签到页面...")
        response = site.request(entry, 'get', 'https://open.cd/plugin_sign-in.php')
        
        if response and not entry.failed:
            print("✅ FlareSolverr请求成功")
            print(f"响应状态码: {getattr(response, 'status_code', 'N/A')}")
            print(f"响应内容长度: {len(getattr(response, 'text', ''))}")
            
            # 检查内容
            content = getattr(response, 'text', '')
            if content:
                signin_indicators = ['imagehash', 'img src', '签到', '簽到']
                found_indicators = [ind for ind in signin_indicators if ind in content]
                if found_indicators:
                    print(f"✅ 找到签到页面指示器: {found_indicators}")
                else:
                    print("❌ 未找到签到页面指示器")
                    print(f"内容前500字符: {content[:500]}")
            return True
        else:
            print(f"❌ FlareSolverr请求失败: {entry.reason if entry.failed else '未知错误'}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 FlareSolverr集成测试开始\n")
    
    success_count = 0
    total_tests = 3
    
    # 测试项目
    tests = [
        ("FlareSolverr连接测试", test_flaresolverr_connection),
        ("FlareSolverr请求测试", test_flaresolverr_request),
        ("Open站点FlareSolverr集成测试", test_open_site_with_flaresolverr),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print('='*60)
        
        try:
            if test_func():
                success_count += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    # 总结
    print(f"\n{'='*60}")
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")
    print('='*60)
    
    if success_count == total_tests:
        print("🎉 所有测试通过！FlareSolverr集成成功")
        return 0
    else:
        print(f"⚠️ {total_tests - success_count} 个测试失败")
        print("💡 请检查FlareSolverr服务器状态和配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
