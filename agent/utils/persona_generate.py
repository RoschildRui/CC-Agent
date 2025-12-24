import sys
sys.path.append("..")

import random
import time
import json
from .generate_utils import (
    create_existing_personas_context,
    create_error_persona,
    is_valid_persona,
    save_personas_to_file,
    update_task_progress
)
from .api_utils import call_ai_api
from agent.prompt_template import *

def generate_initial_personas(product_desc, existing_personas_context, 
                              num_personas, temperature, model_pool=None):
    """
    生成初始用户画像
    product_desc: 产品描述
    existing_personas_context: 已有用户画像上下文
    num_personas: 需要生成的用户画像数量
    temperature: 温度
    model_pool: 模型池
    """
    messages = [
        {"role": "system", "content": persona_system_prompt},
        {"role": "user", "content": f"""产品描述: {product_desc}
{existing_personas_context}

请帮我生成{num_personas}个用户画像，确保与以上已有画像不重复，并且格式严格符合要求。""".strip()}
    ]
    
    response = call_ai_api(messages, response_format="json_object", temp=temperature, model_pool=model_pool)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        print(f"JSON解析错误, 原始响应: {response[:100]}...")
        return []
    
def get_reviewer_questions(persona, product_desc, model_pool=None):
    """
    获取评审专家的问题
    persona: 用户画像
    product_desc: 产品描述
    model_pool: 模型池
    """
    messages = [
        {"role": "system", "content": persona_reviewer_system_prompt},
        {"role": "user", "content": f"""
请审查以下用户画像，并提出3-5个最关键的问题来完善它：

产品描述：
{product_desc}

用户画像：
{json.dumps(persona, ensure_ascii=False, indent=2)}
        """}
    ]
    
    response = call_ai_api(messages, response_format="json_object", temp=0.8, model_pool=model_pool)
    try:
        result = json.loads(response)
        return result.get("questions", [])
    except json.JSONDecodeError:
        print(f"解析评审问题时出错，原始响应: {response[:100]}...")
        return []

def refine_persona_with_questions(persona, questions, product_desc, temperature, model_pool=None):
    """
    根据评审问题完善用户画像
    persona: 用户画像
    questions: 评审问题
    product_desc: 产品描述
    temperature: 温度
    model_pool: 模型池
    """
    if not questions:
        return persona
    
    # 构造问题文本
    questions_text = "\n".join([
        f"{i+1}. [{q['dimension']}] {q['question']}"
        for i, q in enumerate(questions)
    ])
    
    messages = [
        {"role": "system", "content": persona_system_prompt},
        {"role": "user", "content": f"""
请根据以下问题完善这个用户画像，确保新的画像更加真实、具体和深入：

产品描述：
{product_desc}

当前用户画像：
{json.dumps(persona, ensure_ascii=False, indent=2)}

评审问题：
{questions_text}

请提供完善后的用户画像，保持相同的JSON格式。
        """}
    ]
    
    response = call_ai_api(messages, response_format="json_object", 
                           temp=temperature, model_pool=model_pool)
    try:
        refined = json.loads(response)
        # 保留原始ID和时间戳（如果有）
        if "persona_id" in persona:
            refined["persona_id"] = persona["persona_id"]
        if "generated_at" in persona:
            refined["generated_at"] = persona["generated_at"]
        return refined
    except json.JSONDecodeError:
        print(f"解析完善后的画像时出错，原始响应: {response[:100]}...")
        return persona
    
def generate_user_personas(task_id, product_desc, num_personas, 
                           tasks=None, tasks_file=None, model_pool=None,
                           app=None):
    """
    用于生成用户画像
    task_id: 任务ID
    product_desc: 产品描述
    num_personas: 需要生成的用户画像数量
    tasks: 任务列表
    tasks_file(json): 任务文件路径
    model_pool: 模型池
    app: 应用实例
    """
    tasks[task_id]['status'] = 'generating_personas'
    all_personas = []
    
    # 迭代生成时，每批次生成多少个新的用户画像
    PERSONAS_PER_CALL = 2
    temperatures = [0.8, 0.85, 0.9, 0.95]
    max_retries = 3 # 添加重试机制
    
    # 添加计数器用于生成顺序的persona_id
    persona_counter = 1
    
    while len(all_personas) < num_personas:
        # 显示进度
        completed = len(all_personas)
        tasks[task_id]['progress'] = {
            'current_step': 'personas',
            'completed': completed,
            'total': num_personas,
            'percentage': round((completed / num_personas) * 100, 1)
        }
        
        # 随机选择温度增加多样性
        temp = random.choice(temperatures)
        
        # 构造已有画像上下文
        existing_personas_context = create_existing_personas_context(all_personas)
        
        # 第一阶段：生成初始用户画像
        initial_personas = []
        retry_count = 0
        while retry_count < max_retries and not initial_personas:
            try:
                print(f"尝试生成初始用户画像，尝试 {retry_count + 1}/{max_retries}")
                initial_personas = generate_initial_personas(product_desc, existing_personas_context, 
                                                             PERSONAS_PER_CALL, temp, model_pool=model_pool)
                if not initial_personas or len(initial_personas) == 0:
                    raise ValueError("生成的用户画像为空")
                print(f"成功生成 {len(initial_personas)} 个初始画像")
            except Exception as e:
                retry_count += 1
                print(f"生成初始用户画像失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                time.sleep(1)
                if retry_count >= max_retries:
                    print(f"达到最大重试次数，添加 {PERSONAS_PER_CALL} 个错误替代画像")
                    for i in range(PERSONAS_PER_CALL):
                        error_persona = create_error_persona(persona_counter, str(e))
                        all_personas.append(error_persona)
                        persona_counter += 1
                    break
        
        if not initial_personas:
            continue
            
        # 第二阶段：对每个生成的画像进行深度审查和完善
        refined_personas = []
        for i, persona in enumerate(initial_personas):
            print(f"开始完善画像 {i+1}/{len(initial_personas)}")
            
            # 获取评审问题
            reviewer_questions = []
            retry_count = 0
            while retry_count < max_retries and not reviewer_questions:
                try:
                    reviewer_questions = get_reviewer_questions(persona, product_desc, model_pool=model_pool)
                    if not reviewer_questions:
                        raise ValueError("获取评审问题失败")
                except Exception as e:
                    retry_count += 1
                    print(f"获取评审问题失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(1)
                    if retry_count >= max_retries:
                        # 如果获取问题失败，使用空问题列表继续
                        reviewer_questions = []
                        break
            
            # 完善用户画像
            refined_persona = None
            retry_count = 0
            while retry_count < max_retries and not refined_persona:
                try:
                    refined_persona = refine_persona_with_questions(persona, reviewer_questions, 
                                                                    product_desc, temp, 
                                                                    model_pool=model_pool)
                    if not refined_persona:
                        raise ValueError("完善用户画像失败")
                except Exception as e:
                    retry_count += 1
                    print(f"完善用户画像失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(1)
                    if retry_count >= max_retries:
                        # 如果完善失败，使用原始画像
                        refined_persona = persona
                        break
            
            if refined_persona:
                refined_personas.append(refined_persona)
            
            # 每个画像处理后增加间隔
            time.sleep(2)
        
        # 第三阶段：验证和添加有效画像
        valid_count = 0
        for i, persona in enumerate(refined_personas):
            if is_valid_persona(persona):
                # 使用计数器生成顺序的persona_id
                persona["persona_id"] = f"persona_{persona_counter}"
                persona["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                all_personas.append(persona)
                valid_count += 1
                persona_counter += 1  # 递增计数器
            else:
                print(f"画像验证失败: {json.dumps(persona, ensure_ascii=False)[:200]}...")
        
        print(f"本批次添加了 {valid_count} 个有效画像，当前总数: {len(all_personas)}/{num_personas}")
        
        # 每次迭代后暂停以避免速率限制
        time.sleep(1)
    
    # 保留所需数量的画像
    all_personas = all_personas[:num_personas]
    save_personas_to_file(task_id, all_personas, app=app)
    update_task_progress(task_id, num_personas, tasks=tasks)
    
    return all_personas