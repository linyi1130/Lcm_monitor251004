#!/bin/bash

# 创建和设置Python虚拟环境

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

# 检查是否已经存在虚拟环境
if [ -d "$VENV_NAME" ]; then
    echo "检测到已存在的虚拟环境 '$VENV_NAME'，是否重新创建？(y/n)"
    read answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "删除现有的虚拟环境..."
        rm -rf "$VENV_NAME"
    else
        echo "使用现有虚拟环境..."
        echo "要激活虚拟环境，请运行: source $VENV_NAME/bin/activate"
        exit 0
    fi
fi

# 创建虚拟环境
echo "正在创建虚拟环境 '$VENV_NAME'..."
python3 -m venv "$VENV_NAME"

# 激活虚拟环境
source "$VENV_NAME/bin/activate"

# 更新pip
echo "更新pip..."
pip install --upgrade pip

# 安装项目依赖
echo "安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告：未找到requirements.txt文件"
    exit 1
fi

# 安装face_recognition的系统依赖（Raspberry Pi OS/Debian）
echo "正在安装face_recognition所需的系统依赖..."
# 检查是否是root用户
if [ "$(id -u)" = "0" ]; then
    apt-get update
    # 先单独安装cmake，确保它被正确安装
    echo "安装cmake..."
    apt-get install -y cmake
    
    # 安装其他系统依赖
    apt-get install -y build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev libcap-dev
    
    # 尝试安装libtiff相关包（根据不同Linux发行版，包名可能有所不同）
    echo "尝试安装libtiff相关包..."
    apt-get install -y libtiff5 || apt-get install -y libtiff-dev || apt-get install -y libtiff-tools
    
    # 安装可能有助于dlib构建的额外依赖
    echo "安装额外的开发工具和库以帮助dlib构建..."
    apt-get install -y python3-dev git
    
    # 检查cmake是否正确安装
    if command -v cmake &> /dev/null; then
        echo "cmake已成功安装，版本：$(cmake --version)"
        echo "cmake路径：$(which cmake)"
    else
        echo "警告：cmake安装后无法找到，请手动将cmake添加到PATH中"
    fi
else
    echo "警告：需要root权限安装系统依赖，建议运行以下命令："
    echo "sudo apt-get update"
    echo "sudo apt-get install -y cmake"
    echo "sudo apt-get install -y build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev libcap-dev"
    echo "sudo apt-get install -y python3-dev git"
    echo "然后尝试安装libtiff相关包："
    echo "sudo apt-get install -y libtiff5 || sudo apt-get install -y libtiff-dev || sudo apt-get install -y libtiff-tools"
    echo ""
    echo "安装完成后，请验证cmake是否正确安装："
    echo "cmake --version"
    echo "如果找不到cmake命令，请检查是否将其添加到了PATH中"
fi

# 提示用户如何使用虚拟环境
echo "\n===== 虚拟环境设置完成 ====="
echo "要激活虚拟环境，请运行: source $VENV_NAME/bin/activate"
echo "要运行座位监控系统，请在激活虚拟环境后运行: python main.py"
echo "或者使用更新后的启动脚本: ./start_monitor.sh"