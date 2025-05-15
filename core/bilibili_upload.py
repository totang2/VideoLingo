import os
import requests
import json
import time
import hashlib
import base64
import math
from typing import Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class BilibiliUploader:
    """Bilibili video upload client"""
    
    def __init__(self, sessdata: str, bili_jct: str, cookie: str):
        self.sessdata = sessdata
        self.bili_jct = bili_jct
        self.cookie = cookie
        self.headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def _get_upload_url(self) -> str:
        """Get the upload URL from Bilibili API"""
        url = "https://member.bilibili.com/preupload"
        params = {
            'name': 'video.mp4',
            'size': '0',
            'r': 'upos',
            'profile': 'ugcupos/bup',
            'ssl': '0',
            'version': '2.8.12',
            'build': '2081200',
            'upcdn': 'bda2',
            'probe_version': '20200810',
        }
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()['url']

    def _upload_chunk(self, file_path: str, upload_url: str, chunk_size: int = 1024*1024*5) -> str:
        """Upload video file in chunks"""
        file_size = os.path.getsize(file_path)
        total_chunks = math.ceil(file_size / chunk_size)
        upload_id = str(int(time.time() * 1000))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Uploading video...", total=total_chunks)
            
            with open(file_path, 'rb') as f:
                for chunk_number in range(total_chunks):
                    chunk = f.read(chunk_size)
                    start = chunk_number * chunk_size
                    end = start + len(chunk) - 1
                    
                    headers = {
                        **self.headers,
                        'Content-Length': str(len(chunk)),
                        'Content-Type': 'application/octet-stream',
                        'Content-Range': f'bytes {start}-{end}/{file_size}'
                    }
                    
                    params = {
                        'partNumber': chunk_number + 1,
                        'uploadId': upload_id,
                        'chunk': chunk_number,
                        'chunks': total_chunks,
                        'size': len(chunk),
                        'start': start,
                        'end': end,
                        'total': file_size
                    }
                    
                    response = requests.put(
                        f"{upload_url}?{params}",
                        headers=headers,
                        data=chunk
                    )
                    response.raise_for_status()
                    progress.update(task, advance=1)

        return upload_id

    def _submit_video(self, 
                     title: str,
                     desc: str,
                     filename: str,
                     upload_id: str,
                     tags: list[str],
                     tid: int = 21) -> Dict:
        """Submit video information to Bilibili"""
        url = "https://member.bilibili.com/x/vu/web/add"
        
        data = {
            "copyright": 1,
            "videos": [{
                "filename": filename,
                "title": title,
                "desc": desc,
                "cid": upload_id
            }],
            "tid": tid,
            "title": title,
            "desc": desc,
            "tag": ",".join(tags),
            "csrf": self.bili_jct
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def upload_video(self,
                    video_path: str,
                    title: str,
                    description: str,
                    tags: list[str],
                    tid: int = 21) -> Dict:
        """Upload video to Bilibili
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            tid: Video category ID
            
        Returns:
            Dict containing upload response
        """
        try:
            # Get upload URL
            upload_url = self._get_upload_url()
            console.print("[green]✓[/green] Got upload URL")
            
            # Upload video in chunks
            upload_id = self._upload_chunk(video_path, upload_url)
            console.print("[green]✓[/green] Uploaded video file")
            
            # Submit video information
            filename = os.path.basename(video_path)
            response = self._submit_video(
                title=title,
                desc=description,
                filename=filename,
                upload_id=upload_id,
                tags=tags,
                tid=tid
            )
            console.print("[green]✓[/green] Submitted video information")
            
            if response['code'] == 0:
                console.print("[green]✓ Video uploaded successfully![/green]")
                return response
            else:
                raise Exception(f"Upload failed: {response['message']}")
                
        except Exception as e:
            console.print(f"[red]Error uploading video: {str(e)}[/red]")
            raise