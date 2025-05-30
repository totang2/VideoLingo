class DistributedDownloader:
    def __init__(self, node_id: str = None):
        self.node_id = node_id
        self.coordinator_url = "http://localhost:5000"
        
    def register_node(self) -> bool:
        """注册节点到协调器"""
        try:
            response = requests.post(f"{self.coordinator_url}/register", json={"node_id": self.node_id})
            if response.status_code == 200:
                data = response.json()
                self.node_id = data.get("node_id")
                return True
            return False
        except Exception as e:
            print(f"Error registering node: {str(e)}")
            return False
            
    def get_task(self, url: str) -> dict:
        """从协调器获取任务"""
        try:
            response = requests.post(
                f"{self.coordinator_url}/task",
                json={
                    "node_id": self.node_id,
                    "url": url
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting task: {str(e)}")
            return None
            
    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        try:
            requests.post(
                f"{self.coordinator_url}/task/{task_id}/status",
                json={
                    "node_id": self.node_id,
                    "status": status
                }
            )
        except Exception as e:
            print(f"Error updating task status: {str(e)}")
            
    def download_video(self, url: str, resolution: str = "1080", cutoff_time: int = None, browser: str = None) -> bool:
        """下载视频
        
        Args:
            url: 视频URL
            resolution: 视频分辨率
            cutoff_time: 视频截取时间
            browser: 浏览器名称，用于获取cookies
            
        Returns:
            bool: 是否下载成功
        """
        try:
            # 检查是否已注册
            if not self.node_id:
                if not self.register_node():
                    return False
            
            # 获取任务
            task = self.get_task(url)
            if not task:
                return False
            
            # 下载视频
            from core.step1_ytdlp import download_video_ytdlp
            download_video_ytdlp(
                url=url,
                resolution=resolution,
                cutoff_time=cutoff_time,
                browser=browser
            )
            
            # 更新任务状态
            self.update_task_status(task["id"], "completed")
            return True
            
        except Exception as e:
            print(f"Error downloading video: {str(e)}")
            if task:
                self.update_task_status(task["id"], "failed")
            return False 