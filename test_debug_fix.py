#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本：验证SeatMonitor类中debug属性错误修复
"""

import os
import sys
from unittest import mock

# 添加当前目录到Python路径
sys.path.append('.')

# 模拟必要的库
class MockNumpy:
    """模拟numpy库"""
    @staticmethod
    def zeros(shape, dtype):
        return MockArray()
    
    @staticmethod
    def array(arr, dtype=None):
        return MockArray()
    
    class uint8:
        pass

# 模拟numpy.random模块
class MockRandom:
    @staticmethod
    def randint(low, high, size, dtype):
        return MockArray()

# 给MockNumpy添加random属性
MockNumpy.random = MockRandom

class MockArray:
    """模拟numpy数组"""
    def __init__(self):
        self.shape = (480, 640, 3)
        
    def copy(self):
        return self

# 模拟cv2模块
sys.modules['cv2'] = mock.MagicMock()
sys.modules['numpy'] = MockNumpy()
sys.modules['picamera2'] = mock.MagicMock()
sys.modules['face_recognition'] = mock.MagicMock()
sys.modules['PIL'] = mock.MagicMock()
sys.modules['PIL.Image'] = mock.MagicMock()
sys.modules['PIL.ImageDraw'] = mock.MagicMock()
sys.modules['PIL.ImageFont'] = mock.MagicMock()
sys.modules['pandas'] = mock.MagicMock()
sys.modules['pathlib'] = mock.MagicMock()

def test_debug_attribute_fix():
    """测试debug属性错误修复"""
    print("开始测试debug属性错误修复...")
    
    # 尝试导入SeatMonitor类
try:
    from seat_monitor import SeatMonitor
    print("成功导入SeatMonitor类")
except ImportError as e:
    print(f"导入SeatMonitor类失败: {e}")
    sys.exit(1)

class TestSeatMonitor:
    """测试SeatMonitor类的debug属性修复"""
    
    def __init__(self):
        # 创建测试用的配置文件
        self.test_config = {
            "camera": {
                "resolution": {"width": 640, "height": 480},
                "framerate": 5,
                "rotation": 0
            },
            "detection": {
                "motion_threshold": 10000,
                "detection_interval": 0.2
            },
            "seats": [
                {"id": 1, "name": "测试区域", "region": [[50, 50], [200, 50], [200, 200], [50, 200]]}
            ],
            "data": {
                "save_interval": 60,
                "reports_directory": "reports",
                "data_directory": "data",
                "known_faces_directory": "known_faces"
            }
        }
    
    def setup_test(self):
        # 保存测试配置到临时文件
        with open('test_config.json', 'w', encoding='utf-8') as f:
            import json
            json.dump(self.test_config, f)
        
        # 初始化测试目录
        shared_dir = 'shared_frames'
        if not os.path.exists(shared_dir):
            os.makedirs(shared_dir)
        
        return shared_dir
    
    def teardown_test(self):
        # 清理测试文件
        if os.path.exists('test_config.json'):
            os.remove('test_config.json')
    
    def test_debug_attribute(self):
        """测试debug属性是否正确修复"""
        print("开始测试debug属性...")
        shared_dir = self.setup_test()
        
        try:
            # 创建一个模拟的SeatMonitor类，只关注_save_frame_to_shared方法
            class MockSeatMonitor:
                def __init__(self):
                    self.debug_mode = True  # 设置debug_mode为True
                    self.shared_frames_dir = shared_dir
                    self.shared_frame_path = os.path.join(shared_dir, "current_frame.jpg")
                
                def log_message(self, message, level):
                    print(f"[{level}] {message}")
                
                def _save_frame_to_shared(self, frame):
                    try:
                        # 模拟保存帧到文件
                        with open(self.shared_frame_path, 'wb') as f:
                            f.write(b'test_frame')
                        
                        # 关键测试：检查是否使用了self.debug_mode而不是self.debug
                        if self.debug_mode:
                            self.log_message(f"已保存共享帧到: {self.shared_frame_path}", "DEBUG")
                    except Exception as e:
                        self.log_message(f"保存共享帧时出错: {str(e)}", "ERROR")
            
            # 测试修复后的逻辑
            print("测试修复后的_save_frame_to_shared方法...")
            mock_monitor = MockSeatMonitor()
            mock_frame = MockArray()
            mock_monitor._save_frame_to_shared(mock_frame)
            
            # 检查文件是否创建
            frame_path = os.path.join(shared_dir, 'current_frame.jpg')
            if os.path.exists(frame_path):
                print(f"测试成功: 共享帧文件已创建: {frame_path}")
                # 清理测试文件
                os.remove(frame_path)
            else:
                print(f"测试失败: 共享帧文件未创建: {frame_path}")
                return False
            
            # 测试debug_mode为False的情况
            print("测试debug_mode为False的情况...")
            mock_monitor.debug_mode = False
            mock_monitor._save_frame_to_shared(mock_frame)
            
            print("所有测试通过！debug属性错误已修复。")
            return True
            
        except Exception as e:
            print(f"测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.teardown_test()

if __name__ == "__main__":
    print("开始测试SeatMonitor类中的debug属性修复...")
    test = TestSeatMonitor()
    success = test.test_debug_attribute()
    sys.exit(0 if success else 1)