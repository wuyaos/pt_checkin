#!/usr/bin/env python3
"""
本地构建测试脚本
用于验证GitHub Actions构建流程
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔄 {description}")
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 成功: {description}")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {description}")
        print(f"错误: {e.stderr.strip()}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始本地构建测试")
    
    # 检查当前目录
    if not Path("pyproject.toml").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 测试步骤
    tests = [
        # 1. 安装构建依赖
        ([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "升级pip"),
        ([sys.executable, "-m", "pip", "install", "build", "twine", "wheel"], "安装构建工具"),
        
        # 2. 清理旧的构建文件
        (["python", "-c", "import shutil; shutil.rmtree('dist', ignore_errors=True)"], "清理dist目录"),
        
        # 3. 构建包
        ([sys.executable, "-m", "build"], "构建wheel和源码包"),
        
        # 4. 检查构建结果
        ([sys.executable, "-m", "twine", "check", "dist/*"], "检查包完整性"),
        
        # 5. 测试导入
        ([sys.executable, "-c", "import pt_checkin; print('导入成功')"], "测试包导入"),
        
        # 6. 测试CLI
        ([sys.executable, "-m", "pt_checkin.cli", "--help"], "测试CLI帮助"),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for cmd, description in tests:
        if run_command(cmd, description):
            success_count += 1
        else:
            print(f"\n⚠️ 测试失败，但继续执行后续测试...")
    
    # 显示构建结果
    print(f"\n📊 测试结果: {success_count}/{total_count} 通过")
    
    if Path("dist").exists():
        print("\n📦 构建产物:")
        for file in Path("dist").iterdir():
            print(f"  - {file.name} ({file.stat().st_size} bytes)")
    
    # 总结
    if success_count == total_count:
        print("\n🎉 所有测试通过！GitHub Actions构建应该能正常工作")
        return 0
    else:
        print(f"\n⚠️ {total_count - success_count} 个测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
