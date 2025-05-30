import time
from log import logger
from flask import request, jsonify
import socketio

class Coordinator:
    def __init__(self):
        self.nodes = {}  # 节点信息
        self.task_queue = []  # 任务队列
        self.current_task_index = 0  # 当前执行的任务索引
        self.task_status = {}  # 任务状态
        self.socketio = None

    def add_task(self, url: str, task_type: str = "download"):
        """添加任务到队列"""
        task_id = f"task_{len(self.task_queue)}"
        task = {
            'id': task_id,
            'url': url,
            'type': task_type,
            'status': 'queued',
            'timestamp': time.time()
        }
        self.task_queue.append(task)
        self.task_status[task_id] = task
        logger.info(f"Task added to queue: {task_id}")
        return task_id

    def get_queue_status(self):
        """获取队列状态"""
        return {
            'total_tasks': len(self.task_queue),
            'current_index': self.current_task_index,
            'tasks': self.task_queue,
            'status': self.task_status
        }

    def assign_task(self, node_id: str):
        """分配任务给节点"""
        if not self.task_queue:
            return None

        # 找到下一个未完成的任务
        while self.current_task_index < len(self.task_queue):
            task = self.task_queue[self.current_task_index]
            if task['status'] == 'queued':
                task['status'] = 'processing'
                task['assigned_to'] = node_id
                logger.info(f"Task {task['id']} assigned to node {node_id}")
                return task
            self.current_task_index += 1

        return None

    def mark_task_completed(self, task_id: str):
        """标记任务完成"""
        if task_id in self.task_status:
            self.task_status[task_id]['status'] = 'completed'
            logger.info(f"Task {task_id} marked as completed")

    def mark_task_failed(self, task_id: str):
        """标记任务失败"""
        if task_id in self.task_status:
            self.task_status[task_id]['status'] = 'failed'
            logger.info(f"Task {task_id} marked as failed")

    def get_next_available_node(self):
        """获取下一个可用的节点"""
        for node_id, node in self.nodes.items():
            if node['status'] == 'idle':
                return node_id
        return None

    def handle_node_ready(self, node_id: str):
        """处理节点就绪事件"""
        if node_id in self.nodes:
            self.nodes[node_id]['status'] = 'idle'
            # 尝试分配新任务
            task = self.assign_task(node_id)
            if task:
                self.socketio.emit('task_assigned', {
                    'node_id': node_id,
                    'task_id': task['id'],
                    'url': task['url'],
                    'type': task['type']
                })
                logger.info(f"New task assigned to node {node_id}")

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('register')
def handle_register(data):
    node_id = data.get('node_id')
    if node_id:
        coordinator.nodes[node_id] = {
            'status': 'idle',
            'last_seen': time.time()
        }
        logger.info(f"Node registered: {node_id}")
        # 尝试分配任务
        coordinator.handle_node_ready(node_id)

@socketio.on('task_completed')
def handle_task_completed(data):
    task_id = data.get('task_id')
    node_id = data.get('node_id')
    if task_id and node_id:
        coordinator.mark_task_completed(task_id)
        coordinator.handle_node_ready(node_id)

@socketio.on('task_failed')
def handle_task_failed(data):
    task_id = data.get('task_id')
    node_id = data.get('node_id')
    if task_id and node_id:
        coordinator.mark_task_failed(task_id)
        coordinator.handle_node_ready(node_id)

# HTTP 路由
@app.route('/add_task', methods=['POST'])
def add_task():
    data = request.json
    url = data.get('url')
    task_type = data.get('type', 'download')
    if url:
        task_id = coordinator.add_task(url, task_type)
        return jsonify({'task_id': task_id})
    return jsonify({'error': 'Invalid request'}), 400

@app.route('/queue_status', methods=['GET'])
def get_queue_status():
    return jsonify(coordinator.get_queue_status())

# 初始化 coordinator
coordinator = Coordinator()
coordinator.socketio = socketio

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8502) 