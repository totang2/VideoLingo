#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import threading
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

def start_coordinator():
    """启动协调器服务"""
    try:
        from core.coordinator import app, socketio
        logger.info("Starting coordinator service on 0.0.0.0:8502")
        socketio.run(app, host='0.0.0.0', port=8502, debug=False)
    except Exception as e:
        logger.error(f"Failed to start coordinator service: {e}")
        raise

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
    from core.config_utils import load_key

    # 创建协调器
    coordinator = Coordinator()
    
    # 根据配置决定是否启动协调器服务
    if load_key('distributed_download.enabled', False):
        logger.info("Distributed download is enabled, starting coordinator service")
        # 在后台线程中启动协调器服务
        coordinator_thread = threading.Thread(
            target=start_coordinator,
            daemon=True
        )
        coordinator_thread.start()
    else:
        logger.info("Distributed download is disabled, coordinator service will not start")
    
    # 使用 streamlit run 命令启动应用
    st_script = os.path.join(app_dir, "st.py")
    if not os.path.exists(st_script):
        logger.error(f"错误：找不到 {st_script}")
        sys.exit(1)
    
    # 构建 streamlit 命令
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        st_script,
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]
    
    # 运行命令
    try:
        subprocess.run(cmd)
    except Exception as e:
        logger.error(f"Failed to start Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 