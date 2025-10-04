#!/bin/bash

# 在虚拟环境中运行座位监控系统测试

# 确保脚本在错误时退出
set -e

# 虚拟环境名称
VENV_NAME="seat_monitor_venv"

# 检查虚拟环境是否存在
if [ ! -d "$VENV_NAME" ]; then
    echo "虚拟环境 '$VENV_NAME' 不存在，正在创建..."
    python3 -m venv "$VENV_NAME"
    
    # 激活虚拟环境
source "$VENV_NAME/bin/activate"
    
    # 更新pip
echo "更新pip..."
pip install --upgrade pip
    
    # 安装项目依赖（包括测试依赖）
echo "安装项目依赖和测试依赖..."
if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "错误：未找到requirements.txt文件"
        exit 1
    fi
    
    # 安装pandas（测试报告生成需要）
pip install pandas
fi

# 激活虚拟环境
echo "激活虚拟环境 '$VENV_NAME'..."
source "$VENV_NAME/bin/activate"

# 运行测试脚本
echo "正在运行座位监控系统测试..."
python test_system.py

# 测试结束
echo "座位监控系统测试已完成"