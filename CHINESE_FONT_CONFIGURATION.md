# 树莓派5 texie系统中文字体配置指南

## 问题说明
在树莓派5 texie系统上运行Python应用程序（如seat_monitor.py）时，可能会遇到中文无法正常显示的问题。这通常是因为系统缺少中文字体或程序无法正确加载中文字体。

## 解决方案

### 步骤1：安装中文字体

1. 运行我们提供的脚本安装常用中文字体：
```bash
sudo ./install_chinese_fonts.sh
```

2. 脚本会自动安装以下中文字体包：
   - 文泉驿正黑 (fonts-wqy-zenhei)
   - 文泉驿微米黑 (fonts-wqy-microhei)
   - Noto CJK 字体 (fonts-noto-cjk)
   - Droid 回退字体 (fonts-droid-fallback)

3. 安装完成后，重启系统以确保字体生效：
```bash
sudo reboot
```

### 步骤2：验证字体安装

安装完成后，可以使用以下命令检查字体是否安装成功：
```bash
sudo fc-list :lang=zh -f "%{file}\n"
```

如果看到类似下面的输出，说明中文字体已成功安装：
```
/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
/usr/share/fonts/truetype/wqy/wqy-microhei.ttc
/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf
```

### 步骤3：程序字体配置

我们已经优化了seat_monitor.py中的字体加载逻辑，使其：

1. 优先使用树莓派5 texie系统上常见的中文字体
2. 包含更多Linux系统上常用的字体路径
3. 添加了更多通用字体名称选项
4. 增强了文本处理，确保中文内容以正确的Unicode格式处理

## 常见问题排查

### 1. 如果中文仍然无法显示

- 确认是否已重启系统
- 检查seat_monitor.py中的字体路径是否与系统中实际安装的字体路径一致
- 查看日志文件中的字体加载信息：`grep "字体" logs/*.log`

### 2. 找不到特定字体文件

如果系统中找不到特定的字体文件，可以尝试：
```bash
# 搜索系统中的中文字体
sudo find /usr/share/fonts -name "*.ttf" -o -name "*.ttc"
```

然后在seat_monitor.py中更新字体路径。

### 3. 其他解决方法

- 确保系统语言设置为中文：`sudo raspi-config` → `Localisation Options` → `Locale` → 选择`zh_CN.UTF-8`
- 增大字体加载时的日志级别，在seat_monitor.py中设置`debug=True`

## 程序中的关键字体配置

在seat_monitor.py文件中，字体加载逻辑位于`draw_overlay`方法中：

```python
# 字体加载优先级配置
font_path_candidates = [
    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # 优先使用系统已确认存在的字体
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    # 更多字体路径...
]
```

如果需要，可以根据您系统中实际安装的字体调整这些路径的顺序。

## 总结

解决树莓派5 texie系统上的中文显示问题主要需要两个步骤：
1. 安装中文字体包
2. 确保程序能够正确加载这些字体

我们提供的脚本和程序优化应该能够解决大部分中文显示问题。如果您遇到特殊情况，请参考常见问题排查部分。