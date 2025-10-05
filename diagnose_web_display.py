#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本：检查Web服务无法显示监控画面的问题
此脚本将测试：
1. 文件访问权限
2. 图像文件的有效性
3. 增加详细日志以便调试
4. 提供修复建议
"""

import os
import sys
import cv2
import numpy as np
import json
import time
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('diagnose_web_display')

class WebDisplayDiagnostic:
    def __init__(self):
        # 关键路径定义
        self.shared_frame_dir = os.path.join(os.path.dirname(__file__), "shared_frames")
        self.frame_file = os.path.join(self.shared_frame_dir, "current_frame.jpg")
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")
        self.web_server_file = os.path.join(os.path.dirname(__file__), "web_server.py")
        
        # 运行所有诊断测试
        self.run_all_tests()
    
    def run_all_tests(self):
        """运行所有诊断测试"""
        logger.info("=== Web服务显示问题诊断工具 ===")
        
        # 1. 检查文件和目录存在性
        self.check_file_existence()
        
        # 2. 检查权限
        self.check_permissions()
        
        # 3. 检查图像文件有效性
        self.check_image_validity()
        
        # 4. 创建测试图像并验证
        self.create_test_image()
        
        # 5. 检查配置文件
        self.check_config_file()
        
        # 6. 分析web_server.py代码
        self.analyze_web_server_code()
        
        # 7. 提供修复建议
        self.provide_fix_recommendations()
        
        logger.info("=== 诊断完成 ===")
    
    def check_file_existence(self):
        """检查必要文件和目录是否存在"""
        logger.info("\n1. 检查文件和目录存在性：")
        
        # 检查共享帧目录
        if os.path.exists(self.shared_frame_dir):
            logger.info(f"✓ 共享帧目录存在: {self.shared_frame_dir}")
        else:
            logger.error(f"✗ 共享帧目录不存在: {self.shared_frame_dir}")
            try:
                os.makedirs(self.shared_frame_dir, exist_ok=True)
                logger.info(f"  → 已创建共享帧目录: {self.shared_frame_dir}")
            except Exception as e:
                logger.error(f"  → 创建目录失败: {str(e)}")
        
        # 检查帧文件
        if os.path.exists(self.frame_file):
            logger.info(f"✓ 当前帧文件存在: {self.frame_file}")
            file_size = os.path.getsize(self.frame_file)
            logger.info(f"  → 文件大小: {file_size} 字节")
        else:
            logger.error(f"✗ 当前帧文件不存在: {self.frame_file}")
        
        # 检查配置文件
        if os.path.exists(self.config_file):
            logger.info(f"✓ 配置文件存在: {self.config_file}")
        else:
            logger.warning(f"⚠ 配置文件不存在: {self.config_file}，将使用默认配置")
        
        # 检查web_server.py
        if os.path.exists(self.web_server_file):
            logger.info(f"✓ Web服务文件存在: {self.web_server_file}")
        else:
            logger.error(f"✗ Web服务文件不存在: {self.web_server_file}")
    
    def check_permissions(self):
        """检查文件权限"""
        logger.info("\n2. 检查文件权限：")
        
        # 检查共享帧目录权限
        if os.path.exists(self.shared_frame_dir):
            read_ok = os.access(self.shared_frame_dir, os.R_OK)
            write_ok = os.access(self.shared_frame_dir, os.W_OK)
            logger.info(f"  共享帧目录读取权限: {'✓' if read_ok else '✗'}")
            logger.info(f"  共享帧目录写入权限: {'✓' if write_ok else '✗'}")
        
        # 检查帧文件权限
        if os.path.exists(self.frame_file):
            read_ok = os.access(self.frame_file, os.R_OK)
            logger.info(f"  当前帧文件读取权限: {'✓' if read_ok else '✗'}")
    
    def check_image_validity(self):
        """检查图像文件的有效性"""
        logger.info("\n3. 检查图像文件有效性：")
        
        if not os.path.exists(self.frame_file):
            logger.warning("⚠ 无法检查图像有效性，文件不存在")
            return
        
        try:
            # 尝试使用cv2读取图像
            img = cv2.imread(self.frame_file)
            if img is not None:
                logger.info(f"✓ 图像读取成功")
                logger.info(f"  → 图像尺寸: {img.shape[1]}x{img.shape[0]}")
                logger.info(f"  → 通道数: {img.shape[2] if len(img.shape) > 2 else 1}")
                
                # 尝试显示图像信息
                mean_color = np.mean(img, axis=(0, 1))
                logger.info(f"  → 平均颜色值: B={mean_color[0]:.2f}, G={mean_color[1]:.2f}, R={mean_color[2]:.2f}")
            else:
                logger.error("✗ 图像读取失败，文件格式可能无效")
        except Exception as e:
            logger.error(f"✗ 图像检查时出错: {str(e)}")
    
    def create_test_image(self):
        """创建一个简单的测试图像用于验证"""
        logger.info("\n4. 创建测试图像：")
        
        try:
            # 创建一个640x480的彩色图像
            test_img = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # 绘制一些简单的图形
            cv2.rectangle(test_img, (50, 50), (590, 430), (20, 20, 20), -1)
            cv2.putText(test_img, "测试图像", (150, 200), 
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
            cv2.putText(test_img, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                        (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 保存图像
            test_file = os.path.join(self.shared_frame_dir, "test_image.jpg")
            success = cv2.imwrite(test_file, test_img)
            
            if success:
                logger.info(f"✓ 测试图像已创建: {test_file}")
                logger.info(f"  → 文件大小: {os.path.getsize(test_file)} 字节")
                
                # 同时更新current_frame.jpg
                success = cv2.imwrite(self.frame_file, test_img)
                if success:
                    logger.info(f"✓ current_frame.jpg已更新为测试图像")
                else:
                    logger.error(f"✗ 无法更新current_frame.jpg")
            else:
                logger.error(f"✗ 无法创建测试图像")
        except Exception as e:
            logger.error(f"✗ 创建测试图像时出错: {str(e)}")
    
    def check_config_file(self):
        """检查配置文件内容"""
        logger.info("\n5. 检查配置文件：")
        
        if not os.path.exists(self.config_file):
            logger.warning("⚠ 配置文件不存在")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                logger.info("  配置文件内容摘要：")
                
                # 检查相机配置
                if 'camera' in config:
                    camera_config = config['camera']
                    width = camera_config.get('resolution', {}).get('width', 'N/A')
                    height = camera_config.get('resolution', {}).get('height', 'N/A')
                    framerate = camera_config.get('framerate', 'N/A')
                    rotation = camera_config.get('rotation', 'N/A')
                    
                    logger.info(f"  相机分辨率: {width}x{height}")
                    logger.info(f"  帧率: {framerate}")
                    logger.info(f"  旋转角度: {rotation}")
                else:
                    logger.warning("  配置中没有相机设置")
                
                # 检查Web服务配置
                if 'web' in config:
                    web_config = config['web']
                    port = web_config.get('port', 'N/A')
                    host = web_config.get('host', 'N/A')
                    enable_remote = web_config.get('enable_remote', False)
                    auth_required = web_config.get('auth_required', False)
                    
                    logger.info(f"  Web服务端口: {port}")
                    logger.info(f"  主机地址: {host}")
                    logger.info(f"  外网访问: {'已启用' if enable_remote else '已禁用'}")
                    logger.info(f"  认证要求: {'已启用' if auth_required else '已禁用'}")
                else:
                    logger.warning("  配置中没有Web服务设置")
        except Exception as e:
            logger.error(f"✗ 读取配置文件时出错: {str(e)}")
    
    def analyze_web_server_code(self):
        """分析web_server.py中的关键代码"""
        logger.info("\n6. 分析Web服务代码：")
        
        if not os.path.exists(self.web_server_file):
            logger.warning("⚠ Web服务文件不存在，无法分析")
            return
        
        try:
            with open(self.web_server_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查共享模式相关代码
                if 'frame_source == "shared"' in content:
                    logger.info("✓ 检测到共享模式代码")
                else:
                    logger.warning("⚠ 未检测到明确的共享模式代码")
                
                # 检查cv2.imread使用
                if 'cv2.imread' in content:
                    logger.info("✓ 检测到cv2.imread函数调用")
                else:
                    logger.warning("⚠ 未检测到cv2.imread函数调用")
                
                # 检查共享文件路径
                if 'shared_frames/current_frame.jpg' in content:
                    logger.info("✓ 检测到正确的共享文件路径")
                else:
                    logger.warning("⚠ 未检测到明确的共享文件路径")
                
                # 检查视频流生成
                if 'generate_video_frames' in content:
                    logger.info("✓ 检测到视频流生成函数")
                else:
                    logger.warning("⚠ 未检测到视频流生成函数")
        except Exception as e:
            logger.error(f"✗ 分析Web服务代码时出错: {str(e)}")
    
    def provide_fix_recommendations(self):
        """提供修复建议"""
        logger.info("\n7. 修复建议：")
        
        # 1. 创建增强版web_server_debug.py
        try:
            debug_web_server = self.create_debug_web_server()
            if debug_web_server:
                logger.info("✓ 已创建增强版调试Web服务: web_server_debug.py")
                logger.info("  → 运行方式: python3 web_server_debug.py")
        except Exception as e:
            logger.error(f"✗ 创建调试Web服务失败: {str(e)}")
        
        # 2. 其他建议
        logger.info("\n其他建议：")
        logger.info("  - 确保seat_monitor.py正在运行并生成current_frame.jpg")
        logger.info("  - 检查防火墙设置，确保5000端口已开放")
        logger.info("  - 尝试清空浏览器缓存后重新访问")
        logger.info("  - 检查浏览器控制台是否有错误信息")
    
    def create_debug_web_server(self):
        """创建一个增强版的调试Web服务器"""
        debug_server_path = os.path.join(os.path.dirname(__file__), "web_server_debug.py")
        
        # 读取原始web_server.py
        if not os.path.exists(self.web_server_file):
            return False
        
        try:
            with open(self.web_server_file, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            # 在共享模式相关代码中添加更多日志
            debug_code = original_code
            
            # 在generate_video_frames函数中添加更多日志
            debug_code = debug_code.replace(
                "def generate_video_frames(self):",
                "def generate_video_frames(self):\n        # 增强的调试日志\n        frame_source_status = self.frame_source if hasattr(self, 'frame_source') else '未知'\n        logger.info(f'视频流生成开始，帧源: {{{{frame_source_status}}}}')"
            )
            
            # 在共享模式中添加更多日志
            debug_code = debug_code.replace(
                "# 共享模式：从共享文件读取帧",
                "# 共享模式：从共享文件读取帧\n        logger.debug(f'检查共享文件: {self.frame_file}')"
            )
            
            debug_code = debug_code.replace(
                "if os.path.exists(self.frame_file):",
                "if os.path.exists(self.frame_file):\n            logger.debug(f'共享文件存在，大小: {os.path.getsize(self.frame_file)} 字节')"
            )
            
            debug_code = debug_code.replace(
                "frame = cv2.imread(self.frame_file)",
                "frame = cv2.imread(self.frame_file)\n            read_status = '成功' if frame is not None else '失败'\n            logger.debug(f'图像读取结果: {{{{read_status}}}}')"
            )
            
            debug_code = debug_code.replace(
                "if frame is not None:",
                "if frame is not None:\n                img_width = frame.shape[1]\n                img_height = frame.shape[0]\n                logger.debug(f'图像尺寸: {{{{img_width}}}}x{{{{img_height}}}}')"
            )
            
            # 更新日志级别为DEBUG
            debug_code = debug_code.replace(
                "logging.basicConfig(level=logging.INFO,",
                "logging.basicConfig(level=logging.DEBUG,"
            )
            
            # 添加注释说明这是调试版本
            debug_code = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
# 座位监控系统Web服务 - 调试增强版
# 此版本添加了详细的调试日志，用于解决Web服务无法显示监控画面的问题
""" + debug_code
            
            # 保存调试版本
            with open(debug_server_path, 'w', encoding='utf-8') as f:
                f.write(debug_code)
            
            # 添加执行权限
            os.chmod(debug_server_path, 0o755)
            
            return True
        except Exception as e:
            logger.error(f"✗ 创建调试Web服务时出错: {str(e)}")
            return False

if __name__ == "__main__":
    # 运行诊断工具
    diagnostic = WebDisplayDiagnostic()