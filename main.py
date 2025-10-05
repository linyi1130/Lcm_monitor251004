#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
座位监控系统启动入口
此文件提供了一个独立的程序入口点，方便在不同环境下启动系统
"""

import sys
import os
import time
import argparse

def main():
    """主入口函数"""
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='座位监控系统')
        parser.add_argument('-d', '--debug', action='store_true', help='启用调试模式，输出详细日志信息')
        args = parser.parse_args()
        
        # 确保当前工作目录包含seat_monitor模块
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        # 导入座位监控模块
        from seat_monitor import main as monitor_main
        
        # 打印启动信息
        print("\n===== 座位监控系统 =====")
        print(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"当前工作目录: {current_dir}")
        if args.debug:
            print("调试模式已启用")
        print("正在初始化系统...")
        
        # 调用seat_monitor模块的main函数，传递debug参数
        exit_code = monitor_main(args.debug)
        
        # 返回退出码
        return exit_code
        
    except ImportError as e:
        print(f"错误: 无法导入必要的模块 - {str(e)}")
        print("请确保seat_monitor.py文件存在于当前目录中")
        return 1
    except Exception as e:
        print(f"系统启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    # 调用主函数并设置返回码
    exit_code = main()
    # 退出程序，返回相应的退出码
    sys.exit(exit_code)