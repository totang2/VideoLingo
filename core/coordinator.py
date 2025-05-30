from flask import Flask, request, jsonify, send_file
from typing import Dict, List, Set
import os
import shutil
import time
import requests
from pathlib import Path
from flask_socketio import SocketIO, emit
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('coordinator')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

class Coordinator:
    def __init__(self):
        self.nodes: Dict[str, dict] = {}  # node_id -> node_info
        self.tasks: Dict[str, dict] = {}  # url -> task_info
        self.node_tasks: Dict[str, Set[str]] = {}  # node_id -> set of urls
        self.node_sids: Dict[str, str] = {}  # node_id -> socket_id
        self.output_dir = Path("coordinator_output")
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Coordinator initialized, output directory: {self.output_dir}")
        
    def register_node(self, node_id: str, socket_id: str = None) -> dict:
        """Register a new node"""
        logger.info(f"Registering node {node_id} with socket_id {socket_id}")
        self.nodes[node_id] = {
            "status": "active",
            "last_seen": time.time()
        }
        self.node_tasks[node_id] = set()
        if socket_id:
            self.node_sids[node_id] = socket_id
            logger.info(f"Node {node_id} registered with WebSocket connection")
        return {"status": "success", "node_id": node_id}
    
    def assign_task(self, url: str, node_id: str) -> dict:
        """Assign a download task to a node"""
        logger.info(f"Assigning task {url} to node {node_id}")
        if url not in self.tasks:
            self.tasks[url] = {
                "status": "pending",
                "assigned_to": node_id,
                "created_at": time.time()
            }
            logger.info(f"Created new task for {url}")
        self.node_tasks[node_id].add(url)
        logger.info(f"Node {node_id} now has {len(self.node_tasks[node_id])} tasks")
        
        # 通知节点处理任务
        self._notify_node_task(node_id, url)
        
        return {"status": "success", "task": self.tasks[url]}
    
    def _notify_node_task(self, node_id: str, url: str):
        """Notify node to handle a task"""
        try:
            # 优先使用 WebSocket 通知
            if node_id in self.node_sids:
                logger.info(f"Notifying node {node_id} via WebSocket about task {url}")
                socketio.emit('task_assigned', {
                    'url': url,
                    'task_type': 'download'
                }, room=self.node_sids[node_id])
                return
            else:
                logger.warning(f"Node {node_id} not connected via WebSocket")
        except Exception as e:
            logger.error(f"Failed to notify node {node_id} via WebSocket: {e}")
    
    def notify_success(self, node_id: str, url: str, output_path: str) -> dict:
        """Handle successful download notification"""
        logger.info(f"Received success notification from node {node_id} for task {url}")
        if url in self.tasks:
            self.tasks[url]["status"] = "completed"
            self.tasks[url]["completed_at"] = time.time()
            self.tasks[url]["completed_by"] = node_id
            self.tasks[url]["output_path"] = output_path
            logger.info(f"Task {url} marked as completed by node {node_id}")
        return {"status": "success"}
    
    def request_reassignment(self, node_id: str, url: str) -> dict:
        """Handle task reassignment request"""
        logger.info(f"Received reassignment request from node {node_id} for task {url}")
        
        # 标记当前节点为失败状态
        if node_id in self.nodes:
            self.nodes[node_id]["status"] = "failed"
            self.nodes[node_id]["last_failure"] = time.time()
            logger.info(f"Marked node {node_id} as failed")
        
        # Find another available node (排除失败的节点)
        available_nodes = [
            n for n in self.nodes.keys()
            if n != node_id 
            and self.nodes[n]["status"] == "active"
            and (n not in self.nodes or "last_failure" not in self.nodes[n] or 
                 time.time() - self.nodes[n]["last_failure"] > 300)  # 5分钟内没有失败的节点
        ]
        
        if not available_nodes:
            logger.error(f"No available nodes for reassignment of task {url}")
            return {"status": "error", "message": "No available nodes"}
        
        # Assign to the least busy node
        target_node = min(available_nodes, key=lambda n: len(self.node_tasks[n]))
        logger.info(f"Selected node {target_node} for reassignment (has {len(self.node_tasks[target_node])} tasks)")
        
        # Update task info
        self.tasks[url]["status"] = "reassigned"
        self.tasks[url]["reassigned_to"] = target_node
        self.tasks[url]["reassigned_at"] = time.time()
        self.tasks[url]["reassigned_from"] = node_id
        
        # Update node tasks
        self.node_tasks[node_id].remove(url)
        self.node_tasks[target_node].add(url)
        logger.info(f"Task {url} reassigned from node {node_id} to node {target_node}")
        
        # 通知目标节点处理重新分配的任务
        self._notify_node_task(target_node, url)
        
        return {
            "status": "success",
            "reassigned_to": target_node
        }
    
    def notify_node(self, source_node: str, target_node: str, url: str, output_path: str) -> dict:
        """Handle node-to-node notification"""
        logger.info(f"Received node notification: source={source_node}, target={target_node}, url={url}")
        if url in self.tasks:
            self.tasks[url]["status"] = "completed"
            self.tasks[url]["completed_at"] = time.time()
            self.tasks[url]["completed_by"] = source_node
            self.tasks[url]["output_path"] = output_path
            logger.info(f"Task {url} completed by node {source_node}, output at {output_path}")
            
            # 通过 WebSocket 通知目标节点
            if target_node in self.node_sids:
                logger.info(f"Notifying node {target_node} about completed download via WebSocket")
                socketio.emit('download_completed', {
                    'url': url,
                    'source_node': source_node,
                    'output_path': output_path
                }, room=self.node_sids[target_node])
            else:
                logger.warning(f"Target node {target_node} not connected via WebSocket")
        
        return {"status": "success"}

    def receive_file(self, url: str, file) -> dict:
        """Receive file from node"""
        logger.info(f"Receiving file for task {url}")
        try:
            # 保存文件到协调器
            output_file = self.output_dir / f"{url.split('/')[-1]}.mp4"
            file.save(output_file)
            logger.info(f"File saved to {output_file}")
            
            # 更新任务状态
            if url in self.tasks:
                self.tasks[url]["coordinator_file"] = str(output_file)
                logger.info(f"Updated task {url} with coordinator file path")
            
            return {"status": "success", "file_path": str(output_file)}
        except Exception as e:
            logger.error(f"Failed to receive file: {e}")
            return {"status": "error", "message": str(e)}

coordinator = Coordinator()

# WebSocket 事件处理
@socketio.on('connect')
def handle_connect():
    logger.info(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('register')
def handle_register(data):
    node_id = data.get('node_id')
    if node_id:
        logger.info(f'Registering node {node_id} with socket_id {request.sid}')
        result = coordinator.register_node(node_id, request.sid)
        emit('registration_result', result)

@socketio.on('task_completed')
def handle_task_completed(data):
    node_id = data.get('node_id')
    url = data.get('url')
    output_path = data.get('output_path')
    logger.info(f'Received task completion from node {node_id} for {url}')
    result = coordinator.notify_success(node_id, url, output_path)
    emit('task_completion_result', result)

@socketio.on('request_reassignment')
def handle_reassignment_request(data):
    node_id = data.get('node_id')
    url = data.get('url')
    logger.info(f'Received reassignment request from node {node_id} for {url}')
    result = coordinator.request_reassignment(node_id, url)
    emit('reassignment_result', result)

# HTTP 路由
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    node_id = data.get('node_id')
    logger.info(f'HTTP: Registering node {node_id}')
    return jsonify(coordinator.register_node(node_id))

@app.route('/assign', methods=['POST'])
def assign():
    data = request.json
    url = data.get('url')
    node_id = data.get('node_id')
    logger.info(f'HTTP: Assigning task {url} to node {node_id}')
    return jsonify(coordinator.assign_task(url, node_id))

@app.route('/notify_success', methods=['POST'])
def notify_success():
    data = request.json
    node_id = data.get('node_id')
    url = data.get('url')
    output_path = data.get('output_path')
    logger.info(f'HTTP: Received success notification from node {node_id} for {url}')
    return jsonify(coordinator.notify_success(node_id, url, output_path))

@app.route('/reassign', methods=['POST'])
def reassign():
    data = request.json
    node_id = data.get('node_id')
    url = data.get('url')
    logger.info(f'HTTP: Received reassignment request from node {node_id} for {url}')
    return jsonify(coordinator.request_reassignment(node_id, url))

@app.route('/notify_node', methods=['POST'])
def notify_node():
    data = request.json
    source_node = data.get('source_node')
    target_node = data.get('target_node')
    url = data.get('url')
    output_path = data.get('output_path')
    logger.info(f'HTTP: Received node notification from {source_node} to {target_node} for {url}')
    return jsonify(coordinator.notify_node(source_node, target_node, url, output_path))

@app.route('/upload/<path:url>', methods=['POST'])
def upload_file(url):
    """Receive file from node"""
    logger.info(f'HTTP: Receiving file upload for {url}')
    if 'file' not in request.files:
        logger.error('No file part in request')
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        logger.error('No selected file')
        return jsonify({"status": "error", "message": "No selected file"})
    return jsonify(coordinator.receive_file(url, file))

@app.route('/download/<path:url>')
def download_file(url):
    """Serve file to nodes"""
    logger.info(f'HTTP: Serving file for {url}')
    try:
        if url not in coordinator.tasks:
            logger.error(f'Task {url} not found')
            return "Task not found", 404
            
        task = coordinator.tasks[url]
        if "coordinator_file" not in task:
            logger.error(f'File not found for task {url}')
            return "File not found", 404
            
        file_path = Path(task["coordinator_file"])
        if not file_path.exists():
            logger.error(f'File {file_path} does not exist')
            return "File not found", 404
            
        logger.info(f'Serving file {file_path}')
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f'Failed to serve file: {e}')
        return str(e), 500

if __name__ == '__main__':
    logger.info('Starting coordinator server...')
    socketio.run(app, host='0.0.0.0', port=8502, allow_unsafe_werkzeug=True) 