import random
import time
import os
import json
import uuid

def create_existing_personas_context(all_personas):
    """
    创建已有用户画像的上下文信息
    all_personas: 所有用户画像列表
    """
    if not all_personas:
        return ""
    
    sample_size = min(10, len(all_personas))
    sampled = random.sample(all_personas, sample_size)
    existing_personas_texts = []
    
    for p in sampled:
        desc = p.get("persona_description", "无描述")
        user_type = p.get("user_type", "未知")
        freq = p.get("usage_frequency", "未知")
        existing_personas_texts.append(f"• {desc} (类型: {user_type}, 频率: {freq})")
    
    return "\n已有用户画像示例：\n" + "\n".join(existing_personas_texts)

def create_error_persona(index, error_msg):
    """
    创建错误时的替代用户画像
    index: 错误索引
    error_msg: 错误信息
    """
    return {
        "persona_id": f"error_stub_{index}",
        "persona_description": "生成出错的替代画像",
        "key_needs": ["未知需求"],
        "usage_scenarios": ["未知场景"],
        "user_type": "未知",
        "usage_frequency": "未知",
        "location": "未知地区",
        "would_recommend": False,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "error": error_msg
    }

def is_valid_persona(persona):
    """
    验证用户画像是否有效
    persona: 用户画像
    """
    required_fields = {
        "persona_description": str,
        "key_needs": list,
        "usage_scenarios": list,
        "user_type": str,
        "usage_frequency": str,
        "location": str,
    }
    
    try:
        # 检查必要字段
        for field, field_type in required_fields.items():
            if field not in persona:
                return False
            if not isinstance(persona[field], field_type):
                return False
        
        # 检查用户类型是否有效
        valid_user_types = ["核心用户", "边缘用户", "潜在用户", "非目标用户", "未知"]
        if persona["user_type"] not in valid_user_types:
            return False
        
        # 检查使用频率是否有效
        valid_frequencies = ["每天多次", "每天一次", "每周几次", "每周一次", "每月几次", "每月一次", "偶尔使用", "几乎不使用", "未知"]
        if persona["usage_frequency"] not in valid_frequencies:
            return False
        
        # 检查location是否为空
        if not persona["location"] or persona["location"].strip() == "":
            return False
        
        return True
    except Exception:
        return False
    
def save_personas_to_file(task_id, personas, app=None):
    """
    保存用户画像到文件
    task_id: 任务ID
    personas: 用户画像列表
    app: 应用实例
    """
    personas_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_personas.json")
    with open(personas_file, 'w', encoding='utf-8') as f:
        json.dump(personas, f, ensure_ascii=False, indent=2)

def update_task_progress(task_id, num_personas, tasks=None):
    """
    更新任务进度
    task_id: 任务ID
    num_personas: 用户画像数量
    tasks: 任务列表
    """
    tasks[task_id]['progress'] = {
        'current_step': 'personas',
        'completed': num_personas,
        'total': num_personas,
        'percentage': 100
    }

def create_error_result(persona_id, error_msg, error_detail, sim_index=0,
                         instance_id="", user_type="未知", usage_frequency="未知"):
    """
    创建错误时的替代模拟结果
    persona_id: 用户画像ID
    error_msg: 错误信息
    error_detail: 错误详情
    sim_index: 模拟索引
    instance_id: 实例ID
    user_type: 用户类型
    usage_frequency: 使用频率
    """
    # 生成唯一的错误结果ID
    if instance_id:
        simulation_id = f"{persona_id}_{instance_id}_sim_{sim_index}_error" if sim_index > 0 else f"{persona_id}_{instance_id}_error"
    else:
        # 使用随机字符串确保唯一性
        random_id = str(uuid.uuid4())[:6]
        simulation_id = f"{persona_id}_{random_id}_sim_{sim_index}_error" if sim_index > 0 else f"{persona_id}_{random_id}_error"
    
    return {
        "error": error_detail,
        "simulation_id": simulation_id,
        "persona_id": persona_id,
        "user_type": user_type,
        "usage_frequency": usage_frequency,
        "simulated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "initial_impression": "模拟出错",
        "perceived_needs": "模拟出错",
        "would_try": False,
        "would_buy": False,
        "is_must_have": False,
        "would_recommend": False,
        "dependency_level": "无所谓",
        "alternatives": ["无法确定"],
        "barrier_to_adoption": "模拟出错",
        "feedback": f"{error_msg}",
        "suggested_improvements": "由于模拟出错，无法提供改进建议"
    }

def clean_persona_data(persona):
    """
    清理用户画像数据，确保格式正确
    persona: 用户画像
    """
    # 清理key_needs字段
    if "key_needs" in persona:
        if not isinstance(persona["key_needs"], list):
            persona["key_needs"] = ["未知需求"]
        else:
            # 清除null和空字符串
            cleaned_needs = [need for need in persona["key_needs"] if need and need != ""]
            if not cleaned_needs:
                cleaned_needs = ["未知需求"]
            persona["key_needs"] = cleaned_needs
    else:
        persona["key_needs"] = ["未知需求"]
    
    # 清理usage_scenarios字段
    if "usage_scenarios" in persona:
        if not isinstance(persona["usage_scenarios"], list):
            persona["usage_scenarios"] = ["未知场景"]
        else:
            # 清除null和空字符串
            cleaned_scenarios = [scenario for scenario in persona["usage_scenarios"] if scenario and scenario != ""]
            if not cleaned_scenarios:
                cleaned_scenarios = ["未知场景"]
            persona["usage_scenarios"] = cleaned_scenarios
    else:
        persona["usage_scenarios"] = ["未知场景"]
    
    return persona

def process_simulation_result(result, persona, persona_id, sim_index, instance_id=""):
    """
    处理模拟结果，确保所有字段格式正确
    result: 模拟结果
    persona: 用户画像
    persona_id: 用户画像ID
    sim_index: 模拟索引
    instance_id: 实例ID
    """
    # 清理可能存在的元数据字段（以_开头的字段）
    metadata_keys = [k for k in result.keys() if k.startswith('_')]
    if metadata_keys:
        print(f"DEBUG - 检测到元数据字段: {metadata_keys}")
        # 如果存在_final_corrected_version_for_production字段，尝试使用它的内容
        if '_final_corrected_version_for_production' in result and isinstance(result['_final_corrected_version_for_production'], dict):
            print(f"DEBUG - 使用_final_corrected_version_for_production字段内容替换原始响应")
            final_version = dict(result['_final_corrected_version_for_production'])
            for k, v in final_version.items():
                result[k] = v
        
        # 删除所有元数据字段
        for key in metadata_keys:
            print(f"DEBUG - 删除元数据字段: {key}")
            del result[key]
    
    # 确保结果包含所需字段
    required_fields = ["initial_impression", "perceived_needs", "would_try", "would_buy", 
                       "is_must_have", "would_recommend", "dependency_level", "alternatives", "barrier_to_adoption", 
                       "feedback", "suggested_improvements"]
    for field in required_fields:
        if field not in result:
            if field in ["would_try", "would_buy", "is_must_have", "would_recommend"]:
                result[field] = False
            elif field == "dependency_level":
                result[field] = "无所谓"
            elif field == "alternatives":
                result[field] = []
            elif field == "suggested_improvements":
                result[field] = "未提供改进建议"
            else:
                result[field] = "未提供"
    
    # 特别处理alternatives字段，确保它始终是一个列表
    if not isinstance(result["alternatives"], list):
        # 如果是一个字符串，将其转换为单元素列表
        if isinstance(result["alternatives"], str):
            if result["alternatives"]:
                result["alternatives"] = [result["alternatives"]]
            else:
                result["alternatives"] = []
        # 如果是其他类型，设置为空列表
        else:
            print(f"alternatives字段类型错误: {type(result['alternatives'])}")
            result["alternatives"] = []
    
    # 检查布尔值字段，确保它们是布尔类型
    for bool_field in ["would_try", "would_buy", "is_must_have"]:
        if not isinstance(result[bool_field], bool):
            # 尝试转换字符串 "true"/"false" 为布尔值
            if isinstance(result[bool_field], str):
                if result[bool_field].lower() == "true":
                    result[bool_field] = True
                else:
                    result[bool_field] = False
            # 其他类型转为布尔值
            else:
                try:
                    result[bool_field] = bool(result[bool_field])
                except:
                    result[bool_field] = False
    
    # 校验dependency_level字段
    valid_dependency_levels = ["痛苦", "可以接受", "无所谓"]
    if result["dependency_level"] not in valid_dependency_levels:
        original_val = result["dependency_level"]
        result["dependency_level"] = "无所谓"
        print(f"DEBUG - 依赖程度值异常: '{original_val}' 已替换为'无所谓'")
    
    # 添加用户类型和使用频率信息（直接使用persona中的值）
    result["user_type"] = persona.get("user_type", "未知")
    result["usage_frequency"] = persona.get("usage_frequency", "未知")
    
    # 标准化用户类型和使用频率
    valid_user_types = ["核心用户", "边缘用户", "潜在用户", "非目标用户", "未知"]
    if result["user_type"] not in valid_user_types:
        result["user_type"] = "未知"
    
    valid_frequencies = ["每天多次", "每天一次", "每周几次", "每周一次", "每月几次", "每月一次", "偶尔使用", "几乎不使用", "未知"]
    if result["usage_frequency"] not in valid_frequencies:
        result["usage_frequency"] = "未知"
    
    # 添加ID和时间戳，确保唯一性
    if instance_id:
        result["simulation_id"] = f"{persona_id}_{instance_id}_sim_{sim_index}"
    else:
        # 生成随机字符串作为备用
        random_id = str(uuid.uuid4())[:6]
        result["simulation_id"] = f"{persona_id}_{random_id}_sim_{sim_index}"
    
    result["persona_id"] = persona_id
    result["simulated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return result

def fill_missing_results(simulation_results, persona_id, persona, num_simulations, instance_id=""):
    """
    填充缺失的模拟结果以达到要求的数量
    simulation_results: 模拟结果列表
    persona_id: 用户画像ID
    persona: 用户画像
    num_simulations: 要求的模拟数量
    instance_id: 实例ID
    """
    missing_count = num_simulations - len(simulation_results)
    for i in range(missing_count):
        # 生成唯一的填充结果ID
        if instance_id:
            simulation_id = f"{persona_id}_{instance_id}_sim_filler_{i+1}"
        else:
            # 使用随机字符串确保唯一性
            random_id = str(uuid.uuid4())[:6]
            simulation_id = f"{persona_id}_{random_id}_sim_filler_{i+1}"
        
        filler_result = {
            "error": "模拟结果数量不足，自动填充",
            "simulation_id": simulation_id,
            "persona_id": persona_id,
            "user_type": persona.get("user_type", "未知"),
            "usage_frequency": persona.get("usage_frequency", "未知"),
            "simulated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "initial_impression": "自动填充的模拟结果",
            "perceived_needs": "无法确定",
            "would_try": False,
            "would_buy": False,
            "is_must_have": False,
            "would_recommend": False,
            "dependency_level": "无所谓",
            "alternatives": ["无法确定"],
            "barrier_to_adoption": "自动填充的模拟结果",
            "feedback": "这是一个自动填充的模拟结果，用于维持预期的模拟数量",
            "suggested_improvements": "这是一个自动填充的模拟结果，用于维持预期的模拟数量"
        }
        simulation_results.append(filler_result)