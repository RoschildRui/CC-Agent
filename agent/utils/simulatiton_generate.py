import sys
sys.path.append("..")

import concurrent.futures
import random
import time
import uuid
import json
from .generate_utils import (
    create_error_result,
    clean_persona_data,
    process_simulation_result,
    fill_missing_results
)
from .api_utils import call_ai_api
from agent.prompt_template import *

def _inject_web_context(messages, web_context: str):
    if web_context:
        # Insert early so the model can use it as evidence.
        messages = list(messages)
        messages.insert(1, {"role": "system", "content": web_context})
    return messages


def simulate_initial_reaction(persona, product_desc,
                              model_name, model_pool=None, web_context: str = ""):
    """进行初步的用户反应模拟
    persona: 用户画像
    product_desc: 产品描述
    model_name: 模型名称
    model_pool: 模型池
    """
    messages = [
        {"role": "system", "content": simulation_system_prompt},
        {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

产品描述: 
{product_desc}

请完全从上述用户画像描述的人的角度，评估这个产品对你的价值和吸引力。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    response = call_ai_api(messages, response_format="json_object",
                           model_name=model_name, model_pool=model_pool)
    
    # 清理可能存在的不必要前缀或后缀
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    
    try:
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        print(f"JSON解析错误，响应内容: {response[:100]}...")
        raise ValueError("无法解析初步模拟的JSON响应")

def generate_inquiry_questions(persona, product_desc, initial_result,
                               model_name, model_pool=None, web_context: str = ""):
    """
    生成对初步模拟结果的质疑问题
    persona: 用户画像
    product_desc: 产品描述
    initial_result: 初步模拟结果
    model_name: 模型名称
    model_pool: 模型池
    """
    
    messages = [
        {"role": "system", "content": inquiry_system_prompt},
        {"role": "user", "content": f"""
用户画像：
{persona['persona_description']}

产品描述：
{product_desc}

初步反馈：
{json.dumps(initial_result, ensure_ascii=False, indent=2)}

请提出3-5个关键问题，帮助进一步挖掘用户对此产品的真实反应和感受。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    response = call_ai_api(messages, response_format="json_object",
                           model_name=model_name, model_pool=model_pool)
    
    try:
        result = json.loads(response)
        return result.get("questions", [])
    except (json.JSONDecodeError, AttributeError, KeyError):
        print(f"生成质疑问题时出错，返回空问题列表")
        return []

def simulate_refined_reaction(persona, product_desc, initial_result,
                               inquiry_questions, model_name, model_pool=None, web_context: str = ""):
    """
    基于初步结果和质疑问题，进行深入的二次模拟
    persona: 用户画像
    product_desc: 产品描述
    initial_result: 初步模拟结果
    inquiry_questions: 质疑问题
    model_name: 模型名称
    model_pool: 模型池
    """
    # 如果没有问题，直接返回初步结果
    if not inquiry_questions:
        return initial_result
    
    # 构造问题文本
    questions_text = "\n".join([
        f"{i+1}. [{q.get('aspect', '深入探讨')}] {q.get('question', '')}"
        for i, q in enumerate(inquiry_questions)
    ])
    
    messages = [
        {"role": "system", "content": refined_system_prompt},
        {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

产品描述: 
{product_desc}

你的初步反应:
{json.dumps(initial_result, ensure_ascii=False, indent=2)}

请基于以下深入问题，重新思考你对产品的评估:
{questions_text}

请全面思考这些问题，给出更深入、更真实的反馈。返回完整的JSON对象，包含所有必需字段。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    response = call_ai_api(messages, response_format="json_object",
                            model_name=model_name, model_pool=model_pool)
    
    # 清理可能存在的不必要前缀或后缀
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    
    try:
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        print(f"JSON解析错误，响应内容: {response[:100]}...")
        print("返回初步模拟结果作为备选")
        return initial_result

def generate_ad_copy(persona, product_desc, user_feedback, model_name, model_pool=None, web_context: str = ""):
    """
    生成针对用户痛点的广告文案
    persona: 用户画像
    product_desc: 产品描述
    user_feedback: 用户反馈
    model_name: 模型名称
    model_pool: 模型池
    """
    # 第一步：生成初始广告文案
    messages = [
        {"role": "system", "content": ad_generation_system_prompt},
        {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

产品描述: 
{product_desc}

用户反馈:
{json.dumps(user_feedback, ensure_ascii=False, indent=2)}

请生成一个直击用户痛点的广告文案，可以适当引入争议性话题或反常识观点，但要确保与产品价值相关且能引发有价值的讨论。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    initial_ad = call_ai_api(messages, response_format="json_object",
                             model_name=model_name, model_pool=model_pool)
    try:
        initial_ad = json.loads(initial_ad)
    except json.JSONDecodeError:
        print(f"广告文案JSON解析错误，返回空结果")
        return {
            "ad_headline": "生成失败",
            "ad_body": "生成失败",
            "key_pain_points": [],
            "target_emotions": [],
            "controversial_point": "",
            "discussion_angle": ""
        }
    
    # 第二步：获取评审问题
    messages = [
        {"role": "system", "content": ad_reviewer_system_prompt},
        {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

产品描述: 
{product_desc}

用户反馈:
{json.dumps(user_feedback, ensure_ascii=False, indent=2)}

初始广告文案:
{json.dumps(initial_ad, ensure_ascii=False, indent=2)}

请特别关注争议性内容的处理，提出改进建议。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    review_questions = call_ai_api(messages, response_format="json_object",
                                    model_name=model_name, model_pool=model_pool)
    try:
        review_questions = json.loads(review_questions)
        questions = review_questions.get("questions", [])
    except json.JSONDecodeError:
        print(f"评审问题JSON解析错误，使用初始广告文案")
        return initial_ad
    
    # 第三步：改进广告文案
    if questions:
        questions_text = "\n".join([
            f"{i+1}. [{q.get('dimension', '改进建议')}] {q.get('question', '')}"
            for i, q in enumerate(questions)
        ])
        
        messages = [
            {"role": "system", "content": ad_generation_system_prompt},
            {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

产品描述: 
{product_desc}

用户反馈:
{json.dumps(user_feedback, ensure_ascii=False, indent=2)}

初始广告文案:
{json.dumps(initial_ad, ensure_ascii=False, indent=2)}

请根据以下问题改进广告文案，特别关注争议性内容的处理:
{questions_text}
            """}
        ]
        
        messages = _inject_web_context(messages, web_context)
        improved_ad = call_ai_api(messages, response_format="json_object",
                                   model_name=model_name, model_pool=model_pool)
        try:
            return json.loads(improved_ad)
        except json.JSONDecodeError:
            print(f"改进后的广告文案JSON解析错误，返回初始广告文案")
            return initial_ad
    
    return initial_ad

def optimize_product_description(persona, product_desc, user_feedback,
                                  model_name, model_pool=None, web_context: str = ""):
    """
    优化产品描述
    persona: 用户画像
    product_desc: 产品描述
    user_feedback: 用户反馈
    model_name: 模型名称
    model_pool: 模型池
    """
    messages = [
        {"role": "system", "content": product_optimization_system_prompt},
        {"role": "user", "content": f"""
用户画像: 
{persona['persona_description']}

当前产品描述: 
{product_desc}

用户反馈:
{json.dumps(user_feedback, ensure_ascii=False, indent=2)}

请提供优化后的产品描述和改进建议。
        """}
    ]
    
    messages = _inject_web_context(messages, web_context)
    response = call_ai_api(messages, response_format="json_object",
                           model_name=model_name, model_pool=model_pool)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        print(f"产品优化JSON解析错误，返回空结果")
        return {
            "optimized_description": product_desc,
            "key_improvements": [],
            "expected_benefits": [],
            "implementation_priority": "中"
        }

# 模拟用户对产品的反应              
def simulate_user_reactions(task_id, product_desc, persona, num_simulations, model_pool=None, web_context: str = ""):
    """
    对单个用户画像进行多次模拟，获取用户反应，使用并行模拟提高速度
    task_id: 任务ID
    product_desc: 产品描述
    persona: 用户画像
    num_simulations: 模拟次数
    """
    # 首先确保persona是有效的字典
    if not isinstance(persona, dict):
        print(f"用户画像格式错误: {type(persona)}，无法进行模拟")
        error_result = create_error_result("unknown", "用户画像格式错误", f"用户画像格式错误: {type(persona)}")
        return [error_result for _ in range(num_simulations)]
    
    # 确保persona包含用户描述
    if "persona_description" not in persona or not persona["persona_description"] or persona["persona_description"] == "未提供":
        print(f"用户画像 {persona.get('persona_id', 'unknown')} 缺少必要字段或字段为空: persona_description，无法进行模拟")
        error_result = create_error_result(
            persona.get('persona_id', 'unknown'),
            "用户画像缺少必要字段",
            "用户画像缺少必要字段或字段为空: persona_description"
        )
        return [error_result for _ in range(num_simulations)]
    
    # 清理persona数据
    persona = clean_persona_data(persona)
    
    # 获取安全的persona_id，确保它是字符串
    persona_id = str(persona.get('persona_id', f"unknown_{random.randint(1000, 9999)}"))
    
    # 批次重试机制
    max_batch_retries = 3
    batch_retry_count = 0
    valid_simulation_results = False
    
    while batch_retry_count < max_batch_retries and not valid_simulation_results:
        if batch_retry_count > 0:
            print(f"批次模拟失败，正在进行第 {batch_retry_count}/{max_batch_retries} 次重试...")
            time.sleep(2)  # 重试前暂停2秒
        
        # 生成一个随机的唯一标识符，用于确保同一个用户画像的不同模拟实例有唯一ID
        simulation_instance_id = str(uuid.uuid4())[:8]
        
        # 创建用于存储结果的列表
        simulation_results = []
        
        # 创建并行执行的函数
        def run_single_simulation(sim_index):
            print(f"DEBUG - 开始模拟用户 {persona_id} (第 {sim_index+1}/{num_simulations} 次)")
            
            # 从MODEL_POOL中随机选择一个模型
            model_name = random.choice(list(model_pool.keys()))
            print(f"DEBUG - 使用模型: {model_name}")
            
            try:
                # 第一步：初步模拟用户反应
                initial_result = simulate_initial_reaction(
                    persona, product_desc, model_name, model_pool=model_pool, web_context=web_context
                )
                print(f"DEBUG - 完成初步模拟")
                
                # 第二步：让模型自我质疑，提出需要深入考虑的问题
                inquiry_questions = generate_inquiry_questions(
                    persona, product_desc, initial_result, model_name, model_pool=model_pool, web_context=web_context
                )
                print(f"DEBUG - 生成了 {len(inquiry_questions)} 个深入探讨的问题")
                
                # 第三步：基于问题，进行深入模拟
                refined_result = simulate_refined_reaction(
                    persona,
                    product_desc,
                    initial_result,
                    inquiry_questions,
                    model_name,
                    model_pool=model_pool,
                    web_context=web_context,
                )
                print(f"DEBUG - 完成深入模拟")
                
                # 第四步：生成广告文案
                ad_result = generate_ad_copy(
                    persona, product_desc, refined_result, model_name, model_pool=model_pool, web_context=web_context
                )
                print(f"DEBUG - 完成广告文案生成")
                
                # 第五步：优化产品描述
                optimized_product = optimize_product_description(
                    persona, product_desc, refined_result, model_name, model_pool=model_pool, web_context=web_context
                )
                print(f"DEBUG - 完成产品优化")
                
                # 合并所有结果
                final_result = {
                    **refined_result,
                    "ad_copy": ad_result,
                    "optimized_product": optimized_product
                }
                
                # 处理结果，确保所有字段格式正确
                result = process_simulation_result(final_result, persona, persona_id, sim_index+1, simulation_instance_id)
                
                return result
                
            except Exception as e:
                print(f"模拟用户 {persona_id} 反应 {sim_index+1} 时出错: {str(e)}")
                error_result = create_error_result(
                    persona_id, 
                    f"模拟过程中出错: {str(e)}", 
                    str(e),
                    sim_index=sim_index+1,
                    instance_id=simulation_instance_id,
                    user_type=persona.get("user_type", "未知"),
                    usage_frequency=persona.get("usage_frequency", "未知")
                )
                return error_result
        
        try:
            # 使用线程池并行执行模拟
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_simulations, 5)) as executor:
                # 提交所有任务到线程池
                future_to_index = {executor.submit(run_single_simulation, i): i for i in range(num_simulations)}
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_index):
                    try:
                        result = future.result()
                        simulation_results.append(result)
                    except Exception as e:
                        index = future_to_index[future]
                        print(f"处理模拟结果 {index+1} 时出错: {str(e)}")
                        error_result = create_error_result(
                            persona_id,
                            f"处理结果时出错: {str(e)}",
                            str(e),
                            sim_index=index+1,
                            instance_id=simulation_instance_id,
                            user_type=persona.get("user_type", "未知"),
                            usage_frequency=persona.get("usage_frequency", "未知")
                        )
                        simulation_results.append(error_result)
            
            # 验证批次结果
            format_errors = 0
            for result in simulation_results:
                # 检查是否包含错误信息且与JSON格式相关
                if "error" in result and any(err in result["error"] for err in ["JSON", "json", "格式"]):
                    format_errors += 1
            
            # 如果格式错误超过10%，认为这个批次失败，需要重试
            if format_errors > (len(simulation_results) / 10):
                print(f"批次中格式错误数量过多: {format_errors}/{len(simulation_results)}，需要重试")
                batch_retry_count += 1
                # 清空结果，准备重试
                simulation_results = []
            else:
                # 批次有效，跳出重试循环
                valid_simulation_results = True
                print(f"批次模拟成功，有效结果: {len(simulation_results) - format_errors}/{len(simulation_results)}")
                
        except Exception as e:
            print(f"批次模拟过程中出错: {str(e)}")
            batch_retry_count += 1
    
    # 如果达到最大重试次数仍未成功，创建错误结果
    if not valid_simulation_results:
        print(f"达到最大批次重试次数 {max_batch_retries}，返回错误结果")
        simulation_results = []
        for i in range(num_simulations):
            error_result = create_error_result(
                persona_id,
                f"批次模拟失败，达到最大重试次数 {max_batch_retries}",
                f"无法在 {max_batch_retries} 次尝试内获取有效的模拟结果",
                sim_index=i+1,
                instance_id=str(uuid.uuid4())[:8],
                user_type=persona.get("user_type", "未知"),
                usage_frequency=persona.get("usage_frequency", "未知")
            )
            simulation_results.append(error_result)
    
    # 确保返回足够数量的结果
    if len(simulation_results) < num_simulations:
        fill_missing_results(simulation_results, persona_id, persona, num_simulations, simulation_instance_id)
    
    return simulation_results
