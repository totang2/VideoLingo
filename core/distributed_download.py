import os
import json
import time
import requests
from typing import Dict, List, Optional
from pathlib import Path
import shutil
from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from core.step1_ytdlp import download_video_ytdlp, find_video_files
from core.config_utils import load_key, get_auto_process_config
import logging
import streamlit as st
from core.st import update_ui_after_download

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('downloader')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

class DistributedDownloader:
    def __init__(self, node_id: str, coordinator_url: str):
        self.node_id = node_id
        self.coordinator_url = coordinator_url
        self.task_status = {}
        self.output_dir = "output"
        logger.info(f"Downloader initialized: node_id={node_id}, coordinator_url={coordinator_url}")
        
    def register_node(self):
        """Register this node with the coordinator"""
        try:
            # 通过 WebSocket 注册
            logger.info("Registering node via WebSocket")
            socketio.emit('register', {
                'node_id': self.node_id
            })
            return {"status": "success", "node_id": self.node_id}
        except Exception as e:
            logger.error(f"Failed to register node via WebSocket: {e}")
            # 回退到 HTTP
            try:
                logger.info("Falling back to HTTP registration")
                response = requests.post(
                    f"{self.coordinator_url}/register",
                    json={"node_id": self.node_id}
                )
                return response.json()
            except Exception as e:
                logger.error(f"Failed to register node via HTTP: {e}")
                return None

    def download_video(self, url: str, resolution: str = '1080', cutoff_time: Optional[int] = None) -> bool:
        """Attempt to download video, if fails, request task reassignment"""
        logger.info(f"Starting download: url={url}, resolution={resolution}")
        try:
            # Try to download
            download_video_ytdlp(url, resolution=resolution, cutoff_time=cutoff_time)
            
            # Check if download was successful
            video_files = find_video_files()
            if video_files:
                logger.info(f"Download successful: {video_files}")
                # Notify coordinator of success
                self._notify_success(url)
                return True
            logger.warning("Download completed but no video files found")
            return False
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            # Request task reassignment
            self._request_reassignment(url)
            return False

    def _notify_success(self, url: str):
        """Notify coordinator of successful download"""
        try:
            # 通过 WebSocket 通知
            logger.info(f"Notifying success via WebSocket for {url}")
            socketio.emit('task_completed', {
                'node_id': self.node_id,
                'url': url,
                'output_path': self.output_dir
            })
        except Exception as e:
            logger.error(f"Failed to notify success via WebSocket: {e}")
            # 回退到 HTTP
            try:
                logger.info("Falling back to HTTP notification")
                requests.post(
                    f"{self.coordinator_url}/notify_success",
                    json={
                        "node_id": self.node_id,
                        "url": url,
                        "output_path": self.output_dir
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify success via HTTP: {e}")

    def _request_reassignment(self, url: str):
        """Request task reassignment from coordinator"""
        try:
            # 通过 WebSocket 请求重新分配
            logger.info(f"Requesting reassignment via WebSocket for {url}")
            socketio.emit('request_reassignment', {
                'node_id': self.node_id,
                'url': url
            })
        except Exception as e:
            logger.error(f"Failed to request reassignment via WebSocket: {e}")
            # 回退到 HTTP
            try:
                logger.info("Falling back to HTTP reassignment request")
                response = requests.post(
                    f"{self.coordinator_url}/reassign",
                    json={
                        "node_id": self.node_id,
                        "url": url
                    }
                )
                return response.json()
            except Exception as e:
                logger.error(f"Failed to request reassignment via HTTP: {e}")
                return None

    def handle_reassignment(self, url: str, source_node: str):
        """Handle a reassigned download task"""
        logger.info(f"Handling reassigned task: url={url}, source_node={source_node}")
        try:
            # Try to download
            success = self.download_video(url)
            if success:
                # 上传文件到协调器
                self._upload_to_coordinator(url)
                # Notify original node of success
                self._notify_node(source_node, url)
                
                # 检查是否需要自动处理
                auto_config = get_auto_process_config()
                if auto_config["auto_process_after_reassign"]:
                    logger.info("Starting automatic post-processing")
                    video_files = find_video_files()
                    if video_files:
                        video_path = video_files[0]
                        try:
                            # 更新 Streamlit UI
                            logger.info("Updating Streamlit UI")
                            update_ui_after_download(video_path)
                            logger.info("Streamlit UI updated successfully")
                        except Exception as e:
                            logger.error(f"Failed to update Streamlit UI: {e}")
            return success
        except Exception as e:
            logger.error(f"Failed to handle reassignment: {e}")
            return False

    def _upload_to_coordinator(self, url: str):
        """Upload file to coordinator"""
        try:
            # 找到下载的文件
            logger.info("Finding downloaded video files")
            video_files = find_video_files()
            if not video_files:
                raise Exception("No video files found")
            
            # 上传文件
            logger.info(f"Uploading file {video_files[0]} to coordinator")
            with open(video_files[0], 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.coordinator_url}/upload/{url}",
                    files=files
                )
                response.raise_for_status()
                logger.info(f"File uploaded to coordinator: {response.json()}")
        except Exception as e:
            logger.error(f"Failed to upload file to coordinator: {e}")
            raise

    def _notify_node(self, target_node: str, url: str):
        """Notify another node of successful download"""
        try:
            # 通过 WebSocket 通知
            logger.info(f"Notifying node {target_node} via WebSocket")
            socketio.emit('notify_node', {
                'source_node': self.node_id,
                'target_node': target_node,
                'url': url,
                'output_path': self.output_dir
            })
        except Exception as e:
            logger.error(f"Failed to notify node via WebSocket: {e}")
            # 回退到 HTTP
            try:
                logger.info("Falling back to HTTP notification")
                requests.post(
                    f"{self.coordinator_url}/notify_node",
                    json={
                        "source_node": self.node_id,
                        "target_node": target_node,
                        "url": url,
                        "output_path": self.output_dir
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify node via HTTP: {e}")

def create_downloader(node_id: str = None) -> DistributedDownloader:
    """Create a distributed downloader instance"""
    if node_id is None:
        node_id = f"node_{int(time.time())}"
    
    coordinator_url = load_key("coordinator_url", "http://localhost:8502")
    return DistributedDownloader(node_id, coordinator_url)

# 创建全局下载器实例
downloader = None

# WebSocket 事件处理
@socketio.on('connect')
def handle_connect():
    logger.info('Connected to coordinator')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Disconnected from coordinator')

@socketio.on('registration_result')
def handle_registration_result(data):
    logger.info(f'Registration result: {data}')

@socketio.on('task_assigned')
def handle_task_assigned(data):
    """Handle incoming task from coordinator"""
    global downloader
    if downloader is None:
        logger.error("Downloader not initialized")
        return
    
    url = data.get('url')
    task_type = data.get('task_type')
    logger.info(f"Received task: url={url}, type={task_type}")
    
    if task_type == "download":
        success = downloader.download_video(url)
        emit('task_completion_result', {
            'status': 'success' if success else 'error'
        })

@socketio.on('task_reassigned')
def handle_task_reassigned(data):
    """Handle reassigned task from coordinator"""
    global downloader
    if downloader is None:
        logger.error("Downloader not initialized")
        return
    
    url = data.get('url')
    task_type = data.get('task_type')
    source_node = data.get('source_node')
    logger.info(f"Received reassigned task: url={url}, type={task_type}, source={source_node}")
    
    if task_type == "download":
        success = downloader.handle_reassignment(url, source_node)
        emit('task_completion_result', {
            'status': 'success' if success else 'error'
        })

@socketio.on('download_completed')
def handle_download_completed(data):
    """Handle download completion notification from another node"""
    global downloader
    if downloader is None:
        logger.error("Downloader not initialized")
        return
    
    url = data.get('url')
    source_node = data.get('source_node')
    source_output_path = data.get('output_path')
    logger.info(f"Received download completion: url={url}, source={source_node}")
    
    try:
        # 创建目标输出目录
        target_output = Path(f"output_{downloader.node_id}")
        target_output.mkdir(exist_ok=True)
        logger.info(f"Created output directory: {target_output}")
        
        # 从协调器下载文件
        logger.info(f"Downloading file from coordinator for {url}")
        response = requests.get(
            f"{downloader.coordinator_url}/download/{url}",
            stream=True
        )
        response.raise_for_status()
        
        # 保存文件
        output_file = target_output / f"{url.split('/')[-1]}.mp4"
        logger.info(f"Saving file to {output_file}")
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"File downloaded successfully: {output_file}")
        
        # 检查是否需要自动处理
        auto_config = get_auto_process_config()
        if auto_config["auto_process_after_reassign"]:
            logger.info("Starting automatic post-processing")
            if auto_config["process_text"]:
                logger.info("Starting text processing")
                process_video_text(str(output_file))
            if auto_config["process_audio"]:
                logger.info("Starting audio processing")
                process_video_audio(str(output_file))
            logger.info("Automatic post-processing completed")
            
            # 更新 Streamlit UI
            try:
                logger.info("Updating Streamlit UI")
                update_ui_after_download(str(output_file))
                logger.info("Streamlit UI updated successfully")
            except Exception as e:
                logger.error(f"Failed to update Streamlit UI: {e}")
        
    except Exception as e:
        logger.error(f"Failed to download file from coordinator: {e}")
        # 通知协调器下载失败
        socketio.emit('file_receive_failed', {
            'url': url,
            'node_id': downloader.node_id,
            'error': str(e)
        })

# HTTP 路由（作为备用）
@app.route('/handle_task', methods=['POST'])
def handle_task():
    """Handle incoming task from coordinator (HTTP fallback)"""
    global downloader
    if downloader is None:
        logger.error("Downloader not initialized")
        return jsonify({"status": "error", "message": "Downloader not initialized"})
    
    data = request.json
    url = data.get('url')
    task_type = data.get('task_type')
    source_node = data.get('source_node')
    logger.info(f"Received HTTP task: url={url}, type={task_type}, source={source_node}")
    
    if task_type == "download":
        success = downloader.handle_reassignment(url, source_node)
        return jsonify({"status": "success" if success else "error"})
    
    return jsonify({"status": "error", "message": "Unknown task type"})

# 添加文件下载路由
@app.route('/download/<path:url>')
def download_file(url):
    """Serve downloaded files to other nodes"""
    logger.info(f"Serving file for {url}")
    try:
        file_path = Path(f"output/{url}.mp4")
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return "File not found", 404
        logger.info(f"Sending file: {file_path}")
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Failed to serve file: {e}")
        return str(e), 500

def start_node_server(port: int = 5001):
    """Start the node server"""
    global downloader
    logger.info(f"Starting node server on port {port}")
    downloader = create_downloader()
    # 注册节点
    downloader.register_node()
    # 启动服务器
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    start_node_server() 