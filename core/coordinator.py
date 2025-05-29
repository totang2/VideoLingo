from flask import Flask, request, jsonify
from typing import Dict, List, Set
import os
import shutil
import time
import requests
from pathlib import Path

app = Flask(__name__)

class Coordinator:
    def __init__(self):
        self.nodes: Dict[str, dict] = {}  # node_id -> node_info
        self.tasks: Dict[str, dict] = {}  # url -> task_info
        self.node_tasks: Dict[str, Set[str]] = {}  # node_id -> set of urls
        
    def register_node(self, node_id: str) -> dict:
        """Register a new node"""
        self.nodes[node_id] = {
            "status": "active",
            "last_seen": time.time()
        }
        self.node_tasks[node_id] = set()
        return {"status": "success", "node_id": node_id}
    
    def assign_task(self, url: str, node_id: str) -> dict:
        """Assign a download task to a node"""
        if url not in self.tasks:
            self.tasks[url] = {
                "status": "pending",
                "assigned_to": node_id,
                "created_at": time.time()
            }
        self.node_tasks[node_id].add(url)
        
        # 通知节点处理任务
        self._notify_node_task(node_id, url)
        
        return {"status": "success", "task": self.tasks[url]}
    
    def _notify_node_task(self, node_id: str, url: str):
        """Notify node to handle a task"""
        try:
            node_url = f"http://{node_id}/handle_task"
            requests.post(node_url, json={
                "url": url,
                "task_type": "download"
            })
        except Exception as e:
            print(f"Failed to notify node {node_id}: {e}")
    
    def notify_success(self, node_id: str, url: str, output_path: str) -> dict:
        """Handle successful download notification"""
        if url in self.tasks:
            self.tasks[url]["status"] = "completed"
            self.tasks[url]["completed_at"] = time.time()
            self.tasks[url]["completed_by"] = node_id
            self.tasks[url]["output_path"] = output_path
        return {"status": "success"}
    
    def request_reassignment(self, node_id: str, url: str) -> dict:
        """Handle task reassignment request"""
        # Find another available node
        available_nodes = [
            n for n in self.nodes.keys()
            if n != node_id and self.nodes[n]["status"] == "active"
        ]
        
        if not available_nodes:
            return {"status": "error", "message": "No available nodes"}
        
        # Assign to the least busy node
        target_node = min(available_nodes, key=lambda n: len(self.node_tasks[n]))
        
        # Update task info
        self.tasks[url]["status"] = "reassigned"
        self.tasks[url]["reassigned_to"] = target_node
        self.tasks[url]["reassigned_at"] = time.time()
        
        # Update node tasks
        self.node_tasks[node_id].remove(url)
        self.node_tasks[target_node].add(url)
        
        # 通知目标节点处理重新分配的任务
        self._notify_node_task(target_node, url)
        
        return {
            "status": "success",
            "reassigned_to": target_node
        }
    
    def notify_node(self, source_node: str, target_node: str, url: str, output_path: str) -> dict:
        """Handle node-to-node notification"""
        if url in self.tasks:
            self.tasks[url]["status"] = "completed"
            self.tasks[url]["completed_at"] = time.time()
            self.tasks[url]["completed_by"] = source_node
            self.tasks[url]["output_path"] = output_path
            
            # Copy output files to target node's output directory
            target_output = Path(f"output_{target_node}")
            target_output.mkdir(exist_ok=True)
            
            for file in Path(output_path).glob("*"):
                if file.is_file():
                    shutil.copy2(file, target_output / file.name)
        
        return {"status": "success"}

coordinator = Coordinator()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    node_id = data.get('node_id')
    return jsonify(coordinator.register_node(node_id))

@app.route('/assign', methods=['POST'])
def assign():
    data = request.json
    url = data.get('url')
    node_id = data.get('node_id')
    return jsonify(coordinator.assign_task(url, node_id))

@app.route('/notify_success', methods=['POST'])
def notify_success():
    data = request.json
    node_id = data.get('node_id')
    url = data.get('url')
    output_path = data.get('output_path')
    return jsonify(coordinator.notify_success(node_id, url, output_path))

@app.route('/reassign', methods=['POST'])
def reassign():
    data = request.json
    node_id = data.get('node_id')
    url = data.get('url')
    return jsonify(coordinator.request_reassignment(node_id, url))

@app.route('/notify_node', methods=['POST'])
def notify_node():
    data = request.json
    source_node = data.get('source_node')
    target_node = data.get('target_node')
    url = data.get('url')
    output_path = data.get('output_path')
    return jsonify(coordinator.notify_node(source_node, target_node, url, output_path))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8502) 