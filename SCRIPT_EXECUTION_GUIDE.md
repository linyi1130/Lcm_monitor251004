# 脚本执行指南

## 解决 "command not found" 错误

如果在尝试运行 `sudo ./install_chinese_fonts.sh` 时出现 "command not found" 错误，这通常是因为脚本缺少执行权限或没有正确的 shebang 行。

### 修复方法

1. **添加执行权限**（已经修复，但作为参考）：
   ```bash
   chmod +x install_chinese_fonts.sh
   ```

2. **正确运行脚本**：
   ```bash
   sudo ./install_chinese_fonts.sh
   ```
   或者使用 bash 显式运行（即使没有执行权限也可以）：
   ```bash
   sudo bash install_chinese_fonts.sh
   ```

## 系统兼容性说明

- **树莓派5 texie系统**：这是脚本的主要设计目标，包含了必要的软件包安装命令。
- **macOS系统**：脚本已添加了系统检测逻辑，会提示这是为Linux设计的脚本，并提供替代方案。

## 在macOS上安装中文字体

在macOS系统上，建议通过以下方式安装中文字体：

1. 打开 **系统偏好设置** > **字体管理**
2. 点击 **+** 按钮添加字体文件
3. 常用中文字体可以从官方网站下载，如文泉驿、思源黑体等

## 字体验证

安装完成后，可以使用以下命令验证字体是否正确安装：

```bash
# 在树莓派上检查中文字体
fc-list :lang=zh

# 查看特定字体文件是否存在
ls -la /usr/share/fonts/truetype/wqy/
ls -la /usr/share/fonts/truetype/droid/
```

## 在Python中使用中文字体

如果您的Python程序仍无法正确显示中文，请检查以下几点：

1. 确保程序中使用的字体路径是正确的
2. 在seat_monitor.py中，我们已经添加了常用中文字体的路径，包括：
   - /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
   - /usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf
   - /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

3. 可以使用test_chinese_fonts.py脚本来测试字体显示：
   ```bash
   python test_chinese_fonts.py
   ```

## 常见问题

- **脚本权限问题**：确保使用sudo以管理员权限运行
- **软件包不可用**：可能需要更新软件源或检查网络连接
- **字体不生效**：安装完成后重启系统通常可以解决此问题