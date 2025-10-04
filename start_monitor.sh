#!/bin/bash

# 座位监控系统启动脚本 - 使用虚拟环境

# 确保脚本在错误时退出
set -e

# 虚拟环境名称
VENV_NAME="seat_monitor_venv"

# 检查Python是否安装
if ! command -v python3 &> /dev/null
then
    echo "Python 3 未安装，请先安装Python 3"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "$VENV_NAME" ]; then
    echo "虚拟环境 '$VENV_NAME' 不存在，正在创建..."
    python3 -m venv "$VENV_NAME"
    
    # 允许虚拟环境访问系统Python模块
    echo "配置虚拟环境以允许访问系统Python模块..."
    VENV_CONFIG="$VENV_NAME/pyvenv.cfg"
    if [ -f "$VENV_CONFIG" ]; then
        sed -i '' 's/include-system-site-packages = false/include-system-site-packages = true/g' "$VENV_CONFIG"
    else
        echo "include-system-site-packages = true" > "$VENV_CONFIG"
    fi
    
    # 激活虚拟环境
source "$VENV_NAME/bin/activate"
    
    # 更新pip
echo "更新pip..."
pip install --upgrade pip
    
    # 检查cmake是否安装（face_recognition/dlib依赖）
echo "检查cmake是否正确安装..."
if ! command -v cmake &> /dev/null; then
        echo "警告：cmake未安装，这将导致face_recognition/dlib安装失败"
        echo "建议在继续前安装cmake："
        echo "  sudo apt-get update"
        echo "  sudo apt-get install -y cmake"
        echo "  sudo apt-get install -y build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev"
        echo "按Enter键继续安装（可能会失败），或按Ctrl+C取消..."
        read -r
    fi
    
    # 检查libcamera依赖（Picamera2依赖）
echo "检查libcamera依赖是否正确安装..."
if ! python3 -c "import libcamera" &> /dev/null; then
        echo "警告：libcamera模块未安装，这将导致Picamera2初始化失败"
        echo "建议在继续前安装libcamera依赖："
        echo "  sudo apt-get update"
        echo "  sudo apt-get install -y python3-libcamera python3-kms++"
        echo "  sudo apt-get install -y libcamera-apps libcamera-dev"
        echo "按Enter键继续安装（可能会失败），或按Ctrl+C取消..."
        read -r
    fi
    
    # 安装项目依赖
echo "安装项目依赖..."
if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "错误：未找到requirements.txt文件"
        exit 1
    fi
fi

# 激活虚拟环境前先检查配置
echo "检查虚拟环境配置..."
# 确保虚拟环境允许访问系统Python模块
VENV_CONFIG="$VENV_NAME/pyvenv.cfg"
if [ -f "$VENV_CONFIG" ]; then
    if ! grep -q "include-system-site-packages = true" "$VENV_CONFIG"; then
        echo "配置虚拟环境以允许访问系统Python模块..."
        sed -i '' 's/include-system-site-packages = false/include-system-site-packages = true/g' "$VENV_CONFIG"
    fi
else
    echo "警告：未找到虚拟环境配置文件，可能需要重新创建虚拟环境"
fi

# 激活虚拟环境
echo "激活虚拟环境 '$VENV_NAME'..."
source "$VENV_NAME/bin/activate"

# 运行程序
echo "正在启动座位监控系统..."
python main.py

# 程序结束
echo "座位监控系统已停止"