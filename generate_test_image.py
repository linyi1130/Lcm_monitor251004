#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成测试图像
在共享目录中创建一个简单的测试图像文件，用于验证Web服务的共享模式
"""

import os
from datetime import datetime

# 共享目录和文件路径
SHARED_FRAME_DIR = "shared_frames"
SHARED_FRAME_PATH = os.path.join(SHARED_FRAME_DIR, "current_frame.jpg")


def generate_test_image():
    """生成一个测试图像文件并保存到共享目录"""
    try:
        # 确保共享目录存在
        if not os.path.exists(SHARED_FRAME_DIR):
            os.makedirs(SHARED_FRAME_DIR, exist_ok=True)
            print(f"已创建共享目录: {SHARED_FRAME_DIR}")
        else:
            print(f"共享目录已存在: {SHARED_FRAME_DIR}")
        
        # 尝试使用PIL或简单的方式创建测试图像
        try:
            # 优先尝试使用PIL库
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建一个640x480的黑色图像
            width, height = 640, 480
            image = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("simhei.ttf", 24)
            except:
                try:
                    font = ImageFont.truetype("Arial.ttf", 24)
                except:
                    font = None
            
            # 添加测试文字
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if font:
                draw.text((150, 150), "测试画面", font=font, fill=(0, 255, 0))
                draw.text((150, 200), current_time, font=font, fill=(255, 255, 255))
                draw.text((50, 250), "共享模式测试图像", font=font, fill=(255, 0, 0))
            else:
                # 如果没有字体，使用默认绘制
                draw.text((150, 150), "测试画面", fill=(0, 255, 0))
                draw.text((150, 200), current_time, fill=(255, 255, 255))
                draw.text((50, 250), "共享模式测试图像", fill=(255, 0, 0))
            
            # 保存图像
            image.save(SHARED_FRAME_PATH)
            print(f"已使用PIL创建测试图像: {SHARED_FRAME_PATH}")
            
        except ImportError:
            # 如果PIL不可用，尝试使用cv2创建图像
            try:
                import cv2
                import numpy as np
                
                # 创建一个640x480的黑色图像
                width, height = 640, 480
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                
                # 添加测试文字
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, "测试画面", (150, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, current_time, (150, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "共享模式测试图像", (50, 250), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                
                # 保存为真正的JPEG图像
                cv2.imwrite(SHARED_FRAME_PATH, frame)
                print(f"已使用OpenCV创建测试图像: {SHARED_FRAME_PATH}")
            except ImportError:
                # 如果OpenCV也不可用，记录错误但不创建假图像文件
                print("错误：PIL和OpenCV库都不可用，无法创建真正的图像文件。")
                print("请安装PIL或OpenCV库以生成正确的测试图像。")
                # 不创建假的JPEG文件，避免干扰seat_monitor.py的正常工作
                if os.path.exists(SHARED_FRAME_PATH):
                    os.remove(SHARED_FRAME_PATH)
                    print(f"已删除旧的测试文件: {SHARED_FRAME_PATH}")
        
        # 验证文件是否存在
        if os.path.exists(SHARED_FRAME_PATH):
            file_size = os.path.getsize(SHARED_FRAME_PATH)
            print(f"测试图像文件大小: {file_size} 字节")
            print("测试图像已生成，请启动Web服务查看共享模式是否正常工作。")
        else:
            print("错误：测试图像文件未创建。")
            
    except Exception as e:
        print(f"生成测试图像过程中发生错误: {str(e)}")


if __name__ == "__main__":
    print("开始生成测试图像...")
    generate_test_image()