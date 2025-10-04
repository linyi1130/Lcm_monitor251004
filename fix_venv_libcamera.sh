#!/bin/bash

# 修复虚拟环境中libcamera模块访问问题的脚本

# 虚拟环境名称
VENV_NAME="seat_monitor_venv"

# 确保脚本在错误时退出
source_venv() {
    if [ -f "$VENV_NAME/bin/activate" ]; then
        echo "正在激活虚拟环境..."
        source "$VENV_NAME/bin/activate"
        return 0
    else
        echo "错误：找不到虚拟环境 '$VENV_NAME'"
        echo "请确保在项目根目录下运行此脚本，或者使用setup_venv.sh创建虚拟环境"
        return 1
    fi
}

fix_venv_config() {
    echo "\n===== 修复虚拟环境配置以访问系统Python模块 ====="
    
    # 检查虚拟环境配置文件
    VENV_CONFIG="$VENV_NAME/pyvenv.cfg"
    if [ -f "$VENV_CONFIG" ]; then
        echo "检查虚拟环境配置文件: $VENV_CONFIG"
        
        # 显示当前配置
        echo "当前配置内容："
        cat "$VENV_CONFIG"
        
        # 检查include-system-site-packages设置
        if ! grep -q "include-system-site-packages = true" "$VENV_CONFIG"; then
            echo "\n修改虚拟环境配置..."
            
            # 根据操作系统使用不同的sed语法
            if [[ "$(uname)" == "Darwin" ]]; then
                # MacOS
                sed -i '' 's/include-system-site-packages = false/include-system-site-packages = true/g' "$VENV_CONFIG"
            else
                # Linux
                sed -i 's/include-system-site-packages = false/include-system-site-packages = true/g' "$VENV_CONFIG"
            fi
            
            # 再次检查
            if grep -q "include-system-site-packages = true" "$VENV_CONFIG"; then
                echo "✓ 虚拟环境配置已成功更新！"
            else
                # 如果没有找到并替换，尝试直接添加
                echo "\n未找到include-system-site-packages设置，尝试添加..."
                echo "include-system-site-packages = true" >> "$VENV_CONFIG"
                if grep -q "include-system-site-packages = true" "$VENV_CONFIG"; then
                    echo "✓ 虚拟环境配置已成功添加！"
                else
                    echo "✗ 无法更新虚拟环境配置，请手动编辑文件："
                    echo "  $VENV_CONFIG"
                    echo "  添加或修改：include-system-site-packages = true"
                    return 1
                fi
            fi
        else
            echo "✓ 虚拟环境配置已经正确设置！"
        fi
    else
        echo "✗ 警告：未找到虚拟环境配置文件 '$VENV_CONFIG'"
        echo "  可能需要重新创建虚拟环境： ./setup_venv.sh"
        return 1
    fi
    return 0
}

test_libcamera() {
    echo "\n===== 测试libcamera模块访问 ====="
    
    # 尝试使用虚拟环境的Python导入libcamera
    TEST_SCRIPT="$(mktemp)"
    cat > "$TEST_SCRIPT" << EOL
import sys
print(f"Python解释器路径: {sys.executable}")
print(f"Python版本: {sys.version}")
try:
    import libcamera
    print("✓ libcamera模块导入成功！")
except ImportError as e:
    print(f"✗ libcamera模块导入失败: {str(e)}")
    print("系统Python模块路径可能未包含在虚拟环境中")
    print("请尝试重新创建虚拟环境： ./setup_venv.sh")
EOL
    
    # 使用虚拟环境的Python执行测试脚本
    if [ -d "$VENV_NAME" ]; then
        echo "使用虚拟环境的Python执行测试..."
        $VENV_NAME/bin/python "$TEST_SCRIPT"
    else
        echo "错误：虚拟环境不存在，无法执行测试"
    fi
    
    # 清理临时文件
    rm -f "$TEST_SCRIPT"
}

show_help() {
    echo "\n座位监控系统 - libcamera虚拟环境修复工具"
    echo "此工具帮助解决虚拟环境中无法导入libcamera模块的问题"
    echo "\n用法： ./fix_venv_libcamera.sh [选项]"
    echo "\n选项："
    echo "  --help, -h    显示帮助信息"
    echo "  --fix, -f     只修复虚拟环境配置"
    echo "  --test, -t    只测试libcamera模块访问"
    echo "  --all, -a     修复配置并测试（默认）"
    echo "\n注意：运行此脚本前请确保安装了所有系统依赖："
    echo "  sudo apt-get install -y python3-libcamera python3-kms++ libcamera-apps libcamera-dev"
}

# 主函数
main() {
    # 解析命令行参数
    ACTION="all"
    for arg in "$@"; do
        case $arg in
            --help|-h)
                show_help
                return 0
                ;;
            --fix|-f)
                ACTION="fix"
                ;;
            --test|-t)
                ACTION="test"
                ;;
            --all|-a)
                ACTION="all"
                ;;
            *)
                echo "未知选项：$arg"
                show_help
                return 1
                ;;
        esac
    done
    
    # 根据选择的操作执行相应的功能
    case $ACTION in
        fix)
            fix_venv_config
            ;;
        test)
            test_libcamera
            ;;
        all)
            fix_venv_config
            if [ $? -eq 0 ]; then
                test_libcamera
            fi
            ;;
    esac
    
    echo "\n===== 操作完成 ====="
    echo "如果问题仍然存在，请尝试以下操作："
    echo "1. 重新创建虚拟环境： ./setup_venv.sh"
    echo "2. 确保libcamera系统依赖已正确安装"
    echo "3. 查看 HELP_RUNNING_SCRIPTS.md 文件了解更多故障排除信息"
    return 0
}

# 执行主函数
main "$@"

# 退出脚本，返回相应的退出码
exit $?