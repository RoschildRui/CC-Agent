import os
import glob
import json
import re
import random
import time
import datetime
from typing import Dict, List, Any, Optional
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API调用计数器和上次调用时间
api_call_counter = {}
last_api_call_time = {}
api_locks = {}

def expand_env_vars(obj: Any) -> Any:
    """
    Recursively expand environment variables in strings.
    Supports ${VAR_NAME} syntax.
    """
    if isinstance(obj, str):
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([^}]+)\}'
        def replacer(match):
            var_name = match.group(1)
            return os.getenv(var_name, '')
        return re.sub(pattern, replacer, obj)
    elif isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars(item) for item in obj]
    return obj

def load_model_pool() -> Dict[str, Any]:
    """
    加载所有API提供商的模型配置
    支持多API密钥的负载均衡
    """
    model_pool = {}
    models_base_dir = os.path.join(os.path.dirname(__file__))
    
    print(f"开始加载模型配置，基础目录: {models_base_dir}")
    if not os.path.exists(models_base_dir):
        print(f"警告: 模型目录不存在: {models_base_dir}")
        os.makedirs(models_base_dir, exist_ok=True)
        print(f"已创建模型目录: {models_base_dir}")
        return model_pool
    
    all_items = glob.glob(os.path.join(models_base_dir, '*'))
    provider_dirs = [d for d in all_items if os.path.isdir(d)]
    if not provider_dirs:
        print(f"警告: 未找到任何模型提供商目录")
    
    for provider_dir in provider_dirs:
        if os.path.isdir(provider_dir) and not os.path.basename(provider_dir).startswith("__"):
            provider_name = os.path.basename(provider_dir)
            print(f"处理提供商: {provider_name}")
            
            # 查找该提供商的模型配置文件
            model_config_files = glob.glob(os.path.join(provider_dir, '*.json'))
            if not model_config_files:
                print(f"警告: 在提供商目录中未找到配置文件: {provider_dir}")
            
            for config_file in model_config_files:
                try:
                    print(f"加载配置文件: {config_file}")
                    with open(config_file, 'r', encoding='utf-8') as f:
                        models_config = json.load(f)
                    
                    # Expand environment variables in the config
                    models_config = expand_env_vars(models_config)
                    
                    # 处理配置文件中的每个模型
                    for model_name, model_config in models_config.items():
                        full_model_name = f"{provider_name}/{model_name}"
                        
                        # 判断是新格式(支持多API密钥)还是旧格式
                        if "api_keys" in model_config:
                            # 新格式: 支持多API密钥的负载均衡
                            active_keys = [
                                key_config for key_config in model_config["api_keys"] 
                                if key_config.get("status", "active") == "active"
                            ]
                            
                            if not active_keys:
                                print(f"警告: 模型 {full_model_name} 没有可用的API密钥")
                                continue
                                
                            # 为每个API密钥创建计数器和锁
                            for key_config in active_keys:
                                key_id = f"{full_model_name}:{key_config['api_key']}"
                                api_call_counter[key_id] = 0
                                last_api_call_time[key_id] = 0
                                api_locks[key_id] = threading.Lock()
                            
                            # 添加模型到模型池
                            model_pool[full_model_name] = {
                                "config": model_config,
                                "active_keys": active_keys,
                                "current_key_index": 0
                            }
                        else:
                            # 旧格式: 单个API密钥
                            model_pool[full_model_name] = {
                                "config": {
                                    "api_keys": [{
                                        "api_url": model_config.get("api_url", ""),
                                        "api_key": model_config.get("api_key", ""),
                                        "headers": model_config.get("headers", {}),
                                        "weight": 1,
                                        "rate_limit": 60,
                                        "status": "active"
                                    }],
                                    "model_name": model_name,
                                    "max_tokens": model_config.get("max_tokens", 4096),
                                    "temperature_default": model_config.get("temperature_default", 0.7)
                                },
                                "active_keys": [{
                                    "api_url": model_config.get("api_url", ""),
                                    "api_key": model_config.get("api_key", ""),
                                    "headers": model_config.get("headers", {}),
                                    "weight": 1,
                                    "rate_limit": 60,
                                    "status": "active"
                                }],
                                "current_key_index": 0
                            }
                            
                            # 为API密钥创建计数器和锁
                            key_id = f"{full_model_name}:{model_config.get('api_key', '')}"
                            api_call_counter[key_id] = 0
                            last_api_call_time[key_id] = 0
                            api_locks[key_id] = threading.Lock()
                        
                        print(f"已加载模型: {full_model_name} (有 {len(model_pool[full_model_name]['active_keys'])} 个活跃API密钥)")
                except Exception as e:
                    print(f"加载模型配置文件失败: {config_file}, 错误: {str(e)}")
    
    if not model_pool:
        raise Exception("警告: 未加载任何模型配置")

    else:
        print(f"总共加载了 {len(model_pool)} 个模型配置")
    
    return model_pool

def is_deepseek_time() -> bool:
    """
    检查当前时间是否在凌晨00:30至早上8:30之间
    这个时间段优先使用deepseek提供商的API
    
    Returns:
        是否在指定的时间段内
    """
    current_time = datetime.datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # 00:30 - 08:30 的时间段
    start_time = datetime.time(0, 30)
    end_time = datetime.time(8, 30)
    
    # 创建当前时间的time对象
    current_time_obj = datetime.time(current_hour, current_minute)
    
    # 检查当前时间是否在范围内
    if start_time <= current_time_obj <= end_time:
        return True
    return False

def select_model_by_time(model_name: str, model_pool: Dict[str, Any]) -> str:
    """
    根据时间选择模型
    如果在指定的时间段内(00:30-08:30)并且要使用的模型包含"deepseek"关键词，
    则优先选择deepseek提供商的对应模型
    
    Args:
        model_name: 原始选择的模型名称
        model_pool: 模型配置池
        
    Returns:
        实际应该使用的模型名称
    """
    model_type = model_name.split('/', 1)[1] if '/' in model_name else model_name
    
    # 检查是否在deepseek优先时间段
    if is_deepseek_time() and "deepseek" in model_type.lower():
        # 寻找deepseek提供商的同类型模型
        for available_model in model_pool.keys():
            if available_model.startswith("deepseek/"):
                available_model_type = available_model.split('/', 1)[1]
                
                # 如果找到匹配的模型类型，或者deepseek的任何可用模型
                if "deepseek" in available_model_type.lower():
                    print(f"当前处于凌晨时段(00:30-08:30)，已将模型从 {model_name} 切换为 {available_model}")
                    return available_model
    
    # 如果不在指定时间段或没有找到合适的deepseek模型，保持原模型不变
    return model_name

def get_api_config(model_name: str, model_pool: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    根据模型名称获取API配置，使用负载均衡和速率限制
    
    Args:
        model_name: 模型名称
        model_pool: 模型配置池
        
    Returns:
        API配置字典，包含api_url, api_key, headers等
    """
    # 根据时间段来确定最终使用的模型
    actual_model = select_model_by_time(model_name, model_pool)
    
    if actual_model != model_name:
        print(f"根据时间规则，已将模型从 {model_name} 切换为 {actual_model}")
    
    if actual_model not in model_pool:
        print(f"错误: 未找到模型 {actual_model}")
        return None
    
    model_data = model_pool[actual_model]
    active_keys = model_data["active_keys"]
    
    if not active_keys:
        print(f"错误: 模型 {actual_model} 没有可用的API密钥")
        return None
    
    # 加权随机选择API密钥
    weights = [key_config.get("weight", 1) for key_config in active_keys]
    selected_key = random.choices(active_keys, weights=weights, k=1)[0]
    
    # 检查速率限制
    key_id = f"{actual_model}:{selected_key['api_key']}"
    
    with api_locks[key_id]:
        current_time = time.time()
        time_diff = current_time - last_api_call_time.get(key_id, 0)
        rate_limit = selected_key.get("rate_limit", 60)  # 默认每分钟60个请求
        
        # 如果时间差大于60秒，重置计数器
        if time_diff > 60:
            api_call_counter[key_id] = 0
        
        # 如果达到速率限制，尝试其他密钥
        if api_call_counter.get(key_id, 0) >= rate_limit and time_diff <= 60:
            print(f"警告: API密钥 {key_id} 已达到速率限制，尝试其他密钥")
            
            # 从活跃密钥中排除当前密钥
            other_keys = [key for key in active_keys if key['api_key'] != selected_key['api_key']]
            
            if not other_keys:
                print(f"错误: 没有其他可用的API密钥")
                return None
            
            # 重新加权随机选择
            other_weights = [key_config.get("weight", 1) for key_config in other_keys]
            selected_key = random.choices(other_keys, weights=other_weights, k=1)[0]
            key_id = f"{actual_model}:{selected_key['api_key']}"
            
            # 确保新密钥未达到速率限制
            if api_call_counter.get(key_id, 0) >= rate_limit and time_diff <= 60:
                print(f"错误: 所有API密钥都已达到速率限制")
                return None
        
        # 更新计数器和时间
        api_call_counter[key_id] = api_call_counter.get(key_id, 0) + 1
        last_api_call_time[key_id] = current_time
    
    # 返回API配置
    return {
        "api_url": selected_key["api_url"],
        "api_key": selected_key["api_key"],
        "headers": selected_key["headers"],
        "model": model_data["config"].get("model_name", actual_model.split("/", 1)[1])
    }

if __name__ == "__main__":
    model_pool = load_model_pool()
    print(model_pool)

