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