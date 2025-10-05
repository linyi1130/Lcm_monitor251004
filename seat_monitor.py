#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
座位监控系统主程序
基于Raspberry Pi OS和Camera Module 3实现人员行为监控
"""

import cv2
import numpy as np
import pandas as pd
import datetime
import time
from picamera2 import Picamera2
import face_recognition
import os
import json
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

class SeatMonitor:
    def __init__(self, config_file='config.json', debug=False):
        # 加载配置文件
        self.config = self.load_config(config_file)
        
        # 保存调试模式标志
        self.debug_mode = debug
        
        # 初始化日志系统
        self.log_file = None
        self.initialize_logging()
        
        # 初始化摄像头
        print("初始化摄像头...")
        self.camera = Picamera2()
        camera_config = self.camera.create_preview_configuration(
            main={"size": (self.config['camera']['resolution']['width'], 
                          self.config['camera']['resolution']['height'])} 
        )
        self.camera.configure(camera_config)
        self.camera.start()
        if self.config['camera']['rotation'] != 0:
            self.camera.rotation = self.config['camera']['rotation']
        print(f"摄像头已启动，分辨率: {self.config['camera']['resolution']['width']}x{self.config['camera']['resolution']['height']}")
        
        # 设置座位区域 - 直接使用配置文件中的区域
        self.seat_regions = []
        
        # 检查配置文件中是否有座位区域定义
        if 'seats' in self.config and len(self.config['seats']) > 0:
            # 直接使用配置文件中的第一个座位区域
            self.seat_regions.append({
                "id": self.config['seats'][0]['id'],
                "name": self.config['seats'][0]['name'],
                "region": self.config['seats'][0]['region']
            })
            print(f"已加载配置文件中的监控区域，大小: {self.config['camera']['resolution']['width']}x{self.config['camera']['resolution']['height']}")
            self.log_message(f"已加载配置文件中的监控区域，大小: {self.config['camera']['resolution']['width']}x{self.config['camera']['resolution']['height']}", "INFO")
        else:
            # 如果没有定义，使用默认的全屏区域
            default_region = [
                [0, 0],
                [self.config['camera']['resolution']['width'], 0],
                [self.config['camera']['resolution']['width'], self.config['camera']['resolution']['height']],
                [0, self.config['camera']['resolution']['height']]
            ]
            self.seat_regions.append({
                "id": 1,
                "name": "默认监控区域",
                "region": default_region
            })
            print("未在配置文件中找到区域定义，使用默认的全屏监控区域")
            self.log_message("未在配置文件中找到区域定义，使用默认的全屏监控区域", "INFO")
        
        # 人员状态跟踪
        self.occupancy_status = {}
        # 状态滤波计数器，用于记录连续检测到的离开帧数量
        self.leave_counters = {}
        self.initialize_occupancy_status()
        
        # 数据存储
        self.records = []
        self.face_encodings = []
        self.face_names = []
        self.data_dir = self.config['data']['data_directory']
        self.reports_dir = self.config['data']['reports_directory']
        self.known_faces_dir = self.config['data']['known_faces_directory']
        self.save_interval = self.config['data']['save_interval']
        self.detection_interval = self.config['detection']['detection_interval']
        
        # 创建必要的目录
        self.create_directories()
        
        # 加载已知人脸（如果有）
        self.load_known_faces()
        
        # 系统状态
        self.running = True
        self.last_report_generation = datetime.datetime.now().date()
        self.last_save_time = datetime.datetime.now()
        
        # 初始化背景减除器，用于改进人员检测
        self.initialize_background_subtractor()
        
        print("座位监控系统已初始化 - 简化版")
        if self.debug_mode:
            self.log_message("座位监控系统已初始化 - 简化版，使用全屏监控区域", "INFO")
    
    def load_config(self, config_file):
        """加载配置文件，修改为只返回一个座位的配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保只保留第一个座位的配置
                if len(config.get('seats', [])) > 0:
                    config['seats'] = [config['seats'][0]]
                return config
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            # 返回默认配置（只有一个座位）
            return {
                "camera": {
                    "resolution": {"width": 1280, "height": 720},
                    "framerate": 10,
                    "rotation": 0
                },
                "detection": {
                    "motion_threshold": 10000,
                    "detection_interval": 0.1
                },
                "seats": [
                    {"id": 1, "name": "监控区域", "region": [[100, 150], [300, 150], [300, 350], [100, 350]]}
                ],
                "data": {
                    "save_interval": 60,
                    "reports_directory": "reports",
                    "data_directory": "data",
                    "known_faces_directory": "known_faces"
                }
            }
    
    def create_directories(self):
        """创建必要的目录结构"""
        directories = [self.data_dir, self.reports_dir, self.known_faces_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def initialize_occupancy_status(self):
        """初始化所有座位的占用状态"""
        for seat in self.seat_regions:
            self.occupancy_status[seat['id']] = {
                'occupied': False,
                'entry_time': None,
                'exit_time': None,
                'duration': 0,
                'person_id': None,
                'face_encoding': None
            }
            # 初始化离开计数器
            self.leave_counters[seat['id']] = 0
            print(f"初始化座位{seat['id']}状态: 空闲")  # 调试信息
    
    def load_known_faces(self):
        """简化版：不需要加载已知人脸数据"""
        print("使用简化版检测模式，不加载已知人脸数据")
        pass
        
    def initialize_background_subtractor(self):
        """初始化背景减除器，用于简化版的前景检测"""
        try:
            # 从配置文件读取参数
            static_detection_enabled = self.config['detection'].get('static_detection_enabled', False)
            
            # 记录静态检测状态
            if static_detection_enabled:
                self.log_message("警告：配置文件中静态检测已启用，但当前为简化版，静态检测功能将被忽略", "WARNING")
            else:
                self.log_message("静态检测已禁用，使用简化的前景检测模式", "INFO")
            
            # 获取配置参数
            history = self.config['detection'].get('back_sub_history', 300)
            var_threshold = self.config['detection'].get('back_sub_var_threshold', 10)
            
            # 创建背景减除器，关闭阴影检测以简化处理
            self.back_sub = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=var_threshold,
                detectShadows=False
            )
            
            # 设置学习率，使用较高的学习率以加快背景适应
            self.bg_learning_rate = 0.01  # 适中的学习率，平衡敏感性和稳定性
            
            print(f"背景减除器初始化成功（简化版）: 历史帧={history}, 方差阈值={var_threshold}, 学习率={self.bg_learning_rate}")
            self.log_message(f"背景减除器初始化成功: 历史帧={history}, 方差阈值={var_threshold}, 学习率={self.bg_learning_rate}")
        except Exception as e:
            error_msg = f"初始化背景减除器失败: {str(e)}"
            print(error_msg)
            self.log_message(error_msg)
            self.back_sub = None
            
    def initialize_logging(self):
        """初始化日志系统"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(log_dir, f"seat_monitor_{current_time}.log")
            print(f"日志文件已创建: {self.log_file}")
            
            # 写入日志头部
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"===== 座位监控系统日志 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        except Exception as e:
            print(f"初始化日志系统失败: {str(e)}")
            self.log_file = None
            
    def log_message(self, message, level="INFO"):
        """写入日志消息，支持不同日志级别"""
        if self.log_file:
            try:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                log_entry = f"[{timestamp}] [{level}] {message}\n"
                
                # 只有在DEBUG模式下才输出DEBUG级别的日志到控制台
                if level == "DEBUG":
                    if self.debug_mode:
                        print(log_entry.strip())
                else:
                    # 对于INFO、WARNING、ERROR等重要级别，始终输出到控制台
                    if level in ["INFO", "WARNING", "ERROR"]:
                        print(log_entry.strip())
                
                # 所有日志都写入文件
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except Exception as e:
                # 确保错误信息始终显示在控制台
                print(f"写入日志失败: {str(e)}")
        
    def initialize_monitor_region(self):
        """Interactive monitor region initialization, user selects four points with mouse"""
        # Create window
        window_name = "Monitor Region Selection"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.config['camera']['resolution']['width'], 
                         self.config['camera']['resolution']['height'])
        
        # Store clicked points
        points = []
        drawing = False
        temp_point = None
        
        # Mouse callback function
        def mouse_callback(event, x, y, flags, param):
            nonlocal points, drawing, temp_point
            
            if event == cv2.EVENT_LBUTTONDOWN:
                if len(points) < 4:
                    points.append((x, y))
                    print(f"Selected point {len(points)}: ({x}, {y})")
                    if len(points) == 4:
                        print("Four points selected, monitor region defined")
            elif event == cv2.EVENT_MOUSEMOVE:
                temp_point = (x, y)
        
        # Set mouse callback
        cv2.setMouseCallback(window_name, mouse_callback)
        
        # Display camera frame and wait for user to select points
        instructions_shown = False
        while len(points) < 4:
            # Get current frame
            frame = self.camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Display selected points
            for i, (x, y) in enumerate(points):
                cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"{i+1}", (x+10, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # When displaying frame for the first time, show instructions
            if not instructions_shown:
                print("Instructions:")
                print("1. Click four points in the camera view to define the monitor region")
                print("2. Click in clockwise or counter-clockwise order")
                print("3. Press any key to continue after selecting four points")
                instructions_shown = True
            
            # 如果已有点，绘制连线
            if len(points) > 1:
                for i in range(len(points) - 1):
                    cv2.line(frame, points[i], points[i+1], (0, 255, 0), 2)
                # 如果已有四个点，绘制最后一条连线
                if len(points) == 4:
                    cv2.line(frame, points[3], points[0], (0, 255, 0), 2)
            
            # 显示操作提示
            cv2.putText(frame, "点击四个点定义监控区域", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f"已选择点数量: {len(points)}/4", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 显示画面
            cv2.imshow(window_name, frame)
            
            # 按ESC键取消当前选择的所有点
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC键
                points = []
                print("已取消所有选择的点，请重新选择")
            elif key != 255 and len(points) == 4:
                break
        
        # 关闭窗口
        cv2.destroyWindow(window_name)
        
        return points
        
    def save_config(self, config_file):
        """保存配置到文件"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"配置已保存到 {config_file}")
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
    
    def detect_person_in_region(self, frame, region, seat_id=None):
        """检测指定区域内是否有人"""
        if frame is None or region is None:
            self.log_message("检测失败：无效的帧或区域", "ERROR")
            return False, None
        
        # 创建区域掩码
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        pts = np.array(region, np.int32)
        cv2.fillPoly(mask, [pts], 255)
        
        # 计算区域的最小包围矩形以提取ROI
        x = min([p[0] for p in region])
        y = min([p[1] for p in region])
        w = max([p[0] for p in region]) - x
        h = max([p[1] for p in region]) - y
        
        # 检查ROI是否有效
        if w <= 0 or h <= 0:
            self.log_message("无效的ROI尺寸", "ERROR")
            return False, None
        
        # 确保ROI不超出帧边界
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        
        # 提取ROI
        roi = frame[y:y+h, x:x+w].copy()
        if roi is None or roi.size == 0:
            self.log_message("无法提取有效的ROI", "ERROR")
            return False, None
        
        # 应用区域掩码
        roi_mask = mask[y:y+h, x:x+w]
        if roi_mask.shape[:2] != roi.shape[:2]:
            roi_mask = cv2.resize(roi_mask, (roi.shape[1], roi.shape[0]))
        
        # 初始化背景减法器（如果尚未初始化）
        if not hasattr(self, 'back_sub') or self.back_sub is None:
            self.back_sub = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=10, detectShadows=False)
            self.log_message("背景减法器已初始化", "DEBUG")
        
        # 获取当前学习率（默认或从配置读取）
        learning_rate = getattr(self, 'bg_learning_rate', 0.01)
        
        # 应用背景减法获取前景掩码
        fg_mask = self.back_sub.apply(roi, learningRate=learning_rate)
        
        # 应用区域掩码到前景掩码
        fg_mask = cv2.bitwise_and(fg_mask, roi_mask)
        
        # 阈值化处理，去除阴影
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 计算前景面积
        fg_area = cv2.countNonZero(fg_mask)
        
        # 计算区域总面积
        roi_area = w * h
        
        # 计算前景面积占比
        fg_ratio = fg_area / roi_area if roi_area > 0 else 0
        
        # 简单的运动检测逻辑：如果前景面积超过阈值，则认为有人
        # 由于使用整个画面，我们使用相对较小的阈值（1%）
        motion_threshold = 0.01  # 面积占比阈值
        
        # 判断是否检测到人
        person_detected = fg_ratio > motion_threshold
        
        # 日志记录
        self.log_message(f"区域检测 - 前景面积: {fg_area} ({fg_ratio*100:.2f}%), 阈值: {motion_threshold*100:.2f}%, 检测结果: {'有人' if person_detected else '无人'}", "DEBUG")
        
        # 对于简化版本，不进行人脸识别或跟踪
        person_id = None
        
        return person_detected, person_id
    
    def update_occupancy_status(self, frame):
        """更新座位占用状态"""
        # 初始化离开计数器（如果不存在）
        if not hasattr(self, 'leave_counters'):
            self.leave_counters = {}
        
        # 为每个座位更新离开计数器
        for seat in self.seat_regions:
            seat_id = seat['id']
            if seat_id not in self.leave_counters:
                self.leave_counters[seat_id] = 0
        
        # 只在DEBUG模式下记录此信息
        if self.debug_mode:
            self.log_message("开始更新座位占用状态...", "DEBUG")
        
        # 遍历所有座位区域（保持与draw_overlay方法一致的列表访问方式）
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            
            # 获取当前状态
            current_occupied = self.occupancy_status.get(seat_id, {}).get('occupied', False)
            
            # 只在DEBUG模式下记录此信息
            if self.debug_mode:
                self.log_message(f"座位{seat_id} - 当前状态: {'已占用' if current_occupied else '空闲'}", "DEBUG")
            
            # 检测区域内是否有人
            person_detected, person_id = self.detect_person_in_region(frame, region, seat_id)
            
            # 初始化座位状态（如果不存在）
            if seat_id not in self.occupancy_status:
                self.occupancy_status[seat_id] = {
                    'occupied': False,
                    'person_id': None,
                    'start_time': None,
                    'end_time': None,
                    'duration': 0
                }
            
            # 初始化离开计数器
            if seat_id not in self.leave_counters:
                self.leave_counters[seat_id] = 0
            
            # 处理检测结果
            if person_detected:
                # 重置离开计数器
                self.leave_counters[seat_id] = 0
                
                # 只在DEBUG模式下记录此信息
                if self.debug_mode:
                    self.log_message(f"座位{seat_id} - 检测到人，重置离开计数器", "DEBUG")
                
                # 如果之前是空闲状态，现在检测到人，更新状态
                if not self.occupancy_status[seat_id]['occupied']:
                    # 开始新的占用记录
                    self.occupancy_status[seat_id].update({
                        'occupied': True,
                        'person_id': person_id,
                        'start_time': datetime.datetime.now()
                    })
                    # 状态变更始终记录
                    self.log_message(f"座位{seat_id} - 状态变更: 空闲 -> 已占用", "INFO")
                    
                    # 高学习率模式，帮助快速学习新的背景
                    if hasattr(self, 'back_sub') and self.back_sub is not None:
                        self.bg_learning_rate = 0.05  # 临时提高学习率
                        
                        # 只在DEBUG模式下记录此信息
                        if self.debug_mode:
                            self.log_message(f"座位{seat_id} - 临时提高学习率至: {self.bg_learning_rate}", "DEBUG")
            else:
                # 未检测到人，增加离开计数器
                self.leave_counters[seat_id] += 1
                
                # 只在DEBUG模式下记录此信息
                if self.debug_mode:
                    self.log_message(f"座位{seat_id} - 未检测到人，离开计数器: {self.leave_counters[seat_id]}")
                
                # 如果当前是已占用状态，检查是否需要触发离开确认
                if self.occupancy_status[seat_id]['occupied']:
                    # 简化的离开确认逻辑：只要连续未检测到人达到阈值，就确认离开
                    if self.leave_counters[seat_id] >= 3:  # 适中的阈值，平衡误报和响应速度
                        # 记录结束时间和持续时间
                        end_time = datetime.datetime.now()
                        start_time = self.occupancy_status[seat_id]['start_time']
                        duration = (end_time - start_time).total_seconds() if start_time else 0
                        
                        # 更新状态
                        self.occupancy_status[seat_id].update({
                            'occupied': False,
                            'end_time': end_time,
                            'duration': duration
                        })
                        
                        # 状态变更始终记录
                        self.log_message(f"座位{seat_id} - 状态变更: 已占用 -> 空闲, 持续时间: {duration:.2f}秒, 原因: 连续{self.leave_counters[seat_id]}帧未检测到人", "INFO")
                        
                        # 重置离开计数器
                        self.leave_counters[seat_id] = 0
                        
                        # 保存记录
                        self.save_record(seat_id)

        # 保存当前状态
        self.save_current_state()
        
        # 定期保存数据
        if self.save_interval and (datetime.datetime.now() - self.last_save_time).seconds >= self.save_interval:
            self.save_current_state()
            self.last_save_time = datetime.datetime.now()
            # 只在DEBUG模式下记录此信息
            if self.debug_mode:
                self.log_message(f"定期保存数据: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        
        # 生成每日报告
        if self.generate_daily_report(datetime.datetime.now()):
            # 只在DEBUG模式下记录此信息
            if self.debug_mode:
                self.log_message("生成每日报告完成", "INFO")
        
        # 返回当前的占用状态字典
        return self.occupancy_status
    
    def save_current_state(self):
        """定期保存当前状态，防止数据丢失"""
        try:
            current_time = datetime.datetime.now()
            state_filename = os.path.join(self.data_dir, f"current_state_{current_time.strftime('%Y%m%d%H%M%S')}.json")
            
            # 准备保存的数据
            state_data = {
                'timestamp': current_time.isoformat(),
                'occupancy_status': self.occupancy_status,
                'last_report_generation': self.last_report_generation.isoformat()
            }
            
            # 保存状态
            with open(state_filename, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"[{current_time}] 系统状态已保存")
        except Exception as e:
            print(f"保存系统状态时出错: {str(e)}")
    
    def save_record(self, record):
        """保存单条记录到CSV文件"""
        today = datetime.date.today()
        filename = os.path.join(self.data_dir, f"occupancy_records_{today.strftime('%Y%m%d')}.csv")
        
        # 检查文件是否存在
        file_exists = os.path.isfile(filename)
        
        # 创建DataFrame并保存
        df = pd.DataFrame([record])
        df.to_csv(filename, mode='a', header=not file_exists, index=False)
    
    def generate_daily_report(self, date):
        """生成每日监控报告"""
        filename = os.path.join(self.data_dir, f"occupancy_records_{date.strftime('%Y%m%d')}.csv")
        report_filename = os.path.join(self.reports_dir, f"daily_report_{date.strftime('%Y%m%d')}.txt")
        
        if not os.path.isfile(filename):
            print(f"没有找到{date}的数据文件，无法生成报告")
            return
        
        try:
            # 读取数据
            df = pd.read_csv(filename)
            
            # 统计信息
            total_records = len(df)
            unique_persons = df['person_id'].nunique()
            total_duration = df['duration_seconds'].sum() / 3600  # 转换为小时
            
            # 按座位统计
            seat_stats = df.groupby('seat_name').agg({
                'duration_seconds': ['sum', 'count'],
                'person_id': 'nunique'
            }).reset_index()
            
            # 生成报告
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(f"===== 座位监控每日报告 =====\n")
                f.write(f"报告日期: {date.strftime('%Y年%m月%d日')}\n")
                f.write(f"总记录数: {total_records}\n")
                f.write(f"涉及人员: {unique_persons}\n")
                f.write(f"总占用时长: {total_duration:.2f}小时\n\n")
                f.write("各座位统计:\n")
                for _, row in seat_stats.iterrows():
                    seat_name = row['seat_name']
                    duration = row[('duration_seconds', 'sum')] / 3600  # 转换为小时
                    count = row[('duration_seconds', 'count')]
                    persons = row[('person_id', 'nunique')]
                    f.write(f"  {seat_name}: {count}次占用, {persons}人使用, 总时长{duration:.2f}小时\n")
                
            print(f"已生成{date}的每日报告: {report_filename}")
        except Exception as e:
            print(f"生成报告时出错: {str(e)}")
    
    def draw_overlay(self, frame):
        """Draw seat regions and status on video frame"""
        # 创建调试信息区域
        debug_frame = frame.copy()
        
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            status = self.occupancy_status[seat_id]
            
            # Set color based on occupancy status
            color = (0, 0, 255) if status['occupied'] else (0, 255, 0)
            thickness = 2 if status['occupied'] else 1
            
            # Draw region
            cv2.polylines(debug_frame, [np.array(region)], True, color, thickness)
            
            # Display seat name and status (using English to avoid display issues)
            status_text = "Occupied" if status['occupied'] else "Empty"
            text = f"{seat['name']}: {status_text}"
            if status['occupied'] and status['person_id']:
                text += f" ({status['person_id']})"
            
            # Draw text using OpenCV with English
            cv2.putText(debug_frame, text, (region[0][0], region[0][1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 添加离开计数器信息
            counter_text = f"Leave: {self.leave_counters[seat_id]}"
            cv2.putText(debug_frame, counter_text, (region[0][0], region[-1][1] + 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Display current time
        current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(debug_frame, current_time_str, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 显示前景掩码（如果可用）
        if hasattr(self, 'debug_fg_mask') and self.debug_fg_mask is not None:
            # 调整前景掩码大小以适应显示
            mask_h, mask_w = self.debug_fg_mask.shape
            # 创建彩色版本的掩码便于查看
            color_mask = cv2.cvtColor(self.debug_fg_mask, cv2.COLOR_GRAY2BGR)
            # 在主画面上叠加前景掩码
            overlay_h, overlay_w = min(200, mask_h), min(200, mask_w)
            small_mask = cv2.resize(color_mask, (overlay_w, overlay_h))
            # 将掩码叠加在右上角
            if overlay_h < debug_frame.shape[0] and overlay_w < debug_frame.shape[1]:
                debug_frame[10:10+overlay_h, debug_frame.shape[1]-overlay_w-10:debug_frame.shape[1]-10] = small_mask
                cv2.putText(debug_frame, "FG Mask", (debug_frame.shape[1]-overlay_w-10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return debug_frame
    
    def run(self):
        """运行监控系统"""
        try:
            print("座位监控系统已启动，按'q'键退出")
            print("当前模式：简化版 - 持续显示摄像头内容，检测是否有人")
            self.log_message("座位监控系统已启动，按'q'键退出", "INFO")
            
            # 初始化显示窗口
            window_name = '座位监控系统'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, self.config['camera']['resolution']['width'], 
                             self.config['camera']['resolution']['height'])
            
            # 初始化帧时间戳，用于动态调整检测频率
            last_frame_time = datetime.datetime.now()
            
            while self.running:
                try:
                    # 从摄像头获取帧
                    frame = self.camera.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # 转换颜色空间
                    
                    # 检查帧是否获取成功
                    if frame is None or frame.size == 0:
                        self.log_message("警告：未能获取摄像头图像帧", "WARNING")
                        time.sleep(1)  # 暂停1秒后重试
                        continue
                    
                    # 更新占用状态
                    self.update_occupancy_status(frame)
                    
                    # 绘制叠加层
                    display_frame = self.draw_overlay(frame)
                    
                    # 显示结果
                    cv2.imshow(window_name, display_frame)
                    
                    # 检查退出按键
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.running = False
                        
                    # 动态调整延迟时间，确保检测频率稳定
                    current_time = datetime.datetime.now()
                    elapsed_time = (current_time - last_frame_time).total_seconds()
                    sleep_time = max(0, self.detection_interval - elapsed_time)
                    time.sleep(sleep_time)
                    last_frame_time = current_time
                except Exception as e:
                    error_msg = f"处理帧时出错: {str(e)}"
                    print(error_msg)
                    self.log_message(error_msg, "ERROR")
                    time.sleep(0.5)  # 出错时稍作暂停再继续
        
        except KeyboardInterrupt:
            print("系统被用户中断")
            self.log_message("系统被用户中断", "INFO")
        finally:
            # 清理资源
            try:
                self.camera.stop()
                cv2.destroyAllWindows()
                print("摄像头已关闭，窗口已销毁")
                self.log_message("摄像头已关闭，窗口已销毁", "INFO")
            except Exception as e:
                print(f"清理资源时出错: {str(e)}")
                self.log_message(f"清理资源时出错: {str(e)}", "ERROR")
            
            try:
                # 最后保存一次当前状态
                self.save_current_state()
                self.log_message("最后保存当前状态", "INFO")
            except Exception as e:
                print(f"保存状态时出错: {str(e)}")
                self.log_message(f"保存状态时出错: {str(e)}", "ERROR")
            
            try:
                # 生成当天的报告
                today = datetime.date.today()
                self.generate_daily_report(today)
            except Exception as e:
                print(f"生成报告时出错: {str(e)}")
            
            print("座位监控系统已关闭")

def main(debug=False):
    """主函数，程序的入口点"""
    try:
        # 创建座位监控实例，传递debug参数
        monitor = SeatMonitor(debug=debug)
        # 运行监控系统
        monitor.run()
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    # 调用主函数并设置返回码
    exit_code = main()
    # 退出程序，返回相应的退出码
    import sys
    sys.exit(exit_code)