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
    def __init__(self, config_file='config.json'):
        # 加载配置文件
        self.config = self.load_config(config_file)
        
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
        
        # 设置座位区域
        self.seat_regions = []
        
        # 默认直接进入交互式区域选择模式
        print("Starting interactive monitor region selection...")
        region = self.initialize_monitor_region()
        self.seat_regions.append({
            "id": 1,
            "name": "Monitor Area",
            "region": region
        })
        
        # 保存新的区域配置
        self.config['seats'] = [{"id": 1, "name": "Monitor Area", "region": region}]
        self.save_config(config_file)
        
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
        
        print("座位监控系统已初始化")
        
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
    
    def load_known_faces(self):
        """简化版：不需要加载已知人脸数据"""
        print("使用简化版检测模式，不加载已知人脸数据")
        pass
        
    def initialize_background_subtractor(self):
        """初始化背景减除器，平衡静态和动态人体检测"""
        try:
            # 获取配置参数 - 优化整体检测灵敏度
            history = self.config['detection'].get('back_sub_history', 300)  # 适中的历史记录
            var_threshold = self.config['detection'].get('back_sub_var_threshold', 10)  # 降低阈值，提高敏感度
            var_threshold_gen = self.config['detection'].get('back_sub_var_threshold_gen', 9)
            
            # 创建背景减除器
            self.back_sub = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=var_threshold,
                detectShadows=True
            )
            
            # 调整背景减除器参数
            if hasattr(self.back_sub, 'setVarThresholdGen'):
                self.back_sub.setVarThresholdGen(var_threshold_gen)
            
            # 设置阴影阈值，改善阴影处理
            if hasattr(self.back_sub, 'setShadowThreshold'):
                self.back_sub.setShadowThreshold(0.7)  # 增加阴影阈值，更好地识别阴影中的人体
            
            # 配置学习率，提高背景更新速度以适应人员移动
            self.bg_learning_rate = self.config['detection'].get('bg_learning_rate', 0.01)  # 提高学习率，使背景模型能够快速适应场景变化
            
            print("背景减除器初始化成功（已优化人体检测灵敏度）")
        except Exception as e:
            print(f"初始化背景减除器失败: {str(e)}")
            self.back_sub = None
        
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
    
    def detect_person_in_region(self, frame, region):
        """检测指定区域内是否有人，优化算法以适应静止人体、背影和上半身为主的情况"""
        # 提取区域ROI
        x = min([p[0] for p in region])
        y = min([p[1] for p in region])
        w = max([p[0] for p in region]) - x
        h = max([p[1] for p in region]) - y
        roi = frame[y:y+h, x:x+w].copy()
        
        # 获取配置参数
        min_area = self.config['detection']['motion_threshold']
        static_detection_enabled = self.config['detection'].get('static_detection_enabled', True)
        
        # 检查是否启用了背景减除
        if hasattr(self, 'back_sub') and self.back_sub is not None:
            # 使用背景减除获取前景掩码，控制学习率以减慢背景更新
            fg_mask = self.back_sub.apply(roi, learningRate=self.bg_learning_rate)
            
            # 去除阴影（通常值为127）
            _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            
            # 形态学操作，填充小洞和消除小物体
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
            
            # 查找轮廓
            motion_contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            motion_contours = []
        
        # 静态特征检测（不依赖运动）
        static_contours = []
        if static_detection_enabled:
            # 转换为灰度图进行静态轮廓检测
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)  # 减小高斯核，保留更多细节
            
            # 自适应阈值，更好地适应光线变化
            thresh = cv2.adaptiveThreshold(blurred, 255, 
                                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 11, 2)  # 调整块大小和常数，提高敏感度
            
            # 形态学操作，进一步减少噪音
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))  # 减小闭合核，保留更多小细节
            kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open)
            
            # 查找轮廓
            static_contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 合并运动和静态轮廓检测结果
        all_contours = []
        if motion_contours and len(motion_contours) > 0:
            all_contours.extend(motion_contours)
        if static_contours and len(static_contours) > 0:
            all_contours.extend(static_contours)
        
        # 检查是否有足够大的轮廓（可能是人体）
        person_detected = False
        
        # 从配置中读取宽高比范围，适应不同体型和姿态
        aspect_ratio_min = self.config['detection'].get('contour_aspect_ratio_min', 0.2)
        aspect_ratio_max = self.config['detection'].get('contour_aspect_ratio_max', 2.0)
        
        # 针对上半身的特殊配置
        upper_body_min_height_ratio = self.config['detection'].get('upper_body_min_height_ratio', 0.3)
        upper_body_center_offset = self.config['detection'].get('upper_body_center_offset', 0.2)
        
        # 静态人体检测的额外参数
        static_person_min_area_ratio = self.config['detection'].get('static_person_min_area_ratio', 0.05)  # ROI面积的最小比例
        
        # 计算ROI面积用于静态人体检测
        roi_area = w * h
        min_static_area = max(min_area, roi_area * static_person_min_area_ratio)
        
        # 改进的轮廓分析：考虑多个条件，特别优化上半身和静止人体检测
        for contour in all_contours:
            area = cv2.contourArea(contour)
            
            # 面积条件：大幅降低阈值，提高检测灵敏度
            if area > min_area * 0.3 or (static_detection_enabled and area > min_static_area * 0.3):
                # 计算轮廓的边界框
                x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(contour)
                
                # 计算宽高比（上半身通常更宽更矮）
                aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else 0
                
                # 计算轮廓的紧凑度（圆形度）
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    compactness = 4 * math.pi * area / (perimeter * perimeter)
                else:
                    compactness = 0
                
                # 计算轮廓的中心位置
                contour_center_y = y_rect + h_rect / 2
                
                # 上半身检测条件 - 大幅放宽条件，提高检测率
                is_upper_body_candidate = False
                
                # 条件1: 宽高比范围大幅放宽
                # 条件2: 降低高度要求
                # 条件3: 放宽中心位置要求
                # 条件4: 大幅放宽紧凑度要求
                if ((aspect_ratio_min * 0.5 < aspect_ratio < aspect_ratio_max * 2.0) and 
                    h_rect > h * upper_body_min_height_ratio * 0.5 and 
                    (abs(contour_center_y - h/2) < h * upper_body_center_offset * 2.0 or 
                     # 额外条件：轮廓在ROI的任何位置都可能是上半身
                     True) and 
                    compactness < 0.95):  # 大幅放宽紧凑度要求
                    is_upper_body_candidate = True
                
                # 额外的头部检测启发式方法：寻找可能的头部轮廓
                has_potential_head = False
                # 大幅放宽头部检测条件
                if h_rect > h * 0.15 and y_rect < h * 0.4:  # 放宽头部的位置和大小范围
                    # 检查轮廓是否有类似头部的特征
                    if w_rect > h_rect * 0.5 and compactness > 0.3:  # 大幅放宽头部特征要求
                        has_potential_head = True
                
                # 针对静态人体的检测条件 - 大幅放宽条件
                is_static_person_candidate = False
                if static_detection_enabled and area > min_static_area * 0.3:  # 大幅降低面积要求
                    # 静态人体通常有一定的宽高比和面积特征
                    if (aspect_ratio_min * 0.3 < aspect_ratio < aspect_ratio_max * 3.0 and  # 大幅放宽范围
                        h_rect > h * 0.15 and  # 大幅降低高度要求
                        (w_rect > w * 0.1 or  # 大幅放宽宽度要求
                         area > w * h * 0.02)):  # 大幅降低面积比例要求
                        is_static_person_candidate = True
                
                # 综合判断：满足上半身条件、有头部特征或满足静态人体条件，则认为检测到人
                if is_upper_body_candidate or has_potential_head or is_static_person_candidate:
                    person_detected = True
                    break
        
        # 简化版：只检测是否有人，不进行人脸识别
        person_id = "有人" if person_detected else None
        
        return person_detected, person_id
    
    def update_occupancy_status(self):
        """更新座位占用状态，添加状态滤波逻辑"""
        current_time = datetime.datetime.now()
        
        # 捕获图像
        frame = self.camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            
            # 检测区域内是否有人
            person_detected, person_id = self.detect_person_in_region(frame, region)
            
            # 更新占用状态，添加滤波逻辑
            if person_detected:
                # 检测到有人，重置离开计数器
                self.leave_counters[seat_id] = 0
                
                if not self.occupancy_status[seat_id]['occupied']:
                    # 有人坐下
                    self.occupancy_status[seat_id]['occupied'] = True
                    self.occupancy_status[seat_id]['entry_time'] = current_time
                    self.occupancy_status[seat_id]['person_id'] = person_id
                    print(f"[{current_time}] {seat['name']}被{person_id if person_id else '某人'}占用")
            else:
                # 没有检测到人
                if self.occupancy_status[seat_id]['occupied']:
                    # 已经记录为有人，增加离开计数器
                    self.leave_counters[seat_id] += 1
                    
                    # 设置连续检测到离开的帧数阈值（从配置中读取，适应静止和遮挡情况）
                    # 适中的阈值平衡了误报率和响应速度
                    leave_threshold = self.config['detection'].get('leave_detection_threshold', 15)
                    if self.leave_counters[seat_id] >= leave_threshold:
                        # 确认人离开
                        self.occupancy_status[seat_id]['occupied'] = False
                        self.occupancy_status[seat_id]['exit_time'] = current_time
                        duration = (current_time - self.occupancy_status[seat_id]['entry_time']).total_seconds()
                        self.occupancy_status[seat_id]['duration'] = duration
                        
                        # 记录本次占用信息
                        record = {
                            'seat_id': seat_id,
                            'seat_name': seat['name'],
                            'entry_time': self.occupancy_status[seat_id]['entry_time'],
                            'exit_time': current_time,
                            'duration_seconds': duration,
                            'person_id': self.occupancy_status[seat_id]['person_id']
                        }
                        self.records.append(record)
                        self.save_record(record)
                        
                        print(f"[{current_time}] {seat['name']}被释放，占用时长: {duration/60:.2f}分钟")
                        # 重置计数器
                        self.leave_counters[seat_id] = 0
        
        # 检查是否需要定期保存数据（即使当前没有人离开）
        if (current_time - self.last_save_time).total_seconds() > self.save_interval:
            self.save_current_state()
            self.last_save_time = current_time
        
        # 检查是否需要生成每日报告
        if current_time.date() > self.last_report_generation:
            self.generate_daily_report(self.last_report_generation)
            self.last_report_generation = current_time.date()
        
        return frame
    
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
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            status = self.occupancy_status[seat_id]
            
            # Set color based on occupancy status
            color = (0, 0, 255) if status['occupied'] else (0, 255, 0)
            thickness = 2 if status['occupied'] else 1
            
            # Draw region
            cv2.polylines(frame, [np.array(region)], True, color, thickness)
            
            # Display seat name and status (using English to avoid display issues)
            status_text = "Occupied" if status['occupied'] else "Empty"
            text = f"{seat['name']}: {status_text}"
            if status['occupied'] and status['person_id']:
                text += f" ({status['person_id']})"
            
            # Draw text using OpenCV with English
            cv2.putText(frame, text, (region[0][0], region[0][1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Display current time
        current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, current_time_str, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def run(self):
        """运行监控系统"""
        try:
            print("座位监控系统已启动，按'q'键退出")
            print("当前模式：简化版 - 持续显示摄像头内容，检测是否有人")
            
            # 初始化显示窗口
            window_name = '座位监控系统'
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, self.config['camera']['resolution']['width'], 
                             self.config['camera']['resolution']['height'])
            
            # 初始化帧时间戳，用于动态调整检测频率
            last_frame_time = datetime.datetime.now()
            
            while self.running:
                try:
                    # 更新占用状态并获取当前帧
                    frame = self.update_occupancy_status()
                    
                    # 检查帧是否获取成功
                    if frame is None or frame.size == 0:
                        print("警告：未能获取摄像头图像帧")
                        time.sleep(1)  # 暂停1秒后重试
                        continue
                    
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
                    print(f"处理帧时出错: {str(e)}")
                    time.sleep(0.5)  # 出错时稍作暂停再继续
        
        except KeyboardInterrupt:
            print("系统被用户中断")
        finally:
            # 清理资源
            try:
                self.camera.stop()
                cv2.destroyAllWindows()
                print("摄像头已关闭，窗口已销毁")
            except Exception as e:
                print(f"清理资源时出错: {str(e)}")
            
            try:
                # 最后保存一次当前状态
                self.save_current_state()
            except Exception as e:
                print(f"保存状态时出错: {str(e)}")
            
            try:
                # 生成当天的报告
                today = datetime.date.today()
                self.generate_daily_report(today)
            except Exception as e:
                print(f"生成报告时出错: {str(e)}")
            
            print("座位监控系统已关闭")

def main():
    """主函数，程序的入口点"""
    try:
        # 创建座位监控实例
        monitor = SeatMonitor()
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