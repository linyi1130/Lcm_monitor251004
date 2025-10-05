#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
座位监控系统测试脚本
用于在没有实际摄像头的环境下测试系统的基本功能
"""

import os
import sys
import json
import datetime
import time
import shutil
from pathlib import Path
import argparse

class SeatMonitorTest:
    def __init__(self, verbose=False):
        # 控制输出详细程度的标志
        self.verbose = verbose
        
        # 检查项目文件是否齐全
        self.check_project_files()
        
        # 创建测试目录
        self.test_dir = "test_env"
        self.create_test_environment()
        
        if self.verbose:
            print("测试环境已准备就绪")
    
    def check_project_files(self):
        """检查项目必要文件是否存在"""
        required_files = [
            "seat_monitor.py",
            "config.json",
            "requirements.txt",
            "README.md",
            "start_monitor.sh"
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.isfile(file):
                missing_files.append(file)
        
        if missing_files:
            print(f"警告：缺少以下必要文件：{', '.join(missing_files)}")
            print("建议先完成项目的基本文件创建")
    
    def create_test_environment(self):
        """创建测试环境"""
        # 如果测试目录已存在，先删除
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        # 创建测试目录结构
        test_dirs = [
            self.test_dir,
            os.path.join(self.test_dir, "data"),
            os.path.join(self.test_dir, "reports"),
            os.path.join(self.test_dir, "known_faces")
        ]
        
        for dir_path in test_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # 创建模拟数据文件
        self.create_sample_data()
    
    def create_sample_data(self):
        """创建测试用的模拟数据"""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        # 创建昨天的数据文件
        data_file = os.path.join(self.test_dir, "data", f"occupancy_records_{yesterday.strftime('%Y%m%d')}.csv")
        with open(data_file, 'w', encoding='utf-8') as f:
            f.write("seat_id,seat_name,entry_time,exit_time,duration_seconds,person_id\n")
            f.write("1,座位1,2025-10-04 09:00:00,2025-10-04 10:30:00,5400,张三\n")
            f.write("2,座位2,2025-10-04 09:15:00,2025-10-04 11:45:00,9000,李四\n")
            f.write("1,座位1,2025-10-04 13:00:00,2025-10-04 15:20:00,8400,王五\n")
            f.write("3,座位3,2025-10-04 14:00:00,2025-10-04 16:30:00,9000,未知1\n")
    
    def simulate_occupancy(self):
        """模拟座位占用情况"""
        if self.verbose:
            print("\n=== 模拟座位占用测试 ===")
        
        # 模拟时间流逝和座位状态变化
        events = [
            {"time": "09:00:00", "seat_id": 1, "occupied": True, "person_id": "张三"},
            {"time": "09:15:00", "seat_id": 2, "occupied": True, "person_id": "李四"},
            {"time": "10:30:00", "seat_id": 1, "occupied": False},
            {"time": "11:45:00", "seat_id": 2, "occupied": False},
            {"time": "13:00:00", "seat_id": 1, "occupied": True, "person_id": "王五"},
            {"time": "14:00:00", "seat_id": 3, "occupied": True, "person_id": "未知1"},
            {"time": "15:20:00", "seat_id": 1, "occupied": False},
            {"time": "16:30:00", "seat_id": 3, "occupied": False}
        ]
        
        # 模拟状态跟踪
        current_state = {1: False, 2: False, 3: False}
        entry_times = {}
        
        for event in events:
            event_time = datetime.datetime.strptime(event["time"], "%H:%M:%S").time()
            current_dt = datetime.datetime.combine(datetime.date.today(), event_time)
            
            seat_id = event["seat_id"]
            occupied = event["occupied"]
            person_id = event.get("person_id", "未知")
            
            if occupied and not current_state[seat_id]:
                # 有人坐下
                current_state[seat_id] = True
                entry_times[seat_id] = current_dt
                # 只在verbose模式下输出详细信息
                if self.verbose:
                    print(f"[{current_dt.time()}] 座位{seat_id}被{person_id}占用")
            elif not occupied and current_state[seat_id]:
                # 人离开
                current_state[seat_id] = False
                exit_time = current_dt
                duration = (exit_time - entry_times[seat_id]).total_seconds()
                # 只在verbose模式下输出详细信息
                if self.verbose:
                    print(f"[{current_dt.time()}] 座位{seat_id}被释放，占用时长: {duration/60:.2f}分钟")
            
            # 模拟时间间隔
            time.sleep(0.5)
    
    def test_report_generation(self):
        """测试报告生成功能"""
        if self.verbose:
            print("\n=== 测试报告生成功能 ===")
        
        # 模拟生成报告
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        data_file = os.path.join(self.test_dir, "data", f"occupancy_records_{yesterday.strftime('%Y%m%d')}.csv")
        report_file = os.path.join(self.test_dir, "reports", f"daily_report_{yesterday.strftime('%Y%m%d')}.txt")
        
        try:
            # 读取模拟数据
            import pandas as pd
            df = pd.read_csv(data_file)
            
            # 统计信息
            total_records = len(df)
            unique_persons = df['person_id'].nunique()
            total_duration = df['duration_seconds'].sum() / 3600  # 转换为小时
            
            # 按座位统计
            seat_stats = df.groupby('seat_name').agg({
                'duration_seconds': ['sum', 'count'],
                'person_id': 'nunique'
            }).reset_index()
            
            # 生成测试报告
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"===== 座位监控每日报告 =====\n")
                f.write(f"报告日期: {yesterday.strftime('%Y年%m月%d日')}\n")
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
            
            if self.verbose:
                print(f"测试报告已生成: {report_file}")
                print(f"报告内容预览:\n")
                
                # 显示报告内容
                with open(report_file, 'r', encoding='utf-8') as f:
                    print(f.read())
        except Exception as e:
            print(f"生成测试报告时出错: {str(e)}")
            print("请确保已安装pandas库: pip install pandas")
    
    def run_all_tests(self):
        """运行所有测试"""
        if self.verbose:
            print("开始运行系统测试...")
        
        # 测试配置文件解析
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            if self.verbose:
                print("\n=== 配置文件测试 ===")
                print(f"成功解析配置文件，检测到 {len(config['seats'])} 个座位区域")
                print(f"摄像头分辨率: {config['camera']['resolution']['width']}x{config['camera']['resolution']['height']}")
        except Exception as e:
            print(f"配置文件测试失败: {str(e)}")
        
        # 模拟座位占用
        self.simulate_occupancy()
        
        # 测试报告生成
        self.test_report_generation()
        
        if self.verbose:
            print("\n=== 测试完成 ===")
            print(f"测试数据保存在: {self.test_dir}")
            print("提示：在实际部署时，请确保Camera Module 3已正确连接并启用")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='座位监控系统测试脚本')
    parser.add_argument('-v', '--verbose', action='store_true', help='启用详细输出模式')
    args = parser.parse_args()
    
    tester = SeatMonitorTest(verbose=args.verbose)
    tester.run_all_tests()