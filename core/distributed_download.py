import os
import json
import time
import requests
from typing import Dict, List, Optional
from pathlib import Path
import shutil
from flask import Flask, request, jsonify
from core.step1_ytdlp import download_video_ytdlp, find_video_files
from core.config_utils import load_key

app = Flask(__name__)

class DistributedDownloader:
    def __init__(self, node_id: str, coordinator_url: str):
        self.node_id = node_id
        self.coordinator_url = coordinator_url
        self.task_status = {}
        self.output_dir = "output"
        
    def register_node(self):
        """Register this node with the coordinator"""
        try:
            response = requests.post(
                f"{self.coordinator_url}/register",
                json={"node_id": self.node_id}
            )
            return response.json()
        except Exception as e:
            print(f"Failed to register node: {e}")
            return None

    def download_video(self, url: str, resolution: str = '1080', cutoff_time: Optional[int] = None) -> bool:
        """Attempt to download video, if fails, request task reassignment"""
        try:
            # Try to download
            download_video_ytdlp(url, resolution=resolution, cutoff_time=cutoff_time)
            
            # Check if download was successful
            if find_video_files():
                # Notify coordinator of success
                self._notify_success(url)
                return True
            return False
            
        except Exception as e:
            print(f"Download failed: {e}")
            # Request task reassignment
            self._request_reassignment(url)
            return False

    def _notify_success(self, url: str):
        """Notify coordinator of successful download"""
        try:
            requests.post(
                f"{self.coordinator_url}/notify_success",
                json={
                    "node_id": self.node_id,
                    "url": url,
                    "output_path": self.output_dir
                }
            )
        except Exception as e:
            print(f"Failed to notify success: {e}")

    def _request_reassignment(self, url: str):
        """Request task reassignment from coordinator"""
        try:
            response = requests.post(
                f"{self.coordinator_url}/reassign",
                json={
                    "node_id": self.node_id,
                    "url": url
                }
            )
            return response.json()
        except Exception as e:
            print(f"Failed to request reassignment: {e}")
            return None

    def handle_reassignment(self, url: str, source_node: str):
        """Handle a reassigned download task"""
        try:
            # Try to download
            success = self.download_video(url)
            if success:
                # Notify original node of success
                self._notify_node(source_node, url)
            return success
        except Exception as e:
            print(f"Failed to handle reassignment: {e}")
            return False

    def _notify_node(self, target_node: str, url: str):
        """Notify another node of successful download"""
        try:
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
            print(f"Failed to notify node: {e}")

def create_downloader(node_id: str = None) -> DistributedDownloader:
    """Create a distributed downloader instance"""
    if node_id is None:
        node_id = f"node_{int(time.time())}"
    
    coordinator_url = load_key("coordinator_url", "http://localhost:5000")
    return DistributedDownloader(node_id, coordinator_url)

# 创建全局下载器实例
downloader = None

@app.route('/handle_task', methods=['POST'])
def handle_task():
    """Handle incoming task from coordinator"""
    global downloader
    if downloader is None:
        return jsonify({"status": "error", "message": "Downloader not initialized"})
    
    data = request.json
    url = data.get('url')
    task_type = data.get('task_type')
    source_node = data.get('source_node')
    
    if task_type == "download":
        success = downloader.handle_reassignment(url, source_node)
        return jsonify({"status": "success" if success else "error"})
    
    return jsonify({"status": "error", "message": "Unknown task type"})

def start_node_server(port: int = 5001):
    """Start the node server"""
    global downloader
    downloader = create_downloader()
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    start_node_server() 