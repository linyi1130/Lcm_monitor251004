# 座位监控系统

基于Raspberry Pi OS和Camera Module 3的人员座位监控系统，能够自动监测指定座位区域的人员行为，记录入座、离开时间及持续时长，并自动生成每日监控报告。

## 系统功能

1. **人员行为监控**：实时监测指定座位区域内的人员活动
2. **时间记录**：准确记录人员入座时间、离开时间及持续时长
3. **人脸识别**：支持识别已知人员（可选功能）
4. **自动报告生成**：每天自动生成详细的座位使用情况报告
5. **可视化界面**：实时显示座位状态和监控画面

## 硬件要求

- Raspberry Pi 5（推荐，或兼容的Raspberry Pi型号）
- Camera Module 3
- 足够的电源供应
- MicroSD卡（至少32GB，推荐Class 10）
- 可选：显示屏、键盘、鼠标（用于现场监控）

## 软件要求

- Raspberry Pi OS（2025年10月及之后发布，基于Debian 13 "Trixie"）
- Python 3.10或更高版本
- 所需Python库（详见requirements.txt）

## 安装指南

1. **更新系统软件包**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **安装必要的系统依赖**

   **对于Raspberry Pi OS的完整安装步骤：**
   
   由于Raspberry Pi OS上dlib构建特别敏感，我们提供以下优化的安装步骤，以确保cmake正确安装：
   
   ```bash
   # 1. 更新包列表
   sudo apt update -y
   
   # 2. 移除可能存在的损坏cmake副本（重要步骤）
   sudo apt purge -y cmake
   sudo rm -rf /usr/local/bin/cmake /usr/local/lib/cmake
   # 移除Python包管理器可能安装的损坏cmake
   sudo rm -rf $(python3 -c "import sys; print(sys.prefix)")/bin/cmake || true
   
   # 3. 重新安装官方cmake和所有必要的依赖
   sudo apt install -y cmake build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev libcap-dev
   
   # 4. 安装基本系统依赖
   sudo apt install -y python3-pip python3-opencv libopenjp2-7
   
   # 5. 安装额外的开发工具
   sudo apt install -y python3-dev git libtiff5
   
   # 6. 安装libcamera系统依赖（支持Camera Module 3和Picamera2）
   sudo apt install -y python3-libcamera python3-kms++ python3-pyqt5 python3-prctl libatlas-base-dev ffmpeg
   sudo apt install -y libcamera-apps libcamera-dev
   
   # 7. 验证cmake安装
   echo "===== CMake安装验证 ===="
   cmake --version
   which cmake
   dpkg -l | grep cmake
   echo "======================="
   
   # 8. 验证libcamera安装
   echo "===== libcamera安装验证 ===="
   dpkg -l | grep libcamera
   echo "======================="
   ```
   
   *注意1：dlib的构建严重依赖cmake，请确保上述验证步骤显示cmake已正确安装。*
   *注意2：如果在安装过程中遇到问题，请参考HELP_RUNNING_SCRIPTS.md文件中的详细故障排除指南。*

3. **克隆项目代码**
   ```bash
   git clone https://your-repository-url/lcm_monitor.git
   cd lcm_monitor
   ```

4. **使用虚拟环境安装Python依赖（推荐）**
   ```bash
   # 运行虚拟环境设置脚本（方法1：使用bash显式运行）
   bash setup_venv.sh
   
   # 或者（方法2：添加执行权限后直接运行）
   chmod +x setup_venv.sh
   ./setup_venv.sh
   ```
   
   *注意：如果遇到 "setup_venv.sh: command not found" 错误，请使用上述任意一种方法运行脚本。*

   或者手动设置虚拟环境：
   ```bash
   # 创建虚拟环境
   python3 -m venv seat_monitor_venv
   
   # 激活虚拟环境
   source seat_monitor_venv/bin/activate
   
   # 更新pip
   pip install --upgrade pip
   
   # 安装项目依赖
   pip install -r requirements.txt
   ```

   不使用虚拟环境的安装方式（不推荐）：
   ```bash
   pip3 install -r requirements.txt
   ```

   **虚拟环境配置说明：**
   
   注意：libcamera是一个系统级Python模块，默认情况下虚拟环境可能无法访问系统安装的模块。我们的安装脚本已经自动配置了虚拟环境以允许访问系统模块，但如果您遇到导入libcamera模块的问题，可以检查虚拟环境配置文件：

   ```bash
   # 检查虚拟环境配置
   cat seat_monitor_venv/pyvenv.cfg

   # 确保配置中包含以下行
   # include-system-site-packages = true
   ```

   如果需要手动修复配置：

   ```bash
   # 编辑虚拟环境配置文件
   sed -i 's/include-system-site-packages = false/include-system-site-packages = true/g' seat_monitor_venv/pyvenv.cfg
   ```

5. **启用Camera Module 3**
   - 通过Raspberry Pi配置工具启用摄像头：
   ```bash
   sudo raspi-config
   ```
   - 选择"Interface Options" > "Camera" > "Yes"启用摄像头
   - 重启Raspberry Pi：
   ```bash
   sudo reboot
   ```

## 配置说明

系统配置文件为`config.json`，可根据实际需求进行修改：

1. **摄像头设置**：分辨率、帧率、旋转角度
2. **检测参数**：动作检测阈值、人脸识别容差、检测间隔
3. **座位区域**：可以自定义座位数量、名称和坐标区域
4. **数据存储**：保存间隔、报告和数据目录设置

## 使用方法

1. **启动系统**
   
   使用虚拟环境运行（推荐）：
   ```bash
   # 使用启动脚本（会自动处理虚拟环境）
   # 方法1：使用bash显式运行
   bash start_monitor.sh
   
   # 或者（方法2：添加执行权限后直接运行）
   chmod +x start_monitor.sh
   ./start_monitor.sh
   
   # 或者手动激活虚拟环境并运行
   source seat_monitor_venv/bin/activate
   python main.py
   ```
   
   *注意：如果遇到 "start_monitor.sh: command not found" 错误，请使用上述任意一种方法运行脚本。*
   
   不使用虚拟环境的运行方式（不推荐）：
   ```bash
   python3 main.py
   ```

2. **操作说明**
   - 程序启动后会自动开始监控
   - 按"q"键可以退出程序
   - 系统会自动在指定目录下生成数据文件和报告

3. **添加已知人脸（可选）**
   - 将人脸照片保存到`known_faces`目录
   - 照片文件名（不含扩展名）将作为人员识别的名称
   - 支持JPG和PNG格式

4. **运行系统测试**
   在没有实际摄像头的环境下，可以使用测试脚本来验证系统功能：
   ```bash
   # 方法1：使用bash显式运行测试脚本
   bash test_in_venv.sh
   
   # 或者（方法2：添加执行权限后直接运行）
   chmod +x test_in_venv.sh
   ./test_in_venv.sh
   ```
   
   *注意：如果遇到 "test_in_venv.sh: command not found" 错误，请使用上述任意一种方法运行脚本。*

## 目录结构

```
lcm_monitor/
├── seat_monitor.py      # 主程序文件
├── main.py              # 程序入口点
├── config.json          # 配置文件
├── requirements.txt     # Python依赖列表
├── README.md            # 项目说明文档
├── setup_venv.sh        # 虚拟环境设置脚本
├── start_monitor.sh     # 系统启动脚本
├── test_system.py       # 测试脚本
├── test_in_venv.sh      # 虚拟环境中运行测试的脚本
├── data/                # 存储原始记录数据
├── reports/             # 存储生成的报告
└── known_faces/         # 存储已知人脸图像（用于识别）
```

## 数据记录格式

系统会在`data`目录下按日期生成CSV格式的数据文件，包含以下字段：
- `seat_id`：座位ID
- `seat_name`：座位名称
- `entry_time`：入座时间
- `exit_time`：离开时间
- `duration_seconds`：持续时长（秒）
- `person_id`：人员ID（如启用人脸识别）

## 每日报告

系统会在每天结束时自动生成报告，包含以下信息：
- 报告日期
- 总记录数
- 涉及人员数量
- 总占用时长
- 各座位使用统计（使用次数、使用人数、总时长）

## 故障排除

1. **摄像头无法识别**
   - 检查摄像头连接是否正确
   - 确认已在Raspberry Pi配置中启用摄像头
   - 重启Raspberry Pi后重试

2. **识别不准确**
   - 调整`config.json`中的`motion_threshold`参数
   - 确保光照条件良好
   - 重新校准座位区域坐标

3. **程序崩溃或性能问题**
   - 降低摄像头分辨率
   - 增加检测间隔时间
   - 关闭不必要的后台程序

## 注意事项

- 首次运行时，系统会自动创建必要的目录
- 建议定期备份`data`和`reports`目录中的数据
- 长时间运行可能会产生大量数据，请确保有足够的存储空间
- 如需开机自启，可以将启动命令添加到`/etc/rc.local`文件中
- 使用虚拟环境可以更好地隔离项目依赖，避免与系统Python环境冲突
- 如果遇到脚本运行权限问题，请参考[HELP_RUNNING_SCRIPTS.md](HELP_RUNNING_SCRIPTS.md)文件获取详细解决方案

## 版权信息

© 2025 座位监控系统开发团队
保留所有权利