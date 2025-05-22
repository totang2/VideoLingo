import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any
import streamlit as st

class SessionManager:
    """管理用户会话状态和资源"""
    
    def __init__(self):
        if 'user_id' not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.created_at = time.time()
            
        self.user_id = st.session_state.user_id
        self.user_dir = Path(f"output/user_{self.user_id}")
        self.user_dir.mkdir(parents=True, exist_ok=True)
        
        # 清理过期会话
        self.cleanup_old_sessions()
        
    @property
    def output_dir(self) -> Path:
        """获取用户专属的输出目录"""
        return self.user_dir
        
    def get_user_file(self, filename: str) -> Path:
        """获取用户专属文件路径"""
        return self.user_dir / filename
        
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理过期的会话目录"""
        current_time = time.time()
        output_dir = Path("output")
        
        for user_dir in output_dir.glob("user_*"):
            try:
                # 从目录名中提取时间戳
                created_at = float(user_dir.name.split("_")[1])
                if current_time - created_at > max_age_hours * 3600:
                    # 删除过期目录
                    import shutil
                    shutil.rmtree(user_dir)
            except (ValueError, IndexError):
                continue 