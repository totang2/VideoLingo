#!/usr/bin/env python3
import os
import platform
import subprocess
import shutil
import sys
import venv
import zipfile

def build_app():
    print("开始构建 VideoLingo...")
    
    # 确保在正确的目录中
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 检查操作系统
    if platform.system() != "Windows":
        print("错误：此脚本只能在 Windows 系统上运行")
        sys.exit(1)
    
    # 创建发布目录
    dist_dir = "dist/VideoLingo"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # 创建虚拟环境
    print("创建虚拟环境...")
    venv_dir = os.path.join(dist_dir, "venv")
    venv.create(venv_dir, with_pip=True)
    
    # 获取 Python 解释器路径
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    
    # 安装依赖
    print("安装依赖...")
    subprocess.run([pip_exe, "install", "--upgrade", "pip"], check=True)
    
    # 先安装 PyTorch 和 torchaudio
    print("安装 PyTorch 和 torchaudio...")
    subprocess.run([pip_exe, "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu118"], check=True)
    
    # 安装其他依赖
    print("安装其他依赖...")
    subprocess.run([pip_exe, "install", "-r", "requirements.txt"], check=True)
    
    # 复制必要的文件
    print("复制必要文件...")
    shutil.copy("config.yaml", dist_dir)
    shutil.copy("README.md", dist_dir)
    shutil.copy("st.py", dist_dir)
    
    # 复制 .streamlit 目录
    streamlit_dir = os.path.join(dist_dir, ".streamlit")
    if not os.path.exists(streamlit_dir):
        os.makedirs(streamlit_dir)
    for root, dirs, files in os.walk(".streamlit"):
        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(streamlit_dir, file)
            shutil.copy2(src, dst)
    
    # 复制工具目录
    tools_dir = os.path.join(dist_dir, "tools")
    if not os.path.exists(tools_dir):
        os.makedirs(tools_dir)
    for root, dirs, files in os.walk("tools"):
        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(tools_dir, file)
            shutil.copy2(src, dst)
    
    # 创建启动脚本
    with open(os.path.join(dist_dir, "start.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("echo 正在启动 VideoLingo...\n")
        f.write("venv\\Scripts\\python.exe -m streamlit run st.py --server.port=8501 --server.address=127.0.0.1\n")
        f.write("pause\n")
    
    # 创建安装脚本
    with open(os.path.join(dist_dir, "install.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("echo 正在安装 VideoLingo...\n")
        f.write("echo 请稍候...\n")
        f.write("venv\\Scripts\\python.exe -m pip install --upgrade pip\n")
        f.write("venv\\Scripts\\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118\n")
        f.write("venv\\Scripts\\python.exe -m pip install -r requirements.txt\n")
        f.write("echo 安装完成！\n")
        f.write("echo 现在可以运行 start.bat 启动程序了。\n")
        f.write("pause\n")
    
    # 创建桌面快捷方式
    with open(os.path.join(dist_dir, "创建桌面快捷方式.bat"), "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write("echo 正在创建桌面快捷方式...\n")
        f.write("set SCRIPT=\"%TEMP%\\create_shortcut.vbs\"\n")
        f.write("echo Set oWS = WScript.CreateObject(\"WScript.Shell\") > %SCRIPT%\n")
        f.write("echo sLinkFile = oWS.SpecialFolders(\"Desktop\") ^& \"\\VideoLingo.lnk\" >> %SCRIPT%\n")
        f.write("echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%\n")
        f.write("echo oLink.TargetPath = \"%~dp0start.bat\" >> %SCRIPT%\n")
        f.write("echo oLink.WorkingDirectory = \"%~dp0\" >> %SCRIPT%\n")
        f.write("echo oLink.Description = \"VideoLingo - 视频翻译工具\" >> %SCRIPT%\n")
        f.write("echo oLink.IconLocation = \"%~dp0tools\\icon.ico\" >> %SCRIPT%\n")
        f.write("echo oLink.Save >> %SCRIPT%\n")
        f.write("cscript /nologo %SCRIPT%\n")
        f.write("del %SCRIPT%\n")
        f.write("echo 桌面快捷方式创建完成！\n")
        f.write("pause\n")
    
    # 创建压缩包
    print("创建安装包...")
    zip_filename = "VideoLingo-Windows.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(dist_dir))
                zipf.write(file_path, arcname)
    
    print(f"\n构建完成！")
    print(f"安装包位于: {os.path.abspath(zip_filename)}")
    print("\n使用方法:")
    print("1. 解压 VideoLingo-Windows.zip")
    print("2. 双击 install.bat 安装依赖")
    print("3. 双击 start.bat 启动程序")
    print("4. 如需创建桌面快捷方式，请运行 创建桌面快捷方式.bat")

if __name__ == "__main__":
    build_app() 