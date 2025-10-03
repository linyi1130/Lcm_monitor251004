#!/bin/bash

# 座位监控系统启动脚本

# 确保脚本在错误时退出
set -e

# 检查Python是否安装
if ! command -v python3 &> /dev/null
then
    echo "Python 3 未安装，请先安装Python 3"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null
then
    echo "pip3 未安装，正在安装..."
    sudo apt update
    sudo apt install python3-pip -y
fi

# 安装依赖
echo "正在安装项目依赖..."
pip3 install -r requirements.txt

# 确保主程序有执行权限
chmod +x seat_monitor.py

# 运行程序
echo "正在启动座位监控系统..."
python3 seat_monitor.py

# 程序结束
echo "座位监控系统已停止"