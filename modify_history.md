# 多用户支持
我来帮你实现多用户同时访问的支持。主要需要做以下几个改进：

1. 使用 Streamlit 的 session state 来管理每个用户的会话状态
2. 为每个用户创建独立的输出目录
3. 添加用户标识和并发控制

让我们开始修改代码：

1. 首先创建一个用户会话管理模块 `core/session_manager.py`:

```python
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
```

2. 修改 `st_components/bilibili_upload_section.py` 以支持多用户：

```python
import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_utils import load_key, update_key
from core.bilibili_upload import BilibiliUploader
from translations.translations import translate as t

def bilibili_upload_section():
    st.header(t("d. Upload to Bilibili"))
    with st.container(border=True):
        st.markdown(f"""
        <p style='font-size: 20px;'>
        {t("Upload your translated video to Bilibili. You'll need:")}
        <p style='font-size: 20px;'>
            1. {t("Bilibili account credentials")}<br>
            2. {t("Video title and description")}<br>
            3. {t("Video tags and category")}
        """, unsafe_allow_html=True)

        # Bilibili credentials section
        with st.expander(t("Bilibili Account Settings"), expanded=True):
            cookie = config_input(t("Bilibili Cookie"), "bilibili.cookie", 
                                help=t("Your Bilibili login cookie"))
            sessdata = config_input(t("SESSDATA"), "bilibili.sessdata", 
                                  help=t("Your Bilibili SESSDATA"))
            bili_jct = config_input(t("bili_jct"), "bilibili.bili_jct", 
                                  help=t("Your Bilibili bili_jct token"))

        # Video details section
        st.subheader(t("Video Details"))
        title = st.text_input(t("Video Title"), value="", 
                            help=t("Enter the title for your video"))
        description = st.text_area(t("Video Description"), value="", 
                                 help=t("Enter the description for your video"))
        tags = st.text_input(t("Tags (comma separated)"), value="", 
                           help=t("Enter tags separated by commas"))
        
        # Category selection
        categories = {
            "知识": 201,    # Knowledge
            "科技": 188,    # Technology
            "生活": 160,    # Life
            "娱乐": 5,      # Entertainment
            "音乐": 3,      # Music
            "游戏": 4,      # Games
        }
        category = st.selectbox(t("Category"), options=list(categories.keys()))

        # Upload button
        if st.button(t("Upload to Bilibili"), use_container_width=True):
            if not os.path.exists("output/output_dub.mp4"):
                st.error(t("No video file found. Please complete the dubbing process first."))
                return

            if not all([cookie, sessdata, bili_jct, title, description, tags]):
                st.error(t("Please fill in all required fields"))
                return

            try:
                with st.spinner(t("Uploading to Bilibili...")):
                    uploader = BilibiliUploader(
                        sessdata=sessdata,
                        bili_jct=bili_jct,
                        cookie=cookie
                    )
                    
                    # Convert tags string to list
                    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    
                    # Upload video
                    response = uploader.upload_video(
                        video_path="output/output_dub.mp4",
                        title=title,
                        description=description,
                        tags=tag_list,
                        tid=categories[category]
                    )
                    
                    # Show success message with video link
                    if response.get('code') == 0:
                        video_id = response.get('data', {}).get('aid')
                        video_url = f"https://www.bilibili.com/video/{video_id}"
                        st.success(f"{t('Video uploaded successfully!')} [View video]({video_url})")
                    else:
                        st.error(f"{t('Upload failed:')} {response.get('message')}")
                        
            except Exception as e:
                st.error(f"{t('Error during upload:')} {str(e)}")

def config_input(label, key, help=None):
    """Generic config input handler"""
    val = st.text_input(label, value=load_key(key), help=help, type="password")
    if val != load_key(key):
        update_key(key, val)
    return val
```