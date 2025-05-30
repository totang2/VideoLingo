import streamlit as st
import os, sys, shutil
import re
import pandas as pd
from st_components.imports_and_utils import *
from core.config_utils import load_key
from core.language_utils import normalize_language
from st_components.login_section import login_section

# SET PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] += os.pathsep + current_dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="VideoLingo", page_icon="docs/logo.svg")

# 定义常量
OUTPUT_DIR = "output"
INPUT_VIDEO = os.path.join(OUTPUT_DIR, "input.mp4")
SUB_VIDEO = os.path.join(OUTPUT_DIR, "output_sub.mp4")
DUB_VIDEO = os.path.join(OUTPUT_DIR, "output_dub.mp4")

# 初始化会话状态
if 'processing_state' not in st.session_state:
    st.session_state.processing_state = {
        'video_ready': False,
        'subtitle_ready': False,
        'audio_ready': False
    }

def set_subtitle_ready():
    # create a file in the output directory
    with open(os.path.join(OUTPUT_DIR, "subtitle_ready"), "w") as f:
        f.write("finished")
        
def check_subtitle_ready():
    # check if the file exists
    if os.path.exists(os.path.join(OUTPUT_DIR, "subtitle_ready")):
        return True
    return False

def set_audio_ready(is_ready=True):
    if is_ready:
        # create a file in the output directory
        with open(os.path.join(OUTPUT_DIR, "audio_ready"), "w") as f:
            f.write("finished")
    else:
        # delete the file
        if os.path.exists(os.path.join(OUTPUT_DIR, "audio_ready")):
            os.remove(os.path.join(OUTPUT_DIR, "audio_ready"))
        
def check_audio_ready():
    # check if the file exists
    if os.path.exists(os.path.join(OUTPUT_DIR, "audio_ready")):
        return True
    return False

def auto_execute(step):
    if load_key("auto_execute"):
        if step == "text":
            if check_download_video_finished():
                return True
        elif step == "audio":
            if check_subtitle_ready():
                return True
        elif step == "bilibili":
            pass
        
    return False

def text_processing_section():
    st.header(t("b. Translate and Generate Subtitles"))
    with st.container(border=True):
        st.markdown(f"""
        <p style='font-size: 20px;'>
        {t("This stage includes the following steps:")}
        <p style='font-size: 20px;'>
            1. {t("WhisperX word-level transcription")}<br>
            2. {t("Sentence segmentation using NLP and LLM")}<br>
            3. {t("Summarization and multi-step translation")}<br>
            4. {t("Cutting and aligning long subtitles")}<br>
            5. {t("Generating timeline and subtitles")}<br>
            6. {t("Merging subtitles into the video")}
        """, unsafe_allow_html=True)

        if not os.path.exists(SUB_VIDEO):
            if auto_execute("text") or st.button(t("Start Processing Subtitles"), key="text_processing_button"):
                process_text()
                set_subtitle_ready()
                st.rerun()
        else:
            if load_key("burn_subtitles"):
                st.video(SUB_VIDEO)
            download_subtitle_zip_button(text=t("Download All Srt Files"))
            
            if st.button(t("Archive to 'history'"), key="cleanup_in_text_processing"):
                cleanup()
                st.rerun()
            return True

def process_text():
    with st.spinner(t("Using Whisper for transcription...")):
        step2_whisperX.transcribe()
    with st.spinner(t("Splitting long sentences...")):  
        step3_1_spacy_split.split_by_spacy()
        # todo detected language is same, no need to split by meaning
        step3_2_splitbymeaning.split_sentences_by_meaning()
    
    # 检查源语言和目标语言是否相同
    src_language = normalize_language(load_key("whisper.detected_language"))
    target_language = normalize_language(load_key("target_language"))
    
    print(f"src_language: {src_language}, target_language: {target_language}")
    
    if src_language != target_language:
        with st.spinner(t("Summarizing and translating...")):
            step4_1_summarize.get_summary()
            if load_key("pause_before_translate"):
                input(t("⚠️ PAUSE_BEFORE_TRANSLATE. Go to `output/log/terminology.json` to edit terminology. Then press ENTER to continue..."))
            step4_2_translate_all.translate_all()
    else:
        st.info(t("Source and target languages are the same, fake translation..."))
        step4_1_summarize.get_summary()
        from core.step4_2_translate_all_dummy import translate_all as translate_all_dummy
        translate_all_dummy()
    
    with st.spinner(t("Processing and aligning subtitles...")): 
        step5_splitforsub.split_for_sub_main()
        step6_generate_final_timeline.align_timestamp_main()
    with st.spinner(t("Merging subtitles to video...")):
        step7_merge_sub_to_vid.merge_subtitles_to_video()
    
    st.success(t("Subtitle processing complete! 🎉"))
    st.balloons()

def audio_processing_section():
    st.header(t("c. Dubbing"))
    with st.container(border=True):
        st.markdown(f"""
        <p style='font-size: 20px;'>
        {t("This stage includes the following steps:")}
        <p style='font-size: 20px;'>
            1. {t("Generate audio tasks and chunks")}<br>
            2. {t("Extract reference audio")}<br>
            3. {t("Generate and merge audio files")}<br>
            4. {t("Merge final audio into video")}
        """, unsafe_allow_html=True)
        if not os.path.exists(DUB_VIDEO):
            if auto_execute("audio") or st.button(t("Start Audio Processing"), key="audio_processing_button"):
                process_audio()
                set_audio_ready()
                st.rerun()
        else:
            st.success(t("Audio processing is complete! You can click Download in the lower right corner of the video."))
            if load_key("burn_subtitles"):
                st.video(DUB_VIDEO) 
            if st.button(t("Delete dubbing files"), key="delete_dubbing_files"):
                delete_dubbing_files()
                set_audio_ready(False)
                st.rerun()
            if st.button(t("Archive to 'history'"), key="cleanup_in_audio_processing"):
                cleanup()
                st.rerun()

def process_audio():
    with st.spinner(t("Generate audio tasks")): 
        step8_1_gen_audio_task.gen_audio_task_main()
        step8_2_gen_dub_chunks.gen_dub_chunks()
    with st.spinner(t("Extract refer audio")):
        step9_extract_refer_audio.extract_refer_audio_main()
    with st.spinner(t("Generate all audio")):
        step10_gen_audio.gen_audio()
    with st.spinner(t("Merge full audio")):
        step11_merge_full_audio.merge_full_audio()
    with st.spinner(t("Merge dubbing to the video")):
        step12_merge_dub_to_vid.merge_video_audio()
    
    st.success(t("Audio processing complete! 🎇"))
    st.balloons()

def main():
    if not login_section():
        st.stop()
    with st.sidebar:
        page_setting()

    # 如果是reassigned download完成，自动进入后续步骤
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
