#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
座位监控系统Web服务 - 极简调试版
此版本只包含最基本的功能，用于解决Web服务无法显示监控画面的问题
仅依赖Flask和OpenCV，易于安装和运行
"""

import sys
import os
import time
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, send_file, redirect
from datetime import datetime
import io

# 创建Flask应用
app = Flask(__name__)

# 配置共享帧文件路径
SHARED_FRAME_DIR = os.path.join(os.path.dirname(__file__), "shared_frames")
CURRENT_FRAME_FILE = os.path.join(SHARED_FRAME_DIR, "current_frame.jpg")

# 静态图像端点
@app.route('/static_image')
def static_image():
    """提供静态图像文件，不使用视频流格式"""
    try:
        # 首先检查文件是否存在且可读
        if not os.path.exists(CURRENT_FRAME_FILE):
            print(f"共享帧文件不存在: {CURRENT_FRAME_FILE}")
            # 创建一个错误图像返回
            error_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_img, "无法读取图像文件", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, img_encoded = cv2.imencode('.jpg', error_img)
            return Response(img_encoded.tobytes(), mimetype='image/jpeg')
        
        # 检查文件是否可读
        if not os.access(CURRENT_FRAME_FILE, os.R_OK):
            print(f"共享帧文件存在但不可读: {CURRENT_FRAME_FILE}")
            error_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_img, "图像文件不可读", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, img_encoded = cv2.imencode('.jpg', error_img)
            return Response(img_encoded.tobytes(), mimetype='image/jpeg')
        
        # 使用send_file直接提供文件，添加缓存控制头
        return send_file(
            CURRENT_FRAME_FILE,
            mimetype='image/jpeg',
            as_attachment=False,
            conditional=True
        )
    except Exception as e:
        print(f"提供静态图像时出错: {str(e)}")
        # 创建一个简单的错误图像
        error_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_img, "提供图像时出错", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, img_encoded = cv2.imencode('.jpg', error_img)
        return Response(img_encoded.tobytes(), mimetype='image/jpeg')

# 静态图像测试页面端点 - 已更新为新的调试页面
@app.route('/static_image_test.html')
def static_image_test_page():
    """重定向到新的调试页面"""
    return redirect('/web_monitor_debug.html')

# 新的监控调试页面端点
@app.route('/web_monitor_debug.html')
def web_monitor_debug_page():
    """提供新的监控调试页面"""
    try:
        # 读取HTML文件内容
        with open('web_monitor_debug.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return Response(html_content, mimetype='text/html')
    except Exception as e:
        print(f"提供监控调试页面时出错: {str(e)}")
        # 返回错误页面
        error_html = f"<html><body><h1>错误</h1><p>无法加载监控调试页面: {str(e)}</p></body></html>"
        return Response(error_html, mimetype='text/html')

# 检查共享帧目录和文件
print("=== 座位监控系统 - 极简调试版 ===")
print(f"共享帧目录: {SHARED_FRAME_DIR}")
print(f"共享帧文件路径: {CURRENT_FRAME_FILE}")

# 检查并创建共享帧目录
if not os.path.exists(SHARED_FRAME_DIR):
    print(f"共享帧目录不存在，尝试创建: {SHARED_FRAME_DIR}")
    try:
        os.makedirs(SHARED_FRAME_DIR, exist_ok=True)
        print(f"已创建共享帧目录: {SHARED_FRAME_DIR}")
    except Exception as e:
        print(f"创建共享帧目录失败: {str(e)}")

# 检查共享帧文件状态
if os.path.exists(CURRENT_FRAME_FILE):
    file_size = os.path.getsize(CURRENT_FRAME_FILE)
    read_ok = os.access(CURRENT_FRAME_FILE, os.R_OK)
    print(f"共享帧文件已存在，大小: {file_size} 字节，可读: {read_ok}")
    # 尝试验证文件格式
    try:
        img = cv2.imread(CURRENT_FRAME_FILE)
        if img is not None:
            print(f"共享帧文件验证成功，图像尺寸: {img.shape[1]}x{img.shape[0]}")
        else:
            print("警告: 共享帧文件验证失败，不是有效的图像文件")
    except Exception as e:
        print(f"验证共享帧文件时出错: {str(e)}")
else:
    print(f"警告: 共享帧文件不存在: {CURRENT_FRAME_FILE}")

@app.route('/')
def index():
    """主页，显示监控画面"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 接收到主页访问请求")
    
    # 生成HTML页面
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>座位监控系统 - 极简调试版</title>
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
            <h1>座位监控系统实时画面 - 极简调试版</h1>
            <div class="video-container">
                <img id="monitor" src="{{ url_for('video_feed') }}" width="100%" />
            </div>
            <div class="status">
                系统状态: 运行中<br/>
                访问时间: {{ current_time }}<br/>
                刷新间隔: 5秒
            </div>
            <div class="debug-info">
                <strong>调试信息:</strong><br/>
                服务器时间: {{ current_time }}<br/>
                共享文件路径: {{ frame_file }}<br/>
                共享文件存在: {{ file_exists }}<br/>
                {% if file_exists %}
                文件大小: {{ file_size }} 字节<br/>
                {% endif %}
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
    file_exists = os.path.exists(CURRENT_FRAME_FILE)
    file_size = os.path.getsize(CURRENT_FRAME_FILE) if file_exists else 0
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 渲染主页，文件存在: {file_exists}")
    return render_template_string(html_template, 
                                 current_time=current_time, 
                                 frame_file=CURRENT_FRAME_FILE, 
                                 file_exists=file_exists, 
                                 file_size=file_size)

@app.route('/video_feed')
def video_feed():
    """视频流端点，返回MJPEG格式的视频流"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 接收到视频流请求")
    return Response(generate_video_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/test_image')
def test_image():
    """生成测试图像并保存到共享目录"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 接收到生成测试图像请求")
    
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
        success = cv2.imwrite(CURRENT_FRAME_FILE, test_img)
        
        if success:
            file_size = os.path.getsize(CURRENT_FRAME_FILE)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 测试图像已生成并保存到: {CURRENT_FRAME_FILE}, 大小: {file_size} 字节")
            return "测试图像已生成成功，<a href='/'>返回主页</a>"
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 无法保存测试图像到: {CURRENT_FRAME_FILE}")
            return "无法生成测试图像"
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 生成测试图像时出错: {str(e)}")
        return f"生成测试图像时出错: {str(e)}"

def generate_video_frames():
    """生成视频帧流 - 极简调试版"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 视频流生成函数启动")
    
    frame_count = 0
    
    while True:
        frame_count += 1
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 帧循环 #{frame_count}")
        
        try:
            # 检查共享文件是否存在
            if os.path.exists(CURRENT_FRAME_FILE):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 共享文件存在: {CURRENT_FRAME_FILE}")
                file_size = os.path.getsize(CURRENT_FRAME_FILE)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 共享文件大小: {file_size} 字节")
                
                # 检查文件可读性
                if os.access(CURRENT_FRAME_FILE, os.R_OK):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 共享文件可读")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 共享文件不可读: {CURRENT_FRAME_FILE}")
                    time.sleep(1)
                    continue
                
                # 尝试读取共享文件
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 尝试读取共享文件: {CURRENT_FRAME_FILE}")
                frame = cv2.imread(CURRENT_FRAME_FILE)
                
                if frame is not None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 图像读取成功，尺寸: {frame.shape[1]}x{frame.shape[0]}")
                    
                    # 添加时间戳和调试信息
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(frame, current_time, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(frame, "调试模式", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # 编码为JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 图像编码成功，缓冲区大小: {len(buffer)} 字节")
                        frame = buffer.tobytes()
                        # 生成MJPEG流
                        yield (b'--frame\r\n' 
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: 图像编码失败")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 无法读取图像或图像格式无效")
                    # 显示错误画面
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "无法读取图像文件", (50, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n' 
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                # 如果共享文件不存在，显示等待画面
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 警告: 共享帧文件不存在: {CURRENT_FRAME_FILE}")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "等待监控系统画面...", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # 控制帧率
            time.sleep(1)  # 每秒更新一次
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: 获取帧时出错: {str(e)}")
            time.sleep(1)

if __name__ == '__main__':
    # 确保共享帧目录存在
    if not os.path.exists(SHARED_FRAME_DIR):
        try:
            os.makedirs(SHARED_FRAME_DIR, exist_ok=True)
        except Exception as e:
            print(f"创建共享帧目录失败: {str(e)}")
    
    print("\n=== 服务器信息 ===")
    print("请在浏览器中访问 http://localhost:5001 查看监控画面")
    print("调试功能: /test_image 生成测试图像")
    print("\n服务器启动中...\n")
    
    # 启动Flask服务 - 使用端口5001替代被占用的5000
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)