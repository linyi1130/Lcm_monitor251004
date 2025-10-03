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

class SeatMonitor:
    def __init__(self, config_file='config.json'):
        # 加载配置文件
        self.config = self.load_config(config_file)
        
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
        
        # 设置座位区域
        self.seat_regions = []
        for seat_config in self.config['seats']:
            # 转换区域坐标格式
            region = [(p[0], p[1]) for p in seat_config['region']]
            self.seat_regions.append({
                "id": seat_config['id'],
                "name": seat_config['name'],
                "region": region
            })
        
        # 人员状态跟踪
        self.occupancy_status = {}
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
        
        print("座位监控系统已初始化")
        
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            # 返回默认配置
            return {
                "camera": {
                    "resolution": {"width": 1280, "height": 720},
                    "framerate": 10,
                    "rotation": 0
                },
                "detection": {
                    "motion_threshold": 10000,
                    "face_recognition_tolerance": 0.6,
                    "detection_interval": 0.1
                },
                "seats": [
                    {"id": 1, "name": "座位1", "region": [[100, 150], [300, 150], [300, 350], [100, 350]]},
                    {"id": 2, "name": "座位2", "region": [[350, 150], [550, 150], [550, 350], [350, 350]]},
                    {"id": 3, "name": "座位3", "region": [[600, 150], [800, 150], [800, 350], [600, 350]]}
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
    
    def load_known_faces(self):
        """加载已知人脸数据"""
        try:
            for filename in os.listdir(self.known_faces_dir):
                if filename.endswith('.jpg') or filename.endswith('.png'):
                    name = os.path.splitext(filename)[0]
                    image_path = os.path.join(self.known_faces_dir, filename)
                    image = face_recognition.load_image_file(image_path)
                    face_encodings = face_recognition.face_encodings(image)
                    if face_encodings:
                        self.face_encodings.append(face_encodings[0])
                        self.face_names.append(name)
        except Exception as e:
            print(f"加载已知人脸数据失败: {str(e)}")
    
    def detect_person_in_region(self, frame, region):
        """检测指定区域内是否有人"""
        # 提取区域ROI
        x = min([p[0] for p in region])
        y = min([p[1] for p in region])
        w = max([p[0] for p in region]) - x
        h = max([p[1] for p in region]) - y
        roi = frame[y:y+h, x:x+w].copy()
        
        # 转换为灰度图进行轮廓检测
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 70, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 检查是否有足够大的轮廓（可能是人体）
        person_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.config['detection']['motion_threshold']:
                person_detected = True
                break
        
        # 人脸检测和识别
        face_locations = face_recognition.face_locations(roi)
        face_encodings = face_recognition.face_encodings(roi, face_locations)
        
        person_id = None
        if face_encodings:
            # 尝试识别已知人脸
            tolerance = self.config['detection']['face_recognition_tolerance']
            matches = face_recognition.compare_faces(self.face_encodings, face_encodings[0], tolerance=tolerance)
            if True in matches:
                first_match_index = matches.index(True)
                person_id = self.face_names[first_match_index]
            else:
                # 未知人脸，分配临时ID
                person_id = f"未知{len(self.face_names) + 1}"
        
        return person_detected, person_id
    
    def update_occupancy_status(self):
        """更新座位占用状态"""
        current_time = datetime.datetime.now()
        
        # 捕获图像
        frame = self.camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            
            # 检测区域内是否有人
            person_detected, person_id = self.detect_person_in_region(frame, region)
            
            # 更新占用状态
            if person_detected and not self.occupancy_status[seat_id]['occupied']:
                # 有人坐下
                self.occupancy_status[seat_id]['occupied'] = True
                self.occupancy_status[seat_id]['entry_time'] = current_time
                self.occupancy_status[seat_id]['person_id'] = person_id
                print(f"[{current_time}] {seat['name']}被{person_id if person_id else '某人'}占用")
            elif not person_detected and self.occupancy_status[seat_id]['occupied']:
                # 人离开
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
        """在视频帧上绘制座位区域和状态"""
        for seat in self.seat_regions:
            seat_id = seat['id']
            region = seat['region']
            status = self.occupancy_status[seat_id]
            
            # 根据占用状态设置颜色
            color = (0, 0, 255) if status['occupied'] else (0, 255, 0)
            thickness = 2 if status['occupied'] else 1
            
            # 绘制区域
            cv2.polylines(frame, [np.array(region)], True, color, thickness)
            
            # 显示座位名称和状态
            text = f"{seat['name']}: {'有人' if status['occupied'] else '无人'}"
            if status['occupied'] and status['person_id']:
                text += f" ({status['person_id']})"
            cv2.putText(frame, text, (region[0][0], region[0][1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 显示当前时间
        current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, current_time_str, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def run(self):
        """运行监控系统"""
        try:
            print("座位监控系统已启动，按'q'键退出")
            
            while self.running:
                # 更新占用状态并获取当前帧
                frame = self.update_occupancy_status()
                
                # 绘制叠加层
                display_frame = self.draw_overlay(frame)
                
                # 显示结果
                cv2.imshow('座位监控系统', display_frame)
                
                # 检查退出按键
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    
                # 根据配置文件中的检测间隔调整帧率
                time.sleep(self.detection_interval)
        
        except KeyboardInterrupt:
            print("系统被用户中断")
        finally:
            # 清理资源
            self.camera.stop()
            cv2.destroyAllWindows()
            
            # 最后保存一次当前状态
            self.save_current_state()
            
            # 生成当天的报告
            today = datetime.date.today()
            self.generate_daily_report(today)
            
            print("座位监控系统已关闭")

if __name__ == "__main__":
    monitor = SeatMonitor()
    monitor.run()