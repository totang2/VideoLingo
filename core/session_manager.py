import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st
from core.config_utils import load_key, update_key

class SessionManager:
    """管理用户会话状态和资源"""
    
    def __init__(self):
        # 初始化会话状态
        if 'is_authenticated' not in st.session_state:
            st.session_state.is_authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.created_at = time.time()
            
        self.is_authenticated = st.session_state.is_authenticated
        self.user_id = st.session_state.user_id
        self.username = st.session_state.username
        
        if self.is_authenticated and self.user_id:
            self.user_dir = Path(f"output/user_{self.user_id}")
            self.user_dir.mkdir(parents=True, exist_ok=True)
            # 清理过期会话
            self.cleanup_old_sessions()
    
    def login(self, username: str, password: str) -> bool:
        """用户登录"""
        # 从配置文件加载用户信息
        users = load_key('users') or {}
        
        if username in users and users[username]['password'] == password:
            # 登录成功
            st.session_state.is_authenticated = True
            st.session_state.user_id = str(uuid.uuid4())
            st.session_state.username = username
            st.session_state.created_at = time.time()
            
            # 更新会话状态
            self.is_authenticated = True
            self.user_id = st.session_state.user_id
            self.username = username
            
            # 创建用户目录
            self.user_dir = Path(f"output/user_{self.user_id}")
            self.user_dir.mkdir(parents=True, exist_ok=True)
            
            return True
        return False
    
    def logout(self):
        """用户登出"""
        st.session_state.is_authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        self.is_authenticated = False
        self.user_id = None
        self.username = None
    
    @property
    def output_dir(self) -> Optional[Path]:
        """获取用户专属的输出目录"""
        if not self.is_authenticated:
            return None
        return self.user_dir
        
    def get_user_file(self, filename: str) -> Optional[Path]:
        """获取用户专属文件路径"""
        if not self.is_authenticated:
            return None
        return self.user_dir / filename
        
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理过期的会话目录"""
        if not self.is_authenticated:
            return
            
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