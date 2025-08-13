#!/usr/bin/env python3
"""
PT站点自动签到工具启动脚本
解决相对导入问题
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入主程序
from main import cli

if __name__ == '__main__':
    cli()
