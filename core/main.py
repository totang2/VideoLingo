#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
from pathlib import Path

def main():
    # 获取应用程序根目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        app_dir = Path(sys._MEIPASS)
    else:
        # 如果是开发环境
        app_dir = Path(__file__).parent.parent

    # 设置工作目录
    os.chdir(app_dir)

    # 导入必要的模块
    from core.coordinator import Coordinator
    from core.config_utils import ConfigManager

    # 初始化配置
    config_manager = ConfigManager()
    config = config_manager.load_config()

    # 创建协调器
    coordinator = Coordinator(config)
    
    # 使用 streamlit run 命令启动应用
    st_script = os.path.join(app_dir, "st.py")
    if not os.path.exists(st_script):
        print(f"错误：找不到 {st_script}")
        sys.exit(1)
    
    # 构建 streamlit 命令
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        st_script,
        "--server.port=8501",
        "--server.address=127.0.0.1"
    ]
    
    # 运行命令
    subprocess.run(cmd)

if __name__ == "__main__":
    main() 