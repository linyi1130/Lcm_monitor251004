# 如何正确运行脚本文件

根据文件权限信息（-rw-rw-r--），您的脚本文件目前没有执行权限，这就是为什么会遇到"command not found"错误。

## 解决方法

您有两种方式来运行这些脚本：

### 方法1：使用bash命令显式运行（推荐）
```bash
# 运行虚拟环境设置脚本
bash setup_venv.sh

# 运行系统启动脚本
bash start_monitor.sh

# 运行测试脚本
bash test_in_venv.sh
```

### 方法2：先添加执行权限，然后直接运行
```bash
# 为虚拟环境设置脚本添加执行权限
chmod +x setup_venv.sh
# 然后运行它
./setup_venv.sh

# 为系统启动脚本添加执行权限
chmod +x start_monitor.sh
# 然后运行它
./start_monitor.sh

# 为测试脚本添加执行权限
chmod +x test_in_venv.sh
# 然后运行它
./test_in_venv.sh
```

## 关于文件权限的说明

在Linux/Mac系统中，文件权限用10个字符表示，例如：`-rw-rw-r--`

- 第一个字符表示文件类型（`-`表示普通文件）
- 接下来的三个字符表示文件所有者的权限（`rw-`表示可读可写但不可执行）
- 再接下来的三个字符表示文件所属组的权限（`rw-`表示可读可写但不可执行）
- 最后三个字符表示其他用户的权限（`r--`表示只读）

要运行脚本文件，您需要：
1. 使用bash命令显式运行它，或者
2. 为文件添加执行权限（使用chmod +x命令）

## 快速开始

如果您想快速设置和运行座位监控系统，建议使用以下命令：
```bash
# 使用bash运行虚拟环境设置脚本
bash setup_venv.sh

# 使用bash运行系统启动脚本
bash start_monitor.sh
```

如果您想运行测试脚本（在没有摄像头的环境中）：
```bash
# 使用bash运行测试脚本
bash test_in_venv.sh
```