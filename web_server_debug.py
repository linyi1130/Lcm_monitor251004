#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
座位监控系统Web服务 - 调试增强版
此版本添加了详细的调试日志，用于解决Web服务无法显示监控画面的问题
"""

import sys
import os
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, request
from threading import Thread, Lock
import logging
from datetime import datetime
import json

# 配置日志 - 设置为DEBUG级别以获取详细信息
logging.basicConfig(level=logging.DEBUG, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('web_server_debug')

class WebMonitorServer:
    def __init__(self, config_file='config.json', debug=True):
        # 加载配置文件
        logger.debug("开始初始化Web服务...")
        self.config = self.load_config(config_file)
        
        # 保存调试模式标志
        self.debug_mode = debug
        logger.debug(f"调试模式: {debug}")
        
        # 初始化Flask应用
        self.app = Flask(__name__)
        
        # 初始化变量
        self.camera = None
        self.frame = None
        self.lock = Lock()
        self.running = False
        
        # 初始化摄像头
        self.initialize_camera()
        
        # 注册路由
        self.register_routes()
        
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            logger.debug(f"尝试加载配置文件: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.debug(f"配置文件加载成功")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            # 返回默认配置
            default_config = {
                "camera": {
                    "resolution": {"width": 1280, "height": 720},
                    "framerate": 10,
                    "rotation": 0
                },
                "web": {
                    "port": 5000,
                    "host": "0.0.0.0",  # 允许所有IP访问
                    "enable_remote": False,  # 默认禁用外网访问
                    "auth_required": False,
                    "username": "admin",
                    "password": "admin"
                }
            }
            logger.info(f"使用默认配置")
            return default_config
    
    def initialize_camera(self):
        """初始化摄像头或准备从已运行的监控系统获取画面"""
        try:
            logger.debug("开始初始化摄像头...")
            
            # 首先确保共享帧目录存在，无论哪种模式
            self.shared_frame_dir = os.path.join(os.path.dirname(__file__), "shared_frames")
            self.frame_file = os.path.join(self.shared_frame_dir, "current_frame.jpg")
            
            logger.debug(f"共享帧目录: {self.shared_frame_dir}")
            logger.debug(f"共享帧文件路径: {self.frame_file}")
            
            try:
                if not os.path.exists(self.shared_frame_dir):
                    logger.debug(f"共享帧目录不存在，尝试创建: {self.shared_frame_dir}")
                    os.makedirs(self.shared_frame_dir, exist_ok=True)
                    logger.info(f"已创建共享帧目录: {self.shared_frame_dir}")
                else:
                    logger.info(f"共享帧目录已存在: {self.shared_frame_dir}")
                    # 检查目录权限
                    read_ok = os.access(self.shared_frame_dir, os.R_OK)
                    write_ok = os.access(self.shared_frame_dir, os.W_OK)
                    logger.debug(f"共享目录读取权限: {read_ok}, 写入权限: {write_ok}")
            except Exception as e:
                logger.error(f"创建共享帧目录失败: {str(e)}")
            
            # 检查共享帧文件状态
            if os.path.exists(self.frame_file):
                file_size = os.path.getsize(self.frame_file)
                read_ok = os.access(self.frame_file, os.R_OK)
                logger.info(f"共享帧文件已存在，大小: {file_size} 字节，可读: {read_ok}")
                # 尝试验证文件格式
                try:
                    img = cv2.imread(self.frame_file)
                    if img is not None:
                        logger.info(f"共享帧文件验证成功，图像尺寸: {img.shape[1]}x{img.shape[0]}")
                    else:
                        logger.warning("共享帧文件验证失败，不是有效的图像文件")
                except Exception as e:
                    logger.error(f"验证共享帧文件时出错: {str(e)}")
            else:
                logger.warning(f"共享帧文件不存在: {self.frame_file}")
            
            # 默认设置为共享模式
            self.frame_source = "shared"
            logger.info(f"帧源模式已设置为: {self.frame_source}")
        except Exception as e:
            logger.error(f"初始化摄像头/共享模式失败: {str(e)}")
            self.camera = None
            self.frame_source = "none"
    
    def register_routes(self):
        """注册Flask路由"""
        logger.debug("开始注册路由...")
        
        @self.app.route('/')
        def index():
            """主页，显示监控画面"""
            logger.debug("接收到主页访问请求")
            
            # 检查认证（如果启用）
            if self.config.get('web', {}).get('auth_required', False):
                auth = request.authorization
                if not auth or auth.username != self.config['web']['username'] or auth.password != self.config['web']['password']:
                    logger.warning("认证失败")
                    return Response('需要认证', 401, {'WWW-Authenticate': 'Basic realm="监控系统"'})
                logger.debug("认证成功")
                
            # 生成HTML页面
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>座位监控系统 - 调试版</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f0f0f0;
                    }
                    h1 {
                        color: #333;
                        text-align: center;
                    }
                    .container {
                        max-width: 1280px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    .video-container {
                        text-align: center;
                        margin-top: 20px;
                    }
                    img {
                        max-width: 100%;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    .status {
                        margin-top: 20px;
                        text-align: center;
                        font-size: 16px;
                        color: #666;
                        background-color: #f9f9f9;
                        padding: 10px;
                        border-radius: 4px;
                    }
                    .debug-info {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #e9f7fe;
                        border-radius: 4px;
                        font-family: monospace;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>座位监控系统实时画面 - 调试版</h1>
                    <div class="video-container">
                        <img id="monitor" src="{{ url_for('video_feed') }}" width="100%" />
                    </div>
                    <div class="status">
                        系统状态: 运行中<br/>
                        访问时间: {{ current_time }}<br/>
                        帧源模式: {{ frame_source }}
                    </div>
                    <div class="debug-info">
                        <strong>调试信息:</strong><br/>
                        服务器时间: {{ current_time }}<br/>
                        共享文件路径: {{ frame_file }}<br/>
                        共享文件存在: {{ file_exists }}<br/>
                        {% if file_exists %}
                        文件大小: {{ file_size }} 字节<br/>
                        {% endif %}
                        配置分辨率: {{ resolution_width }}x{{ resolution_height }}
                    </div>
                </div>
                <script>
                    // 每5秒刷新一次页面，帮助调试
                    setTimeout(function() {
                        location.reload();
                    }, 5000);
                </script>
            </body>
            </html>
            """
            
            # 获取调试信息
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_exists = os.path.exists(self.frame_file)
            file_size = os.path.getsize(self.frame_file) if file_exists else 0
            resolution_width = self.config['camera']['resolution']['width']
            resolution_height = self.config['camera']['resolution']['height']
            
            logger.debug(f"渲染主页，帧源: {self.frame_source}, 文件存在: {file_exists}")
            return render_template_string(html_template, 
                                         current_time=current_time, 
                                         frame_source=self.frame_source, 
                                         frame_file=self.frame_file, 
                                         file_exists=file_exists, 
                                         file_size=file_size, 
                                         resolution_width=resolution_width, 
                                         resolution_height=resolution_height)
            
        @self.app.route('/video_feed')
        def video_feed():
            """视频流端点，返回MJPEG格式的视频流"""
            logger.debug("接收到视频流请求")
            
            # 检查认证（如果启用）
            if self.config.get('web', {}).get('auth_required', False):
                auth = request.authorization
                if not auth or auth.username != self.config['web']['username'] or auth.password != self.config['web']['password']:
                    logger.warning("视频流认证失败")
                    return Response('需要认证', 401, {'WWW-Authenticate': 'Basic realm="监控系统"'})
            
            logger.debug("开始生成视频流")
            return Response(self.generate_video_frames(), 
                            mimetype='multipart/x-mixed-replace; boundary=frame')
                            
        @self.app.route('/status')
        def status():
            """返回系统状态信息 - 增强版"""
            logger.debug("接收到状态请求")
            
            # 检查共享文件
            file_exists = os.path.exists(self.frame_file)
            file_size = os.path.getsize(self.frame_file) if file_exists else 0
            file_readable = os.access(self.frame_file, os.R_OK) if file_exists else False
            
            # 尝试验证文件格式
            file_valid = False
            img_width = 0
            img_height = 0
            if file_exists:
                try:
                    img = cv2.imread(self.frame_file)
                    if img is not None:
                        file_valid = True
                        img_width = img.shape[1]
                        img_height = img.shape[0]
                except Exception as e:
                    logger.error(f"验证图像文件时出错: {str(e)}")
            
            status_info = {
                'status': 'running' if self.running else 'stopped',
                'timestamp': datetime.now().isoformat(),
                'camera_connected': self.camera is not None,
                'frame_source': self.frame_source,
                'shared_file': {
                    'path': self.frame_file,
                    'exists': file_exists,
                    'size_bytes': file_size,
                    'readable': file_readable,
                    'valid_image': file_valid,
                    'width': img_width,
                    'height': img_height
                },
                'config': {
                    'resolution': self.config['camera']['resolution'],
                    'framerate': self.config['camera']['framerate']
                }
            }
            
            logger.debug(f"返回状态信息: {status_info}")
            return status_info
        
        @self.app.route('/test_image')
        def test_image():
            """生成测试图像并保存到共享目录"""
            logger.debug("接收到生成测试图像请求")
            
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
                success = cv2.imwrite(self.frame_file, test_img)
                
                if success:
                    file_size = os.path.getsize(self.frame_file)
                    logger.info(f"测试图像已生成并保存到: {self.frame_file}, 大小: {file_size} 字节")
                    return {"status": "success", "message": f"测试图像已生成", "file_size": file_size}
                else:
                    logger.error(f"无法保存测试图像到: {self.frame_file}")
                    return {"status": "error", "message": "无法生成测试图像"}
            except Exception as e:
                logger.error(f"生成测试图像时出错: {str(e)}")
                return {"status": "error", "message": str(e)}
    
    def generate_video_frames(self):
        """生成视频帧流，支持直接模式和共享模式 - 增强调试版本"""
        logger.debug(f"视频流生成函数启动，帧源模式: {self.frame_source}")
        
        # 确保共享目录和文件路径已初始化
        if not hasattr(self, 'shared_frame_dir'):
            self.shared_frame_dir = os.path.join(os.path.dirname(__file__), "shared_frames")
        if not hasattr(self, 'frame_file'):
            self.frame_file = os.path.join(self.shared_frame_dir, "current_frame.jpg")
            
        logger.debug(f"共享目录: {self.shared_frame_dir}")
        logger.debug(f"共享文件: {self.frame_file}")
        
        # 再次检查并创建共享目录（确保）
        try:
            if not os.path.exists(self.shared_frame_dir):
                logger.debug(f"共享目录不存在，尝试创建: {self.shared_frame_dir}")
                os.makedirs(self.shared_frame_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建共享帧目录失败: {str(e)}")
        
        frame_count = 0
        
        while True:
            frame_count += 1
            logger.debug(f"帧循环 #{frame_count}，当前时间: {datetime.now().strftime('%H:%M:%S')}")
            
            # 根据不同的帧源获取帧
            if hasattr(self, 'frame_source') and self.frame_source == 'shared':
                logger.debug(f"进入共享模式处理")
                
                try:
                    # 检查共享文件是否存在
                    if os.path.exists(self.frame_file):
                        logger.debug(f"共享文件存在: {self.frame_file}")
                        file_size = os.path.getsize(self.frame_file)
                        logger.debug(f"共享文件大小: {file_size} 字节")
                        
                        # 检查文件可读性
                        if os.access(self.frame_file, os.R_OK):
                            logger.debug(f"共享文件可读")
                        else:
                            logger.warning(f"共享文件不可读: {self.frame_file}")
                            time.sleep(1)
                            continue
                        
                        # 尝试读取共享文件
                        logger.debug(f"尝试读取共享文件: {self.frame_file}")
                        frame = cv2.imread(self.frame_file)
                        
                        if frame is not None:
                            logger.debug(f"图像读取成功，尺寸: {frame.shape[1]}x{frame.shape[0]}")
                            
                            # 添加时间戳和模式标识
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cv2.putText(frame, current_time, (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            cv2.putText(frame, "共享模式 (调试)", (10, 60), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            cv2.putText(frame, f"帧 #{frame_count}", (10, 90), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                            
                            # 编码为JPEG
                            ret, buffer = cv2.imencode('.jpg', frame)
                            if ret:
                                logger.debug(f"图像编码成功，缓冲区大小: {len(buffer)} 字节")
                                frame = buffer.tobytes()
                                # 生成MJPEG流
                                yield (b'--frame\r\n' 
                                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                            else:
                                logger.error(f"图像编码失败")
                        else:
                            logger.warning(f"无法读取图像或图像格式无效")
                            # 显示错误画面
                            frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            cv2.putText(frame, "无法读取图像文件", (50, 240), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            cv2.putText(frame, "请检查文件格式", (80, 280), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            ret, buffer = cv2.imencode('.jpg', frame)
                            frame = buffer.tobytes()
                            yield (b'--frame\r\n' 
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    else:
                        # 如果共享文件不存在，显示等待画面
                        logger.warning(f"共享文件不存在: {self.frame_file}")
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "等待监控系统画面...", (50, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        cv2.putText(frame, f"文件路径: {self.frame_file}", (10, 400), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        ret, buffer = cv2.imencode('.jpg', frame)
                        frame = buffer.tobytes()
                        yield (b'--frame\r\n' 
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    
                    # 控制帧率
                    sleep_time = 1 / self.config['camera']['framerate']
                    logger.debug(f"帧 #{frame_count} 处理完成，准备休眠 {sleep_time:.2f} 秒")
                    time.sleep(sleep_time)
                except Exception as e:
                    logger.error(f"共享模式获取帧时出错: {str(e)}")
                    time.sleep(1)
            elif self.camera is not None:
                # 直接模式：直接从摄像头获取帧
                logger.debug(f"进入直接模式处理")
                try:
                    # 获取帧
                    if hasattr(self.camera, 'capture_array'):
                        # Picamera2
                        frame = self.camera.capture_array()
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # 转换颜色空间
                    else:
                        # OpenCV
                        ret, frame = self.camera.read()
                        if not ret:
                            logger.error("无法获取摄像头帧")
                            time.sleep(1)
                            continue
                    
                    # 按配置旋转图像
                    if self.config['camera']['rotation'] != 0:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE * (self.config['camera']['rotation'] // 90))
                    
                    # 添加时间戳
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(frame, current_time, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # 编码为JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if not ret:
                        logger.error("无法编码帧")
                        time.sleep(1)
                        continue
                    
                    frame = buffer.tobytes()
                    
                    # 生成MJPEG流
                    yield (b'--frame\r\n' 
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    
                    # 控制帧率
                    time.sleep(1 / self.config['camera']['framerate'])
                    
                except Exception as e:
                    logger.error(f"直接模式获取帧时出错: {str(e)}")
                    time.sleep(1)
            else:
                # 摄像头未初始化，显示错误画面
                logger.debug(f"摄像头未初始化，显示错误画面")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "摄像头未初始化", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(frame, f"模式: {self.frame_source}", (10, 400), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1)
    
    def start(self):
        """启动Web服务"""
        try:
            self.running = True
            logger.info(f"Web服务启动信息:")
            logger.info(f"  - 主机: {self.config['web'].get('host', '0.0.0.0')}")
            logger.info(f"  - 端口: {self.config['web'].get('port', 5000)}")
            logger.info(f"  - 帧源模式: {self.frame_source}")
            logger.info(f"  - 共享文件路径: {self.frame_file}")
            logger.info(f"  - 调试模式: 已启用")
            logger.info(f"请在浏览器中访问 http://{self.config['web'].get('host', '0.0.0.0')}:{self.config['web'].get('port', 5000)} 查看监控画面")
            logger.info(f"调试端点: /status 查看详细系统状态")
            logger.info(f"测试功能: /test_image 生成测试图像")
            
            # 启动Flask服务
            self.app.run(host=self.config['web'].get('host', '0.0.0.0'), 
                         port=self.config['web'].get('port', 5000), 
                         debug=self.debug_mode, 
                         threaded=True)
            
        except KeyboardInterrupt:
            logger.info("Web服务被用户中断")
        except Exception as e:
            logger.error(f"Web服务启动失败: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """停止Web服务并清理资源"""
        try:
            self.running = False
            logger.info("正在停止Web服务...")
            
            if self.camera is not None:
                if hasattr(self.camera, 'stop'):
                    self.camera.stop()
                elif hasattr(self.camera, 'release'):
                    self.camera.release()
                logger.info("摄像头已关闭")
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")

# 支持作为独立脚本运行
if __name__ == '__main__':
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='座位监控系统Web服务 - 调试增强版')
    parser.add_argument('-d', '--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--enable-remote', action='store_true', help='启用外网访问（覆盖配置文件）')
    parser.add_argument('--auth', action='store_true', help='启用基本认证（覆盖配置文件）')
    args = parser.parse_args()
    
    # 创建并启动Web服务器
    server = WebMonitorServer(config_file=args.config, debug=args.debug)
    
    # 覆盖配置
    if args.enable_remote:
        if 'web' not in server.config:
            server.config['web'] = {}
        server.config['web']['enable_remote'] = True
    
    if args.auth:
        if 'web' not in server.config:
            server.config['web'] = {}
        server.config['web']['auth_required'] = True
    
    # 启动服务
    server.start()