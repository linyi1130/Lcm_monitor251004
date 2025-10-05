#!/bin/bash

# 启动Web服务的脚本

# 设置工作目录为脚本所在目录
cd "$(dirname "$0")"

# 安装依赖
if [ -f "requirements.txt" ]; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 检查是否有参数
if [ "$1" = "--enable-remote" ]; then
    echo "启用外网访问模式..."
    python3 web_server.py --enable-remote
elif [ "$1" = "--auth" ]; then
    echo "启用认证模式..."
    python3 web_server.py --auth
elif [ "$1" = "--debug" ]; then
    echo "启用调试模式..."
    python3 web_server.py --debug
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "使用方法: $0 [选项]"
    echo "选项:"
    echo "  --enable-remote   启用外网访问"
    echo "  --auth            启用基本认证"
    echo "  --debug           启用调试模式"
    echo "  --help, -h        显示帮助信息"
    echo "  无参数             启动内网模式（默认）"
else
    echo "启动Web服务（内网模式）..."
    python3 web_server.py
fi