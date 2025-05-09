import sys
import os

with open("env_info.txt", "w") as f:
    f.write(f"Python版本: {sys.version}\n")
    f.write(f"Python可执行文件: {sys.executable}\n")
    f.write(f"系统平台: {sys.platform}\n")
    f.write(f"工作目录: {os.getcwd()}\n")

print("信息已保存到env_info.txt") 