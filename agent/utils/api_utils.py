import random
import json
import requests
from models import get_api_config

def call_ai_api_stream(messages, temp=0.7, model_name=None, model_pool=None):
    """
    调用AI API获取流式响应，支持多个模型轮换
    messages: 对话消息
    temp: 温度
    model_name: 模型名称
    model_pool: 模型池
    """

    # 如果没有指定模型，从池中随机选择一个
    if model_name is None:
        model_name = random.choice(list(model_pool.keys()))

    # 使用负载均衡获取API配置
    api_config = get_api_config(model_name, model_pool)

    if not api_config:
        print(f"错误: 无法获取API配置: {model_name}")
        yield f"data: {json.dumps({'error': 'API配置错误'}, ensure_ascii=False)}\n\n"
        return

    # model_name 包含供应商名称 比如siliconflow/Pro/deepseek-ai/DeepSeek-V3
    # use_model 只包含模型名称 比如Pro/deepseek-ai/DeepSeek-V3
    use_model = api_config.get("model", model_name.split("/", 1)[1])

    try:
        # 构建通用的请求payload
        payload = {
            "model": use_model,
            "messages": messages,
            "stream": True,  # 启用流式响应
            "max_tokens": 4096,
            "temperature": temp,
            # "top_p": 0.7,
            # "frequency_penalty": 0.5,
        }
        # # 根据不同模型调整参数
        # if model_name in ["siliconflow/Pro/deepseek-ai/DeepSeek-V3", "deepseek/deepseek-chat", "new_api_aliyun/kimi-k2-turbo-preview"]:
        #     payload["top_k"] = 50
        # print(f"DEBUG - 发送流式请求到 {model_name}，URL: {api_config['api_url']}")
        # print(f"DEBUG - Payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")

        response = requests.post(
            api_config["api_url"],
            json=payload,
            headers=api_config["headers"],
            timeout=600,
            stream=True  # 启用流式接收
        )

        # print(f"DEBUG - API响应状态码: {response.status_code}")
        # print(f"DEBUG - API响应头: {dict(response.headers)}")

        if response.status_code != 200:
            error_text = response.text
            print(f"API调用失败，状态码：{response.status_code}")
            print(f"错误信息：{error_text}")
            yield f"data: {json.dumps({'error': f'API调用失败: {response.status_code}'}, ensure_ascii=False)}\n\n"
            return

        # 逐行读取流式响应
        # 参考: https://github.com/psf/requests/blob/main/docs/user/advanced.rst
        # 不使用decode_unicode=True，而是手动decode UTF-8以确保正确处理中文
        for line in response.iter_lines():
            if not line:
                continue

            # 手动UTF-8解码，确保中文正确显示
            try:
                decoded_line = line.decode('utf-8')
            except UnicodeDecodeError as e:
                # print(f"警告 - UTF-8解码失败: {e}")
                continue

            # print(f"DEBUG - 收到行: {decoded_line[:200]}...")

            # SSE格式通常以"data: "开头
            if decoded_line.startswith("data:"):
                # 去掉"data:"前缀，注意可能有空格也可能没有
                data_str = decoded_line[5:].strip()

                # 检查是否是结束标记
                if data_str == "[DONE]":
                    # print("DEBUG - 收到[DONE]标记")
                    yield "data: [DONE]\n\n"
                    break

                if not data_str:
                    continue

                try:
                    data_json = json.loads(data_str)
                    # print(f"DEBUG - 解析JSON成功: {json.dumps(data_json, ensure_ascii=False)[:200]}...")

                    # 提取content
                    if "choices" in data_json and len(data_json["choices"]) > 0:
                        delta = data_json["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            # print(f"DEBUG - 提取到content: {content[:50]}...")
                            # 发送SSE格式的数据
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

                except json.JSONDecodeError as e:
                    # print(f"DEBUG - JSON解析错误: {e}, 数据: {data_str[:200]}")
                    continue

        # print("DEBUG - 流式响应结束")

    except requests.exceptions.ChunkedEncodingError as e:
        error_msg = f"流式传输中断: {str(e)}"
        print(error_msg)
        yield f"data: {json.dumps({'error': '网络连接中断，请重试'}, ensure_ascii=False)}\n\n"
    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接错误: {str(e)}"
        print(error_msg)
        yield f"data: {json.dumps({'error': '无法连接到API服务，请检查网络'}, ensure_ascii=False)}\n\n"
    except Exception as e:
        import traceback
        error_msg = f"API流式调用错误: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


def call_ai_api_stream_with_web_search(messages, temp=0.7, model_name=None, model_pool=None):
    """
    Streamed response with optional Bocha web search augmentation.
    在QA阶段只显示 References (summarized)，但返回完整的搜索数据用于存储。
    """
    from .web_search_pipeline import (
        build_web_context_block,
        decide_web_search_queries,
        pick_large_model_name,
        run_web_search_session,
        summarize_web_docs_with_llm,
    )

    tail = messages[-8:] if isinstance(messages, list) else []
    user_intent = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in tail])[:8000]

    should_search, queries, _reason = decide_web_search_queries(
        user_intent=user_intent, model_pool=model_pool, model_name=pick_large_model_name(model_pool)
    )

    print(f"Web搜索决策: should_search={should_search}, queries={queries}")

    if should_search and queries:
        print(f"🔍 开始执行Web搜索: {len(queries)} 个查询")

    session = run_web_search_session(queries) if should_search else None
    web_block = build_web_context_block(session) if session else ""

    augmented_messages = messages
    if web_block:
        augmented_messages = list(messages)
        augmented_messages.insert(1, {"role": "system", "content": web_block})

    for chunk in call_ai_api_stream(augmented_messages, temp=temp, model_name=model_name, model_pool=model_pool):
        if chunk.strip() == "data: [DONE]":
            break
        yield chunk

    # 处理web搜索结果
    if session and session.all_docs():
        synthesis = summarize_web_docs_with_llm(
            session, model_pool=model_pool, model_name=pick_large_model_name(model_pool)
        )

        # 只显示 References (summarized)，不显示 synthesis 和详细的 web search
        references_only = session.references_markdown(include_per_query_summaries=False)

        if references_only.strip():
            print(f"发送Web搜索引用 ({len(session.all_docs())} 个文档)")
            # 发送显示给用户的内容（只有References）
            # Note: Define newline string outside f-string to avoid backslash syntax error
            separator = '\n\n---\n\n'
            content_data = json.dumps({'content': separator + references_only}, ensure_ascii=False)
            yield f"data: {content_data}\n\n"

        # 发送完整的web搜索元数据用于存储（不显示在UI）
        web_search_metadata = {
            'synthesis': synthesis,
            'references': references_only,
            'queries': queries,
            'doc_count': len(session.all_docs())
        }
        yield f"data: {json.dumps({'web_search_data': web_search_metadata}, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"

def call_ai_api(messages, response_format="text", temp=0.7, model_name=None, model_pool=None):
    """
    调用AI API获取响应，支持多个模型轮换
    messages: 对话消息
    response_format: 响应格式
    temp: 温度
    model_name: 模型名称
    model_pool: 模型池
    """
    
    # 如果没有指定模型，从池中随机选择一个
    if model_name is None:
        model_name = random.choice(list(model_pool.keys()))
    
    # 使用负载均衡获取API配置
    api_config = get_api_config(model_name, model_pool)
    
    if not api_config:
        print(f"错误: 无法获取API配置: {model_name}")
        return f"API配置错误: 无法获取有效的API配置"
    
    # model_name 包含供应商名称 比如siliconflow/Pro/deepseek-ai/DeepSeek-V3
    # use_model 只包含模型名称 比如Pro/deepseek-ai/DeepSeek-V3
    # api_config['model] 也只包含模型名称 比如Pro/deepseek-ai/DeepSeek-V3
    use_model = api_config.get("model", model_name.split("/", 1)[1])

    try:
        if model_name in ["siliconflow/Pro/deepseek-ai/DeepSeek-V3"]:
            # 硅基流动DeepSeek v3调用逻辑
            # 参考文档 https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions
            payload = {
                "model": use_model,
                "messages": messages,
                "stream": False,
                "max_tokens": 4096,
                "temperature": temp,
                # "top_p": 0.7,
                # "top_k": 50,
                # "frequency_penalty": 0.5,
            }
            
            if response_format == "json_object":
                payload["response_format"] = {"type": "json_object"}

            # print(f"DEBUG - 发送请求到 {model_name}，URL: {api_config['api_url']}")
            # print(f"DEBUG - 请求头: {api_config['headers']}")
            # print(f"DEBUG - 请求载荷: {json.dumps(payload, ensure_ascii=False)[:500]}...")

            response = requests.post(
                api_config["api_url"],
                json=payload,
                headers=api_config["headers"],
                timeout=600
            )

            # print(f"DEBUG - API响应状态码: {response.status_code}")
            # print(f"DEBUG - API响应头: {response.headers}")
            # print(f"DEBUG - API原始响应文本: {response.text[:500]}...")

            if response.status_code != 200:
                print(f"API调用失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                raise Exception(f"API调用失败: {response.status_code}, {response.text[:200]}")

            response_json = response.json()
            # print(f"DEBUG - 解析的JSON响应: {json.dumps(response_json, ensure_ascii=False)[:500]}...")
            
            if "choices" not in response_json or len(response_json["choices"]) == 0:
                raise Exception(f"API响应缺少choices字段: {json.dumps(response_json, ensure_ascii=False)[:200]}")
            
            content = response_json["choices"][0]["message"]["content"]

        if model_name in ["deepseek/deepseek-chat"]:
            # deepseek chat调用逻辑
            # 参考文档 https://api-docs.deepseek.com/zh-cn/api/create-chat-completion
            payload = {
                "model": use_model,
                "messages": messages,
                "stream": False,
                "max_tokens": 4096,
                "temperature": temp,
                # "top_p": 0.7,
                # "top_k": 50,
                # "frequency_penalty": 0.5,
            }

            if response_format == "json_object":
                payload["response_format"] = {"type": "json_object"}

            # print(f"DEBUG - 发送请求到 {model_name}，URL: {api_config['api_url']}")
            # print(f"DEBUG - 请求头: {api_config['headers']}")
            # print(f"DEBUG - 请求载荷: {json.dumps(payload, ensure_ascii=False)[:500]}...")

            response = requests.post(
                api_config["api_url"],
                json=payload,
                headers=api_config["headers"],
                timeout=600
            )

            # print(f"DEBUG - API响应状态码: {response.status_code}")
            # print(f"DEBUG - API响应头: {response.headers}")
            # print(f"DEBUG - API原始响应文本: {response.text[:500]}...")

            if response.status_code != 200:
                print(f"API调用失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                raise Exception(f"API调用失败: {response.status_code}, {response.text[:200]}")

            response_json = response.json()
            # print(f"DEBUG - 解析的JSON响应: {json.dumps(response_json, ensure_ascii=False)[:500]}...")

            if "choices" not in response_json or len(response_json["choices"]) == 0:
                raise Exception(f"API响应缺少choices字段: {json.dumps(response_json, ensure_ascii=False)[:200]}")

            content = response_json["choices"][0]["message"]["content"]

        if model_name in ["new_api_aliyun/kimi-k2-turbo-preview"]:
            # 阿里云API kimi模型调用逻辑
            payload = {
                "model": use_model,
                "messages": messages,
                "stream": False,
                "max_tokens": 4096,
                "temperature": temp,
                # "top_p": 0.7,
                # "frequency_penalty": 0.5,
            }

            if response_format == "json_object":
                payload["response_format"] = {"type": "json_object"}

            # print(f"DEBUG - 发送请求到 {model_name}，URL: {api_config['api_url']}")
            # print(f"DEBUG - 请求头: {api_config['headers']}")
            # print(f"DEBUG - 请求载荷: {json.dumps(payload, ensure_ascii=False)[:500]}...")

            response = requests.post(
                api_config["api_url"],
                json=payload,
                headers=api_config["headers"],
                timeout=600
            )

            # print(f"DEBUG - API响应状态码: {response.status_code}")
            # print(f"DEBUG - API响应头: {response.headers}")
            # print(f"DEBUG - API原始响应文本: {response.text[:500]}...")

            if response.status_code != 200:
                print(f"API调用失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                raise Exception(f"API调用失败: {response.status_code}, {response.text[:200]}")

            response_json = response.json()
            # print(f"DEBUG - 解析的JSON响应: {json.dumps(response_json, ensure_ascii=False)[:500]}...")

            if "choices" not in response_json or len(response_json["choices"]) == 0:
                raise Exception(f"API响应缺少choices字段: {json.dumps(response_json, ensure_ascii=False)[:200]}")

            content = response_json["choices"][0]["message"]["content"]

        # 处理JSON响应
        if response_format == "json_object":
            # print(f"DEBUG (call_ai_api) - Raw content received from {model_name}: {content[:500]}...")

            # 清除可能存在的代码块标记
            original_content_before_cleanup = content # 保存清理前的内容
            if "```json" in content or "```" in content:
                import re
                json_matches = re.findall(r'```(?:json)?(.*?)```', content, re.DOTALL)
                if json_matches:
                    content = json_matches[0].strip()
                elif content.startswith("```") and content.endswith("```"):
                    content = content[3:-3].strip()

            try:
                parsed_json = json.loads(content)
                if isinstance(parsed_json, list):
                    # print(f"DEBUG (call_ai_api) - Parsed JSON is a list: {parsed_json}")
                    pass
                elif isinstance(parsed_json, dict):
                    # print(f"DEBUG (call_ai_api) - Parsed JSON is a dict: {parsed_json}")
                    pass
                else:
                    # print(f"DEBUG (call_ai_api) - Parsed JSON is of unexpected type: {type(parsed_json)}")
                    pass

                # print(f"DEBUG (call_ai_api) - JSON parsed successfully from {model_name}.")
                return json.dumps(parsed_json, ensure_ascii=False)
            except json.JSONDecodeError as e:
                # print(f"DEBUG (call_ai_api) - JSONDecodeError from {model_name}: {e}")
                # print(f"DEBUG (call_ai_api) - Content that failed parsing (after cleanup): {content[:500]}...")
                # print(f"DEBUG (call_ai_api) - Original content before cleanup: {original_content_before_cleanup[:500]}...")
                
                # 如果解析失败，返回空对象或数组
                if "产品描述:" in messages[1]["content"] and "用户画像" in messages[1]["content"]:
                    return json.dumps([])
                else:
                    return json.dumps({})
        
        return content
        
    except Exception as e:
        print(f"API调用错误: {str(e)}")
        # 打印更多上下文
        # print(f"DEBUG (call_ai_api) - Error occurred for messages: {messages}")
        if response_format == "json_object":
            # 区分返回类型
            is_persona_request = False
            if "用户画像" in messages[1]["content"]:
                is_persona_request = True
            return json.dumps([]) if is_persona_request else json.dumps({})
        return f"API调用错误: {str(e)}"