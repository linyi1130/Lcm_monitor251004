#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
座位监控系统Web服务
提供摄像头实时画面的Web访问功能
支持内网和外网访问
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

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('web_server')

class WebMonitorServer:
    def __init__(self, config_file='config.json', debug=False):
        # 加载配置文件
        self.config = self.load_config(config_file)
        
        # 保存调试模式标志
        self.debug_mode = debug
        
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
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            # 返回默认配置
            return {
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
    
    def initialize_camera(self):
        """初始化摄像头或准备从已运行的监控系统获取画面"""
        try:
            # 尝试导入Picamera2（树莓派专用）
            try:
                from picamera2 import Picamera2
                
                # 尝试初始化摄像头，但如果失败，则准备使用替代方式
                try:
                    self.camera = Picamera2()
                    camera_config = self.camera.create_preview_configuration(
                        main={"size": (self.config['camera']['resolution']['width'], 
                                      self.config['camera']['resolution']['height'])}
                    )
                    self.camera.configure(camera_config)
                    self.camera.start()
                    if self.config['camera']['rotation'] != 0:
                        self.camera.rotation = self.config['camera']['rotation']
                    logger.info(f"已初始化Picamera2摄像头，分辨率: {self.config['camera']['resolution']['width']}x{self.config['camera']['resolution']['height']}")
                    # 设置为直接模式
                    self.frame_source = "direct"
                except RuntimeError as e:
                    # 如果摄像头被占用，切换到替代模式
                    if "Device or resource busy" in str(e):
                        logger.warning("摄像头已被占用，将使用替代方式获取画面")
                        self.camera = None
                        # 创建一个共享目录用于帧共享
                        self.shared_frame_dir = os.path.join(os.path.dirname(__file__), "shared_frames")
                        if not os.path.exists(self.shared_frame_dir):
                            os.makedirs(self.shared_frame_dir)
                        self.frame_file = os.path.join(self.shared_frame_dir, "current_frame.jpg")
                        # 设置为共享模式
                        self.frame_source = "shared"
                    else:
                        raise e
            except ImportError:
                # 如果没有Picamera2，尝试使用OpenCV
                logger.info("尝试使用OpenCV初始化摄像头")
                try:
                    self.camera = cv2.VideoCapture(0)
                    if not self.camera.isOpened():
                        # 摄像头被占用，切换到共享模式
                        logger.warning("摄像头已被占用，将使用替代方式获取画面")
                        self.camera = None
                        self.shared_frame_dir = os.path.join(os.path.dirname(__file__), "shared_frames")
                        if not os.path.exists(self.shared_frame_dir):
                            os.makedirs(self.shared_frame_dir)
                        self.frame_file = os.path.join(self.shared_frame_dir, "current_frame.jpg")
                        self.frame_source = "shared"
                    else:
                        # 设置分辨率
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['resolution']['width'])
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['resolution']['height'])
                        logger.info(f"已初始化OpenCV摄像头，分辨率: {self.config['camera']['resolution']['width']}x{self.config['camera']['resolution']['height']}")
                        self.frame_source = "direct"
                except Exception as e:
                    logger.error(f"OpenCV初始化失败: {str(e)}")
                    self.camera = None
                    self.frame_source = "none"
        except Exception as e:
            logger.error(f"初始化摄像头失败: {str(e)}")
            self.camera = None
            self.frame_source = "none"
    
    def register_routes(self):
        """注册Flask路由"""
        @self.app.route('/')
        def index():
            """主页，显示监控画面"""
            # 检查认证（如果启用）
            if self.config.get('web', {}).get('auth_required', False):
                auth = request.authorization
                if not auth or auth.username != self.config['web']['username'] or auth.password != self.config['web']['password']:
                    return Response('需要认证', 401, {'WWW-Authenticate': 'Basic realm="监控系统"'})
                    
            # 生成HTML页面
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>座位监控系统</title>
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
                    video {
                        max-width: 100%;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    .status {
                        margin-top: 20px;
                        text-align: center;
                        font-size: 16px;
                        color: #666;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>座位监控系统实时画面</h1>
                    <div class="video-container">
                        <img src="{{ url_for('video_feed') }}" width="100%" />
                    </div>
                    <div class="status">
                        系统状态: 运行中<br/>
                        访问时间: {{ current_time }}
                    </div>
                </div>
            </body>
            </html>
            """
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return render_template_string(html_template, current_time=current_time)
            
        @self.app.route('/video_feed')
        def video_feed():
            """视频流端点，返回MJPEG格式的视频流"""
            # 检查认证（如果启用）
            if self.config.get('web', {}).get('auth_required', False):
                auth = request.authorization
                if not auth or auth.username != self.config['web']['username'] or auth.password != self.config['web']['password']:
                    return Response('需要认证', 401, {'WWW-Authenticate': 'Basic realm="监控系统"'})
                    
            return Response(self.generate_video_frames(), 
                            mimetype='multipart/x-mixed-replace; boundary=frame')
                            
        @self.app.route('/status')
        def status():
            """返回系统状态信息"""
            status_info = {
                'status': 'running' if self.running else 'stopped',
                'timestamp': datetime.now().isoformat(),
                'camera_connected': self.camera is not None,
                'config': {
                    'resolution': self.config['camera']['resolution'],
                    'framerate': self.config['camera']['framerate']
                }
            }
            return status_info
    
    def generate_video_frames(self):
        """生成视频帧流，支持直接模式和共享模式"""
        while True:
            # 根据不同的帧源获取帧
            if hasattr(self, 'frame_source') and self.frame_source == 'shared':
                # 共享模式：从共享文件读取帧
                try:
                    # 检查共享文件是否存在
                    if os.path.exists(self.frame_file):
                        # 尝试读取共享文件
                        frame = cv2.imread(self.frame_file)
                        if frame is not None:
                            # 添加时间戳和模式标识
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cv2.putText(frame, current_time, (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            cv2.putText(frame, "共享模式", (10, 60), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # 编码为JPEG
                            ret, buffer = cv2.imencode('.jpg', frame)
                            if ret:
                                frame = buffer.tobytes()
                                # 生成MJPEG流
                                yield (b'--frame\r\n' 
                                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    else:
                        # 如果共享文件不存在，显示等待画面
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "等待监控系统画面...", (50, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        ret, buffer = cv2.imencode('.jpg', frame)
                        frame = buffer.tobytes()
                        yield (b'--frame\r\n' 
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    # 控制帧率
                    time.sleep(1 / self.config['camera']['framerate'])
                except Exception as e:
                    logger.error(f"共享模式获取帧时出错: {str(e)}")
                    time.sleep(1)
            elif self.camera is not None:
                # 直接模式：直接从摄像头获取帧
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
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "摄像头未初始化", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1)
    
    def start(self):
        """启动Web服务"""
        try:
            self.running = True
            
            # 启动帧获取线程（如果需要）
            # 在这个简单版本中，我们直接在generate_video_frames中获取帧
            
            # 读取Web配置
            web_config = self.config.get('web', {})
            host = web_config.get('host', '0.0.0.0')
            port = web_config.get('port', 5000)
            enable_remote = web_config.get('enable_remote', False)
            
            logger.info(f"Web服务启动信息:")
            logger.info(f"  - 主机: {host}")
            logger.info(f"  - 端口: {port}")
            logger.info(f"  - 外网访问: {'已启用' if enable_remote else '已禁用'}")
            logger.info(f"  - 认证要求: {'已启用' if web_config.get('auth_required', False) else '已禁用'}")
            
            if enable_remote:
                logger.warning("注意: 外网访问已启用，建议配置强密码和考虑使用HTTPS")
            
            logger.info(f"请在浏览器中访问 http://{host}:{port} 查看监控画面")
            
            # 启动Flask服务
            # 注意：在生产环境中应使用gunicorn或uWSGI替代Flask的开发服务器
            self.app.run(host=host, port=port, debug=self.debug_mode, threaded=True)
            
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
    parser = argparse.ArgumentParser(description='座位监控系统Web服务')
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