from ruamel.yaml import YAML
from typing import Any, Optional
import os, sys
import threading
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 日志配置
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'config_utils.log')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

def setup_logger(name: str) -> logging.Logger:
    """设置日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志目录
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 如果已经有处理器，不重复添加
    if logger.handlers:
        return logger
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

# 创建日志记录器
logger = setup_logger('config_utils')

CONFIG_PATH = 'config.yaml'
config_lock = threading.Lock()

yaml = YAML()
yaml.preserve_quotes = True

def _get_nested_value(data: dict, key: str, default: Any = None) -> Any:
    """Get nested value from dictionary using dot notation
    
    Args:
        data: Dictionary to search in
        key: Key in dot notation (e.g. 'distributed_download.auto_process')
        default: Default value if key not found
        
    Returns:
        Value if found, default otherwise
    """
    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            logger.debug(f"Key {key} not found, using default value")
            return default
    return value

def load_key(key: str, default: Any = None) -> Any:
    """Load a key from config.yaml with thread safety
    
    Args:
        key: Key in dot notation (e.g. 'distributed_download.auto_process')
        default: Default value if key not found
        
    Returns:
        Value if found, default otherwise
    """
    with config_lock:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                data = yaml.load(file)
            value = _get_nested_value(data, key, default)
            logger.debug(f"Loaded key {key}: {value}")
            return value
        except Exception as e:
            logger.error(f"Failed to load key {key}: {e}", exc_info=True)
            return default

def update_key(key: str, value: Any):
    """更新配置值
    
    Args:
        key: 配置键，使用点号分隔 (例如 'distributed_download.auto_process')
        value: 要保存的值
        
    Raises:
        ValueError: 如果键格式不正确
        IOError: 如果文件操作失败
        YAMLError: 如果 YAML 解析失败
    """
    if not key or not isinstance(key, str):
        raise ValueError("Key must be a non-empty string")
        
    with config_lock:
        try:         
            # 读取现有配置
            data = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                        data = yaml.load(file) or {}
                except Exception as e:
                    logger.error(f"Failed to read config file: {e}")
                    # 如果文件损坏，创建新的配置
                    data = {}
            
            # 使用点号分隔的键来更新嵌套字典
            keys = key.split('.')
            current = data
            for k in keys[:-1]:
                if not isinstance(current, dict):
                    current = {}
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 设置最终值
            if not isinstance(current, dict):
                current = {}
            current[keys[-1]] = value
            
            # 保存更新后的配置
            with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
                yaml.dump(data, file)
            logger.info(f"Successfully updated key {key} with value {value}")
            
        except Exception as e:
            logger.error(f"Failed to update key {key}: {e}", exc_info=True)
            raise

def save_key(key: str, value: Any) -> bool:
    """Save a key-value pair to config.yaml with thread safety
    
    Args:
        key: Key in dot notation (e.g. 'distributed_download.auto_process')
        value: Value to save
        
    Returns:
        True if successful, False otherwise
    """
    with config_lock:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                data = yaml.load(file)
                
            keys = key.split('.')
            current = data
            for k in keys[:-1]:
                if isinstance(current, dict):
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                else:
                    current = {}
                    
            if isinstance(current, dict):
                current[keys[-1]] = value
                with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
                    yaml.dump(data, file)
                logger.info(f"Successfully saved key {key} with value {value}")
                return True
            logger.warning(f"Failed to save key {key}: Invalid path")
            return False
        except Exception as e:
            logger.error(f"Failed to save key {key}: {e}", exc_info=True)
            return False

def get_auto_process_config() -> dict:
    """Get auto process configuration from YAML config
    
    Returns:
        Dictionary containing auto process settings
    """
    config = {
        "auto_process_after_reassign": load_key('distributed_download.auto_process_after_reassign', True),
        "process_text": load_key('distributed_download.process_text', True),
        "process_audio": load_key('distributed_download.process_audio', True)
    }
    logger.debug(f"Loaded auto process config: {config}")
    return config

def save_auto_process_config(auto_process: bool, process_text: bool = True, process_audio: bool = True) -> bool:
    """Save auto process configuration to YAML config
    
    Args:
        auto_process: Whether to auto process after reassign
        process_text: Whether to process text
        process_audio: Whether to process audio
        
    Returns:
        True if successful, False otherwise
    """
    config = {
        'auto_process_after_reassign': auto_process,
        'process_text': process_text,
        'process_audio': process_audio
    }
    logger.info(f"Saving auto process config: {config}")
    
    success = True
    success &= save_key('distributed_download.auto_process_after_reassign', auto_process)
    success &= save_key('distributed_download.process_text', process_text)
    success &= save_key('distributed_download.process_audio', process_audio)
    
    if success:
        logger.info("Successfully saved auto process configuration")
    else:
        logger.error("Failed to save auto process configuration")
    
    return success

def ensure_user_config(user_id: str) -> bool:
    """Ensure user configuration exists
    
    Args:
        user_id: User ID to ensure config for
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Ensuring config for user {user_id}")
    default_config = {
        'cookie': '',
        'sessdata': '',
        'bili_jct': ''
    }
    success = save_key(f'bilibili.{user_id}', default_config)
    
    if success:
        logger.info(f"Successfully ensured config for user {user_id}")
    else:
        logger.error(f"Failed to ensure config for user {user_id}")
    
    return success

def get_joiner(language: str) -> str:
    """Get joiner for language
    
    Args:
        language: Language code
        
    Returns:
        Joiner string (space or empty)
        
    Raises:
        ValueError: If language is not supported
    """
    logger.debug(f"Getting joiner for language: {language}")
    if language in load_key('language_split_with_space', []):
        logger.debug(f"Using space joiner for language: {language}")
        return " "
    elif language in load_key('language_split_without_space', []):
        logger.debug(f"Using empty joiner for language: {language}")
        return ""
    else:
        logger.error(f"Unsupported language code: {language}")
        raise ValueError(f"Unsupported language code: {language}")

if __name__ == "__main__":
    print(load_key('language_split_with_space'))
