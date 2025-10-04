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

# 安装face_recognition的系统依赖（Raspberry Pi OS/Debian）
echo "正在安装face_recognition所需的系统依赖..."

# 执行Raspberry Pi OS特定的cmake安装和验证
install_cmake_rpi() {
    # 首先确保apt包列表是最新的
    sudo apt-get update -y
    
    # 移除可能存在的损坏的cmake副本（尤其是来自Python包管理器的）
    echo "检查并移除可能损坏的cmake副本..."
    sudo apt-get purge -y cmake
    sudo rm -rf /usr/local/bin/cmake /usr/local/lib/cmake
    sudo rm -rf $(python3 -c "import sys; print(sys.prefix)")/bin/cmake
    
    # 重新安装官方的cmake包
    echo "安装官方的cmake包..."
    sudo apt-get install -y cmake
    
    # 安装其他系统依赖
    echo "安装dlib构建所需的开发工具和库..."
    sudo apt-get install -y build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev libcap-dev
    
    # 安装libcamera相关依赖（支持Picamera2）
    echo "安装libcamera系统依赖（支持Picamera2）..."
    sudo apt-get install -y python3-libcamera python3-kms++
    sudo apt-get install -y python3-pyqt5 python3-prctl libatlas-base-dev ffmpeg python3-pip
    sudo apt-get install -y libcamera-apps libcamera-dev
    
    # 安装libtiff相关包
    echo "安装libtiff相关包..."
    sudo apt-get install -y libtiff5 || sudo apt-get install -y libtiff-dev || sudo apt-get install -y libtiff-tools
    
    # 安装额外的开发工具
    echo "安装额外的开发工具..."
    sudo apt-get install -y python3-dev git python3-pip
    
    # 验证cmake是否正确安装
    echo "验证cmake安装..."
    if command -v cmake &> /dev/null; then
        echo "✓ cmake已成功安装"        
        echo "版本: $(cmake --version)"
        echo "路径: $(which cmake)"
        
        # 显示cmake的详细信息
        echo "CMake详细信息:"        
        sudo dpkg -l | grep cmake
    else
        echo "✗ 警告：cmake安装后无法找到！"
        echo "请尝试注销并重新登录，或手动将cmake添加到PATH中："
        echo "export PATH=$PATH:/usr/bin"
        echo "然后验证：cmake --version"
        return 1
    fi
    return 0
}

# 检查是否是root用户
if [ "$(id -u)" = "0" ]; then
    install_cmake_rpi
else
    echo "需要root权限安装系统依赖，正在执行Raspberry Pi OS特定的安装步骤..."
    # 即使不是root用户，也提供详细的安装命令指导
    echo "\n请在终端中运行以下命令以安装所有必要的依赖："
    echo "\n# 完整的Raspberry Pi OS依赖安装命令"    
    echo "sudo apt-get update -y"
    echo "sudo apt-get purge -y cmake"
    echo "sudo rm -rf /usr/local/bin/cmake /usr/local/lib/cmake"
    echo "sudo rm -rf $(python3 -c "import sys; print(sys.prefix)")/bin/cmake || true"
    echo "sudo apt-get install -y cmake build-essential libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev libcap-dev"
    echo "sudo apt-get install -y python3-dev git python3-pip libtiff5"
    echo "\n# 验证cmake安装"
    echo "cmake --version"
    echo "which cmake"
    echo "\n# 重要提示：安装完成后请重新运行此脚本"
fi

# 创建虚拟环境 - 并允许访问系统Python模块
echo "正在创建虚拟环境 '$VENV_NAME'..."
python3 -m venv "$VENV_NAME"

# 允许虚拟环境访问系统Python模块
echo "配置虚拟环境以允许访问系统Python模块..."
# 创建或修改pyvenv.cfg文件，设置include-system-site-packages为true
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

# 安装项目依赖
echo "安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告：未找到requirements.txt文件"
    exit 1
fi

# 提示用户如何使用虚拟环境
echo "\n===== 虚拟环境设置完成 ====="
echo "要激活虚拟环境，请运行: source $VENV_NAME/bin/activate"
echo "要运行座位监控系统，请在激活虚拟环境后运行: python main.py"
echo "或者使用更新后的启动脚本: ./start_monitor.sh"