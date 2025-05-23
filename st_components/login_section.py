import streamlit as st
from core.session_manager import SessionManager
from translations.translations import translate as t
from core.config_utils import load_key, update_key

def login_section():
    """登录组件"""
    session_manager = SessionManager()
    
    # 如果已经登录，显示用户信息和登出按钮
    if session_manager.is_authenticated:
        # 使用自定义CSS美化已登录状态
        st.markdown("""
        <style>
        .user-info {
            background-color: rgba(248, 249, 250, 0.9);
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid #e9ecef;
            backdrop-filter: blur(10px);
        }
        .welcome-text {
            color: #2c3e50;
            font-size: 1.1rem;
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 添加工具栏
        st.markdown(f"""
        <div class="user-info">
            <div class="welcome-text">👋 {t('Welcome')}, {session_manager.username}!</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 登出按钮
        if st.button("登出", key="logout-button", type="secondary", use_container_width=False):
            session_manager.logout()
            st.rerun()
        
        # 添加设置选项
        st.markdown("""
        <div class="settings-box">
            <p style='margin: 0; color: #2c3e50; font-size: 0.9rem; font-weight: 500;'>⚙️ 处理设置</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 自动执行选项
        auto_execute = st.checkbox(
            "全自动处理",
            value=load_key('auto_execute') or False,
            help="视频下载后将自动执行所有处理步骤，无需手动点击"
        )
        
        # 保存设置
        if auto_execute != load_key('auto_execute'):
            update_key('auto_execute', auto_execute)
        
        return True
    
    # 登录表单样式
    st.markdown("""
    <style>
    .main {
        background-image: url('https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        height: 100%;
        padding: 1rem 0;
        margin: -1rem 0;
    }
    .login-container {
        max-width: 360px;
        margin: 0 auto;
        padding: 1.5rem;
        background-color: rgba(248, 249, 250, 0.9);
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(233, 236, 239, 0.8);
        backdrop-filter: blur(10px);
    }
    .login-title {
        text-align: center;
        color: #2c3e50;
        font-size: 1.75rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    .login-subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    .stForm {
        background-color: transparent !important;
    }
    .stButton>button {
        background-color: #2c3e50;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #34495e;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .stTextInput>div>div>input {
        border-radius: 6px;
        border: 1px solid #e9ecef;
        padding: 0.5rem;
        background-color: #ffffff !important;
        color: #2c3e50 !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: #2c3e50;
        box-shadow: 0 0 0 1px #2c3e50;
    }
    .stTextInput>div>div>input::placeholder {
        color: #adb5bd !important;
    }
    .info-box {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 8px;
        padding: 0.75rem;
        margin-top: 1rem;
        border: 1px solid rgba(233, 236, 239, 0.8);
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 登录表单容器
    st.markdown("""
    <div class="main">
        <div class="login-container">
            <div class="login-title">VideoLingo</div>
            <div class="login-subtitle">请登录以继续使用</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 登录表单
    with st.container():
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input(t("Username"), placeholder="请输入用户名")
            password = st.text_input(t("Password"), type="password", placeholder="请输入密码")
            submit = st.form_submit_button(t("Login"), use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("请输入用户名和密码")
                elif session_manager.login(username, password):
                    st.success(t("Login successful!"))
                    st.rerun()
                else:
                    st.error(t("Invalid username or password"))
    
    return False 