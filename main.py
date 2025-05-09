import tkinter as tk
import sys
import traceback
from gui import ScraperApp

def show_error(exc_type, exc_value, exc_traceback):
    """显示未捕获的异常"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"发生错误:\n{error_msg}")
    try:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write(f"异常: {error_msg}\n\n")
    except:
        pass

if __name__ == "__main__":
    # 设置未捕获异常处理器
    sys.excepthook = show_error
    
    try:
        root = tk.Tk()
        app = ScraperApp(root)
        root.mainloop()
    except Exception as e:
        show_error(type(e), e, e.__traceback__)