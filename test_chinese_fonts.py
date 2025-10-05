#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中文字体测试脚本
用于测试树莓派5 texie系统上PIL库的中文显示功能
帮助诊断和解决seat_monitor.py中的中文显示问题
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from pathlib import Path

class ChineseFontTester:
    def __init__(self):
        print("======= 中文字体显示测试工具 =======")
        print("此工具用于测试PIL库在树莓派5 texie系统上的中文显示功能")
        print("\n正在初始化测试环境...")
        
        # 创建测试目录
        self.test_dir = "font_test_results"
        Path(self.test_dir).mkdir(parents=True, exist_ok=True)
        
        # 测试文本
        self.test_texts = [
            "座位监控系统",
            "监控区域",
            "空闲",
            "已占用",
            "时长: 5m30s | 进入: 14:25:10",
            "你好，世界！这是一个中文测试。"
        ]
        
        # 字体路径候选列表（与seat_monitor.py保持一致）
        self.font_path_candidates = [
            # 树莓派/Linux系统常用中文字体
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
            # 通用字体名称
            'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'SimHei', 
            'Heiti TC', 'Microsoft YaHei', 'Arial Unicode MS', 
            'Noto Sans CJK', 'Noto Serif CJK', 'Droid Sans Fallback'
        ]
        
        # 搜索系统字体目录，补充更多可能的字体路径
        self.scan_system_fonts()
        
    def scan_system_fonts(self):
        """扫描系统字体目录，寻找更多中文字体"""
        print("\n正在扫描系统字体目录...")
        
        # 常见的字体目录
        font_dirs = [
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            '/home/pi/.fonts'
        ]
        
        # 搜索字体文件
        system_fonts = []
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for root, _, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith(('.ttf', '.ttc', '.otf')):
                            font_path = os.path.join(root, file)
                            system_fonts.append(font_path)
        
        if system_fonts:
            print(f"找到 {len(system_fonts)} 个系统字体文件")
            # 将找到的字体添加到候选列表（去重）
            for font_path in system_fonts:
                if font_path not in self.font_path_candidates:
                    self.font_path_candidates.append(font_path)
        else:
            print("未找到系统字体文件")
    
    def test_font_loading(self):
        """测试字体加载功能"""
        print("\n===== 开始字体加载测试 =====")
        
        successfully_loaded = []
        failed_to_load = []
        
        for font_path in self.font_path_candidates:
            try:
                # 尝试加载字体
                font = ImageFont.truetype(font_path, 12)
                successfully_loaded.append(font_path)
                print(f"✓ 成功加载字体: {font_path}")
            except Exception as e:
                failed_to_load.append((font_path, str(e)))
                print(f"✗ 无法加载字体 {font_path}: {str(e)[:50]}...")
        
        print(f"\n字体加载测试结果:")
        print(f"成功加载: {len(successfully_loaded)} 个字体")
        print(f"加载失败: {len(failed_to_load)} 个字体")
        
        # 保存测试结果
        with open(os.path.join(self.test_dir, "font_test_results.txt"), 'w', encoding='utf-8') as f:
            f.write("===== 字体加载测试结果 =====\n")
            f.write(f"测试时间: {self.get_current_time()}\n")
            f.write(f"成功加载字体 ({len(successfully_loaded)}):\n")
            for font_path in successfully_loaded:
                f.write(f"  - {font_path}\n")
            
            f.write(f"\n加载失败字体 ({len(failed_to_load)}):\n")
            for font_path, error in failed_to_load:
                f.write(f"  - {font_path}: {error}\n")
        
        print(f"测试结果已保存至: {os.path.join(self.test_dir, 'font_test_results.txt')}")
        
        return successfully_loaded
    
    def test_text_rendering(self, font_paths):
        """测试中文文本渲染"""
        if not font_paths:
            print("\n没有可用于测试的字体，跳过文本渲染测试")
            return
        
        print("\n===== 开始文本渲染测试 =====")
        
        # 创建一个黑色背景的图像
        width, height = 800, 600
        
        for i, font_path in enumerate(font_paths[:5]):  # 测试前5个字体
            try:
                # 创建测试图像
                image = Image.new('RGB', (width, height), color=(0, 0, 0))
                draw = ImageDraw.Draw(image)
                
                # 加载字体
                font_size = 20
                font = ImageFont.truetype(font_path, font_size)
                
                # 绘制字体信息
                font_name = os.path.basename(font_path)
                draw.text((20, 20), f"使用字体: {font_name}", font=font, fill=(255, 255, 255))
                
                # 绘制测试文本
                y_position = 60
                for text in self.test_texts:
                    draw.text((20, y_position), text, font=font, fill=(0, 255, 0))
                    y_position += 40
                
                # 保存图像
                image_path = os.path.join(self.test_dir, f"text_render_test_{i+1}_{os.path.basename(font_path).replace('.', '_')}.png")
                image.save(image_path)
                
                # 转换为OpenCV格式并显示（可选）
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                print(f"已生成字体渲染测试图像: {image_path}")
            except Exception as e:
                print(f"渲染字体 {font_path} 时出错: {str(e)}")
    
    def test_opencv_pil_integration(self, font_paths):
        """测试OpenCV和PIL的集成（模拟seat_monitor.py的绘制流程）"""
        if not font_paths:
            print("\n没有可用于测试的字体，跳OpenCV-PIL集成测试")
            return
        
        print("\n===== 开始OpenCV-PIL集成测试 =====")
        
        try:
            # 创建一个黑色背景的OpenCV图像
            width, height = 800, 600
            cv_image = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 转换为PIL格式
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            draw = ImageDraw.Draw(pil_image)
            
            # 加载第一个成功的字体
            font_path = font_paths[0]
            font = ImageFont.truetype(font_path, 20)
            font_large = ImageFont.truetype(font_path, 24)
            
            # 绘制测试文本（模拟seat_monitor.py的逻辑）
            font_name = os.path.basename(font_path)
            draw.text((20, 20), f"集成测试 - 使用字体: {font_name}", font=font_large, fill=(255, 255, 255))
            
            # 模拟座位区域绘制
            region_points = [(100, 100), (700, 100), (700, 500), (100, 500)]
            draw.polygon(region_points, outline=(0, 255, 0), width=2)
            
            # 绘制座位信息
            draw.text((120, 120), "监控区域", font=font, fill=(0, 255, 0))
            draw.text((120, 150), "状态: 已占用", font=font, fill=(0, 255, 0))
            draw.text((120, 180), "时长: 10m30s | 进入: 15:20:30", font=font, fill=(0, 255, 0))
            
            # 绘制系统信息
            draw.text((20, 520), f"系统时间: {self.get_current_time()}", font=font, fill=(255, 255, 255))
            draw.text((20, 550), "系统状态: 正常运行中", font=font, fill=(255, 255, 255))
            
            # 转换回OpenCV格式
            result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 保存结果
            image_path = os.path.join(self.test_dir, "opencv_pil_integration_test.png")
            cv2.imwrite(image_path, result_image)
            
            print(f"已生成OpenCV-PIL集成测试图像: {image_path}")
        except Exception as e:
            print(f"OpenCV-PIL集成测试出错: {str(e)}")
    
    def get_current_time(self):
        """获取当前时间的格式化字符串"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n开始运行所有测试...")
        
        # 1. 测试字体加载
        successfully_loaded_fonts = self.test_font_loading()
        
        # 2. 测试文本渲染
        self.test_text_rendering(successfully_loaded_fonts)
        
        # 3. 测试OpenCV-PIL集成
        self.test_opencv_pil_integration(successfully_loaded_fonts)
        
        print("\n===== 测试完成 =====")
        print(f"测试结果保存在目录: {self.test_dir}")
        print("\n请查看测试图像以确认中文显示效果。")
        print("如果中文显示正常，但seat_monitor.py中仍有问题，建议:")
        print("1. 确保seat_monitor.py使用了正确的字体路径")
        print("2. 检查程序中的文本编码是否为UTF-8")
        print("3. 参考CHINESE_FONT_CONFIGURATION.md文档进行配置")

if __name__ == "__main__":
    tester = ChineseFontTester()
    tester.run_all_tests()