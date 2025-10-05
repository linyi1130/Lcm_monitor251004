#!/bin/bash

# 树莓派5 texie系统安装中文字体脚本
# 用于解决Python PIL库中文显示问题

# 确保以root权限运行
if [ "$EUID" -ne 0 ]
  then echo "请以root权限运行此脚本: sudo ./install_chinese_fonts.sh"
  exit
fi

# 更新软件源
echo "更新系统软件源..."
sudo apt update && sudo apt upgrade -y

# 安装中文字体
# 文泉驿正黑和微米黑是常用的开源中文字体，支持PIL中文显示
echo "安装中文字体包..."
sudo apt install -y fonts-wqy-zenhei fonts-wqy-microhei ttf-wqy-zenhei
sudo apt install -y fonts-noto-cjk fonts-noto-cjk-extra

# 安装Droid字体（已在程序中使用的字体）
echo "安装Droid中文字体..."
sudo apt install -y fonts-droid-fallback

# 复制字体到PIL可能使用的位置
echo "更新字体缓存..."
sudo fc-cache -f -v

# 提示用户设置系统语言（可选）
echo "\n中文字体已安装完成！"
echo "\n若需设置系统语言为中文，请运行：sudo raspi-config"
echo "然后选择 Localisation Options -> Locale" 
echo "使用空格键勾选 zh_CN.UTF-8 UTF-8，Tab键切换选项"
echo "\n安装完成后请重启系统以确保字体生效：sudo reboot"
echo "\n注意：对于Python程序中的中文显示，您可能需要修改seat_monitor.py中的字体路径"
echo "建议使用：/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc 或 /usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"