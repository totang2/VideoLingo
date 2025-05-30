import streamlit as st
import os
from pathlib import Path
import logging
import sys
import subprocess

logger = logging.getLogger('streamlit')

def update_ui_after_download(video_path: str):
    """Update Streamlit UI state after video download
    
    Args:
        video_path: Path to the downloaded video file
    """
    try:
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file does not exist: {video_path}")
            st.error("视频文件不存在")
            return
            
        # 更新会话状态
        st.session_state['video_path'] = video_path
        st.session_state['current_step'] = 'download'
        st.session_state['download_completed'] = True  # 标记下载完成
        st.session_state['video_loaded'] = True
        
        # 显示视频
        st.video(video_path)
        
        logger.info(f"UI state updated for video: {video_path}")
    except Exception as e:
        logger.error(f"Failed to update UI state: {e}")
        raise 

def main():
    if not login_section():
        st.stop()
    with st.sidebar:
        page_setting()

    if st.session_state.get('download_completed'):
        st.success(f"Video downloaded successfully: {st.session_state['video_path']}")
        st.session_state['download_completed'] = False
        text_processing_section()
        audio_processing_section()
    else:
        download_video_section()
        text_processing_section()
        audio_processing_section()

if __name__ == "__main__":
    main() 