import streamlit as st
import os, sys, shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_utils import load_key, update_key
from core.step1_ytdlp import download_video_ytdlp, find_video_files
from core.distributed_download import create_downloader
from time import sleep
import re
import subprocess
from translations.translations import translate as t

OUTPUT_DIR = "output"

def set_download_video_finished():
    # create a file in the output directory
    with open(os.path.join(OUTPUT_DIR, "download_video_finished"), "w") as f:
        f.write("finished")
        
def check_download_video_finished():
    # check if the file exists
    if os.path.exists(os.path.join(OUTPUT_DIR, "download_video_finished")):
        return True
    return False

def download_video_section():
    st.header(t("a. Download or Upload Video"))
    with st.container(border=True):
        try:
            video_file = find_video_files()
            st.video(video_file)
            if st.button(t("Delete and Reselect"), key="delete_video_button"):
                os.remove(video_file)
                if os.path.exists(OUTPUT_DIR):
                    shutil.rmtree(OUTPUT_DIR)
                sleep(1)
                st.rerun()
            return True
        except:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                url = st.text_input(t("Enter YouTube link:"))
            with col2:
                res_dict = {
                    "360p": "360",
                    "1080p": "1080",
                    "Best": "best"
                }
                target_res = load_key("ytb_resolution")
                res_options = list(res_dict.keys())
                default_idx = list(res_dict.values()).index(target_res) if target_res in res_dict.values() else 0
                res_display = st.selectbox(t("Resolution"), options=res_options, index=default_idx)
                res = res_dict[res_display]
            with col3:
                # 添加浏览器选择
                browser_options = {
                    "None": None,
                    "Chrome": "chrome",
                    "Firefox": "firefox",
                    "Safari": "safari",
                    "Edge": "edge",
                    "Opera": "opera",
                    "Brave": "brave",
                    "Vivaldi": "vivaldi"
                }
                browser = st.selectbox(
                    t("Browser for Cookies"),
                    options=list(browser_options.keys()),
                    index=0,  # 默认选择 "None"
                    help=t("Select browser to get cookies from")
                )
                browser = browser_options[browser]
                
            if st.button(t("Download Video"), key="download_button", use_container_width=True):
                if url:
                    with st.spinner("Downloading video..."):
                        # 检查是否启用分布式下载
                        distributed_config = load_key("distributed_download", {})
                        if distributed_config.get("enabled", False):
                            # 使用分布式下载
                            downloader = create_downloader(distributed_config.get("node_id"))
                            
                            # 注册节点
                            if not downloader.register_node():
                                st.error("Failed to register with coordinator")
                                return False
                            
                            # 尝试下载
                            success = downloader.download_video(url, resolution=res, cutoff_time=load_key("cutoff_time"), browser=browser)
                            
                            if success:
                                set_download_video_finished()
                                st.rerun()
                            else:
                                st.warning("Download failed, task has been reassigned to another node. Please wait...")
                                # 等待任务完成
                                max_retries = distributed_config.get("max_retries", 30)
                                retry_interval = distributed_config.get("retry_interval", 1)
                                retry_count = 0
                                while retry_count < max_retries:
                                    if check_download_video_finished():
                                        st.rerun()
                                        break
                                    sleep(retry_interval)
                                    retry_count += 1
                                if retry_count >= max_retries:
                                    st.error("Download failed after multiple attempts")
                        else:
                            # 使用普通下载
                            try:
                                download_video_ytdlp(url, resolution=res, cutoff_time=load_key("cutoff_time"), browser=browser)
                                if find_video_files():
                                    set_download_video_finished()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Download failed: {str(e)}")

            uploaded_file = st.file_uploader(t("Or upload video"), type=load_key("allowed_video_formats") + load_key("allowed_audio_formats"))
            if uploaded_file:
                if os.path.exists(OUTPUT_DIR):
                    shutil.rmtree(OUTPUT_DIR)
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                
                raw_name = uploaded_file.name.replace(' ', '_')
                name, ext = os.path.splitext(raw_name)
                clean_name = re.sub(r'[^\w\-_\.]', '', name) + ext.lower()
                    
                with open(os.path.join(OUTPUT_DIR, clean_name), "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if ext.lower() in load_key("allowed_audio_formats"):
                    convert_audio_to_video(os.path.join(OUTPUT_DIR, clean_name))
                    
                    # set the download video finished
                    set_download_video_finished()
                st.rerun()
            else:
                return False

def convert_audio_to_video(audio_file: str) -> str:
    output_video = os.path.join(OUTPUT_DIR, 'black_screen.mp4')
    if not os.path.exists(output_video):
        print(f"🎵➡️🎬 Converting audio to video with FFmpeg ......")
        ffmpeg_cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=640x360', '-i', audio_file, '-shortest', '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', output_video]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"🎵➡️🎬 Converted <{audio_file}> to <{output_video}> with FFmpeg\n")
        # delete audio file
        os.remove(audio_file)
    return output_video
