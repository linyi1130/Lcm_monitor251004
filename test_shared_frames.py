#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试共享帧功能
简单测试共享目录的创建和文件写入功能
"""

import os
from datetime import datetime

# 共享目录和文件路径
SHARED_FRAME_DIR = "shared_frames"
SHARED_FRAME_PATH = os.path.join(SHARED_FRAME_DIR, "current_frame.jpg")


def test_shared_directory():
    """测试共享目录的创建和访问权限"""
    try:
        # 确保共享目录存在
        if not os.path.exists(SHARED_FRAME_DIR):
            os.makedirs(SHARED_FRAME_DIR, exist_ok=True)
            print(f"已创建共享目录: {SHARED_FRAME_DIR}")
        else:
            print(f"共享目录已存在: {SHARED_FRAME_DIR}")
        
        # 检查目录权限
        if os.access(SHARED_FRAME_DIR, os.R_OK | os.W_OK | os.X_OK):
            print(f"目录权限检查通过，可以读写执行")
        else:
            print(f"警告：目录权限不足")
        
        # 创建一个简单的文本文件作为测试
        test_file_path = os.path.join(SHARED_FRAME_DIR, "test_file.txt")
        with open(test_file_path, 'w') as f:
            f.write(f"测试文件创建时间: {datetime.now().isoformat()}\n")
            f.write("这是一个测试文件，用于验证共享目录的写入功能。\n")
        
        print(f"已创建测试文件: {test_file_path}")
        
        # 验证文件是否存在并可读
        if os.path.exists(test_file_path):
            file_size = os.path.getsize(test_file_path)
            print(f"测试文件大小: {file_size} 字节")
            
            # 读取文件内容
            with open(test_file_path, 'r') as f:
                content = f.read()
                print(f"测试文件内容: {content.strip()}")
            
            # 清理测试文件
            os.remove(test_file_path)
            print(f"已删除测试文件")
            
            print("测试成功！共享目录功能正常工作。")
        else:
            print("错误：测试文件未创建。")
            
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    print("开始测试共享帧目录功能...")
    test_shared_directory()