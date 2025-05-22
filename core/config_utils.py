from ruamel.yaml import YAML
from typing import Any
import os, sys
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = 'config.yaml'
config_lock = threading.Lock()

yaml = YAML()
yaml.preserve_quotes = True

def load_key(key: str) -> Any:
    """Load a value from config file with thread safety"""
    with config_lock:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file)

    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None  # 如果键不存在，返回None而不是抛出异常
    return value

def update_key(key: str, new_value: Any) -> bool:
    """Update a value in config file with thread safety"""
    with config_lock:
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
                return False

        if isinstance(current, dict):
            current[keys[-1]] = new_value
            with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
                yaml.dump(data, file)
            return True
        return False

def ensure_user_config(user_id: str) -> None:
    """确保用户配置存在"""
    with config_lock:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file)
            
        if 'bilibili' not in data:
            data['bilibili'] = {}
            
        if user_id not in data['bilibili']:
            data['bilibili'][user_id] = {
                'cookie': '',
                'sessdata': '',
                'bili_jct': ''
            }
            
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            yaml.dump(data, file)

# basic utils
def get_joiner(language):
    if language in load_key('language_split_with_space'):
        return " "
    elif language in load_key('language_split_without_space'):
        return ""
    else:
        raise ValueError(f"Unsupported language code: {language}")

if __name__ == "__main__":
    print(load_key('language_split_with_space'))
