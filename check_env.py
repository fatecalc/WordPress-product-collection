import sys
import os
import platform
import pkg_resources
import tkinter

# 收集系统信息
env_info = []
env_info.append(f"Python版本: {sys.version}")
env_info.append(f"Python路径: {sys.executable}")
env_info.append(f"系统平台: {sys.platform}")
env_info.append(f"系统详情: {platform.platform()}")
env_info.append(f"处理器: {platform.processor()}")
env_info.append(f"当前工作目录: {os.getcwd()}")
env_info.append(f"Python路径列表: {os.pathsep.join(sys.path)}")

# 检查必要模块
env_info.append("\n已安装包:")
for pkg in pkg_resources.working_set:
    env_info.append(f"  {pkg.key} {pkg.version}")

# 检查tkinter
env_info.append(f"\nTkinter版本: {tkinter.TkVersion}")
env_info.append(f"Tkinter库路径: {tkinter.__file__}")

# 保存到文件
with open("environment_info.txt", "w", encoding="utf-8") as f:
    for line in env_info:
        f.write(line + "\n")

print("环境信息已保存到 environment_info.txt") 