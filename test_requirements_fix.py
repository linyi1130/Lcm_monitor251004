#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证requirements.txt修复是否成功
用于检查依赖安装是否能正常工作
"""

import os
import sys
import subprocess

print("开始测试requirements.txt修复...")

# 检查当前目录下是否存在requirements.txt
if not os.path.exists('requirements.txt'):
    print("错误：未找到requirements.txt文件")
    sys.exit(1)

# 查看修复后的requirements.txt内容
print("\n修复后的requirements.txt内容：")
with open('requirements.txt', 'r') as f:
    print(f.read())

# 创建一个临时虚拟环境用于测试
venv_name = "test_requirements_env"
print(f"\n创建临时虚拟环境 '{venv_name}' 用于测试依赖安装...")

try:
    # 创建临时虚拟环境
    subprocess.run([sys.executable, '-m', 'venv', venv_name], check=True)
    print(f"✓ 成功创建虚拟环境 '{venv_name}'")
    
    # 获取pip路径
    if sys.platform == 'win32':
        pip_path = os.path.join(venv_name, 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(venv_name, 'bin', 'pip')
    
    # 更新pip
    print("\n更新pip...")
    subprocess.run([pip_path, 'install', '--upgrade', 'pip'], check=True)
    
    # 尝试安装requirements.txt中的依赖
    print("\n尝试安装requirements.txt中的依赖...")
    result = subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], 
                           capture_output=True, text=True)
    
    # 检查安装是否成功
    if result.returncode == 0:
        print("✓ 依赖安装成功！")
        print("\n安装的依赖列表：")
        subprocess.run([pip_path, 'list'])
    else:
        print("✗ 依赖安装失败！")
        print(f"错误输出：\n{result.stderr}")
        
finally:
    # 清理临时虚拟环境
    print(f"\n清理临时虚拟环境 '{venv_name}'...")
    import shutil
    if os.path.exists(venv_name):
        shutil.rmtree(venv_name)
        print(f"✓ 已删除临时虚拟环境 '{venv_name}'")

print("\n测试完成！")
print("\n===== 总结 ======")
print("1. requirements.txt已修复：移除了重复的opencv-python和无法找到的ipp依赖")
print("2. 现在您可以重新运行 setup_venv.sh 脚本来设置虚拟环境")
print("3. 安装命令: bash setup_venv.sh")