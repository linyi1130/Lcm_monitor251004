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
   ```bash
   sudo apt install python3-pip python3-opencv libopenjp2-7 -y
   
   # 尝试安装libtiff相关包（根据不同Linux发行版，包名可能有所不同）
   sudo apt install libtiff5 -y || sudo apt install libtiff-dev -y || sudo apt install libtiff-tools -y
   ```
   
   *注意：如果上述命令执行失败，可能是因为您的Linux发行版中包名称不同。请根据您的系统实际情况安装相应的libtiff包。*

3. **克隆项目代码**
   ```bash
   git clone https://your-repository-url/lcm_monitor.git
   cd lcm_monitor
   ```

4. **使用虚拟环境安装Python依赖（推荐）**
   ```bash
   # 运行虚拟环境设置脚本
   bash setup_venv.sh
   ```

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
   bash start_monitor.sh
   
   # 或者手动激活虚拟环境并运行
   source seat_monitor_venv/bin/activate
   python main.py
   ```
   
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

## 版权信息

© 2025 座位监控系统开发团队
保留所有权利