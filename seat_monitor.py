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
        self.camera = Picamera2()
        camera_config = self.camera.create_preview_configuration(
            main={"size": (self.config['camera']['resolution']['width'], 
                          self.config['camera']['resolution']['height'])} 
        )
        self.camera.configure(camera_config)
        self.camera.start()
        if self.config['camera']['rotation'] != 0:
            self.camera.rotation = self.config['camera']['rotation']
        
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
            self.log_message(f"加载配置文件失败: {str(e)}", "ERROR")
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
    
    def load_known_faces(self):
        """简化版：不需要加载已知人脸数据"""
        self.log_message("使用简化版检测模式，不加载已知人脸数据", "INFO")
        pass
        
    def initialize_background_subtractor(self):
        """初始化背景减除器，用于简化版的前景检测"""
        try:
            # 记录静态检测状态
            self.log_message("静态检测已禁用，使用优化的前景检测模式", "INFO")
            
            # 获取配置参数，但使用更稳定的默认值
            history = 150  # 减少历史帧数，加快对真实变化的响应
            var_threshold = 20  # 提高方差阈值，减少噪声影响
            
            # 创建背景减除器，关闭阴影检测
            self.back_sub = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=var_threshold,
                detectShadows=False
            )
            
            # 设置学习率，使用较低的学习率以减少误判
            self.bg_learning_rate = 0.001  # 降低学习率，使背景模型更稳定，减少静止人员被误判为背景
            
            self.log_message(f"背景减除器初始化成功: 历史帧={history}, 方差阈值={var_threshold}, 学习率={self.bg_learning_rate}", "INFO")
        except Exception as e:
            error_msg = f"初始化背景减除器失败: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.back_sub = None
    
    def initialize_logging(self):
        """初始化日志系统"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(log_dir, f"seat_monitor_{current_time}.log")
            
            # 写入日志头部
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"===== 座位监控系统日志 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        except Exception as e:
            self.log_message(f"初始化日志系统失败: {str(e)}", "ERROR")
            self.log_file = None
            
    def log_message(self, message, level="INFO"):
        """写入日志消息，支持不同日志级别"""
        if self.log_file:
            try:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                log_entry = f"[{timestamp}] [{level}] {message}\n"
                
                # 只有在状态变更时才输出到控制台
                # 检查消息是否包含状态变更相关内容
                if "状态变更" in message:
                    # 直接打印简单的状态变更信息，不包含时间戳和日志级别
                    # 提取状态变更的核心信息
                    if "空闲 -> 已占用" in message:
                        print(f"{message}")
                    elif "已占用 -> 空闲" in message:
                        print(f"{message}")
                
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
                    if len(points) == 4:
                        pass  # 静默选择
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
            
            # 静默模式下不显示指令
            
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
            self.log_message(f"配置已保存到 {config_file}", "INFO")
        except Exception as e:
            self.log_message(f"保存配置文件失败: {str(e)}", "ERROR")
    
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
            
            self.log_message(f"系统状态已保存", "INFO")
        except Exception as e:
            self.log_message(f"保存系统状态时出错: {str(e)}", "ERROR")
    
    def generate_daily_report(self, date):
        """生成每日监控报告"""
        filename = os.path.join(self.data_dir, f"occupancy_records_{date.strftime('%Y%m%d')}.csv")
        report_filename = os.path.join(self.reports_dir, f"daily_report_{date.strftime('%Y%m%d')}.txt")
        
        if not os.path.isfile(filename):
            self.log_message(f"没有找到{date}的数据文件，无法生成报告", "INFO")
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
                
            self.log_message(f"已生成{date}的每日报告: {report_filename}", "INFO")
        except Exception as e:
            self.log_message(f"生成报告时出错: {str(e)}", "ERROR")
    
    def update_occupancy_status(self, frame):
        """更新座位的占用状态，优化版：增强稳定性，减少误判"""
        # 获取当前时间
        current_time = datetime.datetime.now()
        
        # 初始化状态追踪器
        if not hasattr(self, 'occupancy_history'):
            self.occupancy_history = {s['id']: [] for s in self.seat_regions}
        
        # 对每个座位区域进行人员检测
        for seat in self.seat_regions:
            seat_id = seat['id']
            seat_name = seat['name']
            region = seat['region']
            
            # 检测区域内是否有人
            is_occupied = self.detect_person_in_region(frame, region)
            
            # 获取当前座位状态
            current_status = self.occupancy_status[seat_id]
            
            # 维护最近的检测历史
            self.occupancy_history[seat_id].append(is_occupied)
            # 只保留最近15个状态（约1.5秒）
            self.occupancy_history[seat_id] = self.occupancy_history[seat_id][-15:]
            
            # 使用历史状态来确定最终的占用状态，而不是单一帧的检测结果
            # 如果历史中有80%的帧检测到有人，则认为当前是占用状态
            history_occupied_ratio = sum(self.occupancy_history[seat_id]) / len(self.occupancy_history[seat_id])
            final_occupied = history_occupied_ratio > 0.8  # 增加阈值以提高稳定性
            
            # 增加进入计数器
            if not hasattr(self, 'enter_counters'):
                self.enter_counters = {s['id']: 0 for s in self.seat_regions}
            
            # 如果综合判断为有人
            if final_occupied:
                self.enter_counters[seat_id] += 1
                self.leave_counters[seat_id] = 0
                
                # 连续5帧确认有人才更新状态（约0.5秒）
                if not current_status['occupied'] and self.enter_counters[seat_id] >= 5:
                    current_status['occupied'] = True
                    current_status['entry_time'] = current_time
                    current_status['person_id'] = f"person_{current_time.strftime('%Y%m%d%H%M%S')}_{seat_id}"
                    
                    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    self.log_message(f"[{timestamp_str}] {seat_name}状态变更: 空闲 -> 已占用", "INFO")
                    
                    self.records.append({
                        'timestamp': current_time.isoformat(),
                        'seat_id': seat_id,
                        'seat_name': seat_name,
                        'person_id': current_status['person_id'],
                        'action': 'enter'
                    })
            else:
                # 如果综合判断为无人
                self.leave_counters[seat_id] += 1
                self.enter_counters[seat_id] = 0
                
                # 增加阈值到20帧（约2秒）才确认离开，大幅减少误判
                if current_status['occupied'] and self.leave_counters[seat_id] >= 20:
                    current_status['occupied'] = False
                    current_status['exit_time'] = current_time
                    
                    if current_status['entry_time']:
                        duration = (current_time - current_status['entry_time']).total_seconds()
                        current_status['duration'] = duration
                        
                        for record in reversed(self.records):
                            if record['person_id'] == current_status['person_id'] and record['action'] == 'enter':
                                record['exit_time'] = current_time.isoformat()
                                record['duration_seconds'] = duration
                                break
                        
                        # 提高最小持续时间阈值到5秒
                        if duration >= 5:
                            timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                            self.log_message(f"[{timestamp_str}] {seat_name}状态变更: 已占用 -> 空闲, 持续时长: {int(duration)}秒", "INFO")
                        else:
                            if self.debug_mode:
                                self.log_message(f"[{timestamp_str}] {seat_name}短暂状态修正: 忽略短时间占用({int(duration)}秒)", "DEBUG")
                            if self.records and self.records[-1]['action'] == 'enter' and self.records[-1]['person_id'] == current_status['person_id']:
                                self.records.pop()
        
        # 定期保存数据
        if (current_time - self.last_save_time).total_seconds() >= self.save_interval:
            self.save_current_state()
            self.last_save_time = current_time
            
        # 定期生成报告
        if current_time.date() > self.last_report_generation:
            try:
                yesterday = current_time.date() - datetime.timedelta(days=1)
                self.generate_daily_report(yesterday)
                self.last_report_generation = current_time.date()
            except Exception as e:
                self.log_message(f"生成报告时出错: {str(e)}", "ERROR")
    
    def detect_person_in_region(self, frame, region):
        """检测指定区域内是否有人"""
        # 如果背景减除器未初始化，返回默认值
        if self.back_sub is None:
            return False
        
        try:
            # 创建掩码，只处理监控区域内的部分
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            region_points = np.array(region, dtype=np.int32)
            cv2.fillPoly(mask, [region_points], 255)
            
            # 应用掩码到帧
            masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
            
            # 使用背景减除器获取前景，降低学习率以减少误判
            fg_mask = self.back_sub.apply(masked_frame, learningRate=self.bg_learning_rate)
            
            # 对前景掩码进行形态学操作，使用更大的核来更好地去除噪声
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))  # 增大核大小以更好地去除噪声
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)  # 先闭操作填充小洞
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)   # 再开操作去除小物体
            
            # 计算前景区域的面积
            foreground_area = cv2.countNonZero(fg_mask)
            
            # 从配置获取运动阈值，但增加一个基于区域大小的动态调整因子
            base_threshold = self.config['detection']['motion_threshold']
            # 计算区域面积，根据区域大小动态调整阈值
            region_area = cv2.contourArea(region_points)
            # 阈值调整因子，确保小区域有较低的阈值，大区域有较高的阈值
            adjusted_threshold = base_threshold * (region_area / (frame.shape[0] * frame.shape[1]))
            
            # 确保阈值不会过低或过高
            adjusted_threshold = max(1000, min(10000, adjusted_threshold))
            
            is_occupied = foreground_area > adjusted_threshold
            
            if self.debug_mode:
                self.log_message(f"区域检测: 前景面积={foreground_area}, 阈值={adjusted_threshold}, 结果={is_occupied}", "DEBUG")
            
            return is_occupied
        except Exception as e:
            self.log_message(f"区域检测出错: {str(e)}", "ERROR")
            return False
    
    def draw_overlay(self, frame):
        """在帧上绘制叠加层，显示座位状态信息，支持中文显示"""
        # 创建帧的副本，避免修改原始帧
        display_frame = frame.copy()
        
        # 将OpenCV的BGR图像转换为PIL的RGB图像以支持中文显示
        try:
            # 创建PIL图像对象
            pil_img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            
            # 尝试加载中文字体，支持多种可能的字体路径和名称
            font_path_candidates = [
                # macOS 常用中文字体
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/SFNSMono.ttf',
                '/System/Library/Fonts/STHeiti Medium.ttc',
                '/System/Library/Fonts/Songti.ttc',
                # Linux 常用中文字体
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                # Windows 常用中文字体
                'C:/Windows/Fonts/simhei.ttf',
                'C:/Windows/Fonts/simsun.ttc',
                'C:/Windows/Fonts/msyh.ttc',
                # 通用字体名称（系统会自动查找）
                'SimHei', 'WenQuanYi Micro Hei', 'Heiti TC', 'Microsoft YaHei',
                'Arial Unicode MS', 'Noto Sans CJK', 'Noto Serif CJK'
            ]
            
            # 尝试加载字体，如果找不到则使用默认字体
            font = None
            font_large = None
            loaded_font_path = None
            
            for font_path in font_path_candidates:
                try:
                    # 尝试作为字体路径加载
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, 16)
                        font_large = ImageFont.truetype(font_path, 24)
                        loaded_font_path = font_path
                        break
                except Exception:
                    try:
                        # 尝试作为字体名称加载
                        font = ImageFont.truetype(font_path, 16)
                        font_large = ImageFont.truetype(font_path, 24)
                        loaded_font_path = font_path
                        break
                    except Exception:
                        continue
            
            # 记录字体加载状态
            if self.debug_mode:
                if font:
                    self.log_message(f"成功加载字体: {loaded_font_path}", "INFO")
                else:
                    self.log_message("未能加载中文字体，将使用默认字体（可能显示乱码）", "WARNING")
                    # 尝试使用PIL默认字体作为最后的备选
                    try:
                        font = ImageFont.load_default()
                        font_large = ImageFont.load_default()
                        self.log_message("已加载PIL默认字体", "INFO")
                    except Exception:
                        self.log_message("无法加载任何字体", "ERROR")
            
            # 为每个座位区域绘制边界和状态信息
            for seat in self.seat_regions:
                seat_id = seat['id']
                seat_name = seat['name']
                region = seat['region']
                
                # 获取座位当前状态
                status = self.occupancy_status[seat_id]
                is_occupied = status['occupied']
                
                # 根据座位状态选择颜色 (BGR -> RGB for PIL)
                color = (255, 0, 0) if is_occupied else (0, 255, 0)  # 占用:红色, 空闲:绿色
                
                try:
                    # 获取当前时间用于标记
                    seat_time = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    # 在区域左上角显示座位名称、状态和时间
                    region_points = np.array(region, dtype=np.int32)
                    text_position = tuple(region_points[0])
                    text = f"{seat_name}: {'占用' if is_occupied else '空闲'} [{seat_time}]"
                    
                    # 使用PIL绘制中文文本和区域边界
                    if font:
                        # 绘制区域边界（使用PIL绘制多边形）
                        draw.polygon(tuple(map(tuple, region_points)), outline=color, width=2)
                        # 绘制文本
                        draw.text((text_position[0], text_position[1] - 20), text, font=font, fill=color)
                        
                        # 如果座位被占用，显示占用时长和进入时间
                        if is_occupied and 'entry_time' in status:
                            duration = (datetime.datetime.now() - status['entry_time']).total_seconds()
                            minutes, seconds = divmod(int(duration), 60)
                            entry_time_str = status['entry_time'].strftime("%H:%M:%S")
                            duration_text = f"时长: {minutes}m{seconds}s | 进入: {entry_time_str}"
                            duration_position = (text_position[0], text_position[1])
                            draw.text(duration_position, duration_text, font=font, fill=color)
                    else:
                        # 如果无法加载字体，回退到OpenCV（可能仍显示乱码）
                        cv2.polylines(display_frame, [region_points], True, (color[2], color[1], color[0]), 2)
                        cv2.putText(display_frame, text, text_position, 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (color[2], color[1], color[0]), 2)
                        
                        if is_occupied and 'entry_time' in status:
                            duration = (datetime.datetime.now() - status['entry_time']).total_seconds()
                            minutes, seconds = divmod(int(duration), 60)
                            entry_time_str = status['entry_time'].strftime("%H:%M:%S")
                            duration_text = f"时长: {minutes}m{seconds}s | 进入: {entry_time_str}"
                            duration_position = (text_position[0], text_position[1])
                            cv2.putText(display_frame, duration_text, duration_position, 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (color[2], color[1], color[0]), 1)
                    
                except Exception as e:
                    if self.debug_mode:
                        self.log_message(f"绘制座位{seat_name}时出错: {str(e)}", "ERROR")
            
            # 获取当前时间并格式化
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 在左上角显示当前时间
            time_text = f"时间: {current_time}"
            status_text = f"[{current_time}] 系统状态: 运行中 | FPS: {self.config['camera']['framerate']}"
            
            # 使用PIL绘制中文文本
            if font:
                # 绘制时间和状态文本
                draw.text((10, 10), time_text, font=font_large, fill=(255, 255, 255))
                draw.text((10, 40), status_text, font=font_large, fill=(255, 255, 255))
                
                # 在所有绘制操作完成后，将PIL图像转回OpenCV格式
                display_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            else:
                # 回退到OpenCV
                cv2.putText(display_frame, time_text, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, status_text, (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
        except Exception as e:
            if self.debug_mode:
                self.log_message(f"绘制叠加层时出错: {str(e)}", "ERROR")
        
        return display_frame
    
    def run(self):
        """运行监控系统"""
        try:
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
                    self.log_message(error_msg, "ERROR")
                    time.sleep(0.5)  # 出错时稍作暂停再继续
        
        except KeyboardInterrupt:
            self.log_message("系统被用户中断", "INFO")
        finally:
            # 清理资源
            try:
                self.camera.stop()
                cv2.destroyAllWindows()
                self.log_message("摄像头已关闭，窗口已销毁", "INFO")
            except Exception as e:
                self.log_message(f"清理资源时出错: {str(e)}", "ERROR")
            
            try:
                # 最后保存一次当前状态
                self.save_current_state()
                self.log_message("最后保存当前状态", "INFO")
            except Exception as e:
                self.log_message(f"保存状态时出错: {str(e)}", "ERROR")
            
            try:
                # 生成当天的报告
                today = datetime.date.today()
                self.generate_daily_report(today)
            except Exception as e:
                self.log_message(f"生成报告时出错: {str(e)}", "ERROR")
            
            self.log_message("座位监控系统已关闭", "INFO")

def main(debug=False):
    """主函数，程序的入口点"""
    try:
        # 创建座位监控实例，传递debug参数
        monitor = SeatMonitor(debug=debug)
        # 运行监控系统
        monitor.run()
    except Exception as e:
        # 使用普通print语句，因为self变量在这里不可用
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