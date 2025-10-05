#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
虚拟环境访问权限测试脚本
用于检查虚拟环境是否能够正确访问系统安装的Python模块
特别是libcamera和picamera2模块
"""

import sys
import os
import argparse

# 解析命令行参数
parser = argparse.ArgumentParser(description='虚拟环境访问权限测试脚本')
parser.add_argument('-v', '--verbose', action='store_true', help='启用详细输出模式')
args = parser.parse_args()
verbose = args.verbose

def print_verbose(message):
    """只在详细模式下打印消息"""
    if verbose:
        print(message)

if verbose:
    print("===== 虚拟环境访问权限测试 ======")
    
    # 显示当前Python解释器路径
    print(f"Python解释器路径: {sys.executable}")
    
    # 显示Python版本
    print(f"Python版本: {sys.version}")
    
    # 显示Python模块搜索路径
    sys_path_str = "\n".join(sys.path)
    print(f"\nPython模块搜索路径:\n{sys_path_str}")
    
    # 检查是否在虚拟环境中
    is_venv = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    print(f"\n是否在虚拟环境中: {is_venv}")
    if is_venv:
        print(f"虚拟环境基础路径: {sys.base_prefix}")
        print(f"虚拟环境前缀: {sys.prefix}")

# 尝试导入libcamera模块
success = True
print_verbose("\n===== 尝试导入libcamera模块 ======")
try:
    import libcamera
    print("✓ libcamera模块导入成功")
    print_verbose(f"libcamera模块路径: {libcamera.__file__}")
except ImportError as e:
    print(f"✗ libcamera模块导入失败: {str(e)}")
    if verbose:
        print("\n可能的原因:")
        print("1. libcamera模块未安装")
        print("2. 虚拟环境无法访问系统Python模块")
        print("3. Python路径配置问题")
        
        # 检查系统Python模块路径
        system_python_lib = f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/dist-packages"
        if os.path.exists(system_python_lib):
            print(f"\n系统Python模块路径: {system_python_lib}")
            if system_python_lib not in sys.path:
                print("该路径不在Python模块搜索路径中，这可能是问题所在")
    success = False

# 尝试导入picamera2模块
print_verbose("\n===== 尝试导入picamera2模块 ======")
try:
    import picamera2
    print("✓ picamera2模块导入成功")
    print_verbose(f"picamera2模块路径: {picamera2.__file__}")
    
    # 检查picamera2是否能正常使用libcamera
    try:
        if verbose:
            test_camera = picamera2.Picamera2()
            print("✓ Picamera2初始化成功")
            test_camera.close()
except Exception as e:
    print(f"✗ picamera2模块导入失败: {str(e)}")
    success = False

if verbose:
    print("\n===== 测试完成 ======")

# 退出状态码反映测试结果
sys.exit(0 if success else 1)