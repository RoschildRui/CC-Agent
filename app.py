import os
import json
import time
import uuid
import datetime
import threading
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, abort, Response, stream_with_context
from werkzeug.utils import secure_filename
from email.header import Header
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent import(
    run_analysis_task,
    generate_user_personas,
    simulate_user_reactions,
    save_tasks,
    load_tasks,
    update_task_status,
    stop_task,
    call_ai_api,
    call_ai_api_stream,
    call_ai_api_stream_with_web_search,
    save_conversation,
    extract_product_description,
    send_report_email,
    send_payment_notification,
    verify_and_use_invite_code,
    increment_invite_code_usage,
    is_vip_user,
    system_prompt,
    persona_system_prompt,
    persona_reviewer_system_prompt,
    simulation_system_prompt,
    inquiry_system_prompt,
    refined_system_prompt,
    ad_generation_system_prompt,
    ad_reviewer_system_prompt,
    product_optimization_system_prompt,
)
from models import load_model_pool

# 创建Flask应用
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'change-this-in-production')

# Admin password for protected endpoints
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data')
app.config['REPORTS_FOLDER'] = os.path.join(os.path.dirname(__file__), 'reports')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'conversations'), exist_ok=True)

# 用于存储分析任务状态
tasks = {}
# 用于存储任务中止标志
task_stop_flags = {}

# 任务数据持久化文件路径
TASKS_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'tasks.json')
# 对话历史文件夹路径
CONVERSATIONS_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'conversations')

# 启动时加载任务数据
tasks = load_tasks(tasks_file=TASKS_FILE)
MODEL_POOL = load_model_pool()

# 添加中止任务的API
@app.route('/api/task/<task_id>/stop', methods=['POST'])
def stop_task_api(task_id):
    # 添加一个简单的密码保护
    key = request.args.get('key')
    if key != ADMIN_PASSWORD:
        return jsonify({'error': '未授权访问'}), 403
        
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    if tasks[task_id]['status'] in ['completed', 'failed', 'stopped']:
        return jsonify({'error': '任务已结束'}), 400
    
    if stop_task(task_id, tasks=tasks, tasks_file=TASKS_FILE, task_stop_flags=task_stop_flags):
        return jsonify({'message': '任务已中止'})
    else:
        return jsonify({'error': '中止任务失败'}), 500

# 添加重启任务的API
@app.route('/api/task/<task_id>/restart', methods=['POST'])
def restart_task_api(task_id):
    # 添加一个简单的密码保护
    key = request.args.get('key')
    if key != ADMIN_PASSWORD:
        return jsonify({'error': '未授权访问'}), 403
        
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 只有失败或已中止的任务可以重启
    if task['status'] not in ['failed', 'stopped']:
        return jsonify({'error': '只能重启失败或已中止的任务'}), 400
    
    # 重置任务状态
    task['status'] = 'pending'
    task['progress'] = {'percentage': 0}
    task.pop('error', None)  # 移除错误信息
    save_tasks(tasks=tasks, tasks_file=TASKS_FILE)
    
    # 启动新的后台任务
    thread = threading.Thread(
        target=run_analysis_task, 
        args=(task_id, task['product_description'], 
              task['num_personas'], task['num_simulations'],
              tasks, task_stop_flags,
              TASKS_FILE, MODEL_POOL, app)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': '任务已重启'})

# 首页路由
@app.route('/')
def index():
    return render_template('index.html')

# 步骤1：产品描述
@app.route('/step1', methods=['GET', 'POST'])
def step1():
    # 处理POST请求（用于页面刷新后保持对话状态）
    if request.method == 'POST' and 'conversation' in request.form:
        conversation_json = request.form['conversation']
        conversation = json.loads(conversation_json)

        # 检查是否有产品描述
        has_product_description = False
        for msg in conversation:
            if msg.get('role') == 'assistant' and '【产品描述】' in msg.get('content', ''):
                has_product_description = True
                break

        return render_template('step1.html',
                              conversation=conversation,
                              conversation_json=conversation_json,
                              system_prompt=system_prompt,
                              has_product_description=has_product_description)

    # GET请求：返回初始状态
    initial_conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": "您好！我是您的产品顾问。请描述一下您正在构思的产品，我会帮助您优化产品定义。"}
    ]
    return render_template('step1.html',
                          conversation=initial_conversation,
                          conversation_json=json.dumps(initial_conversation),
                          system_prompt=system_prompt,
                          has_product_description=False)

# 流式响应端点
@app.route('/step1/stream', methods=['POST'])
def step1_stream():
    conversation = json.loads(request.form['conversation'])

    def generate():
        full_response = ""
        web_search_metadata = None  # 存储web搜索元数据
        try:
            for chunk in call_ai_api_stream_with_web_search(conversation, model_pool=MODEL_POOL):
                yield chunk
                # 从chunk中提取内容以构建完整响应
                if chunk.startswith("data: "):
                    data_str = chunk[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            data = json.loads(data_str)
                            if 'content' in data:
                                full_response += data['content']
                            # 捕获web搜索元数据（不显示在UI）
                            if 'web_search_data' in data:
                                web_search_metadata = data['web_search_data']
                        except:
                            pass

            # 检查是否包含产品描述
            has_product_description = "【产品描述】" in full_response
            if has_product_description:
                # 生成临时任务ID并保存对话
                temp_task_id = str(uuid.uuid4())
                conversation.append({"role": "assistant", "content": full_response})

                # 如果有web搜索元数据，保存到单独的文件
                if web_search_metadata:
                    web_search_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{temp_task_id}_web_search.json")
                    with open(web_search_file, 'w', encoding='utf-8') as f:
                        json.dump(web_search_metadata, f, ensure_ascii=False, indent=2)
                    print(f"Web搜索元数据已保存: {web_search_file}")

                save_conversation(temp_task_id, conversation, conversation_file=CONVERSATIONS_FOLDER)
                # 发送任务ID
                yield f"data: {json.dumps({'task_id': temp_task_id, 'has_product_description': True})}\n\n"
        except Exception as e:
            import traceback
            print(f"Stream错误: {str(e)}")
            print(f"错误堆栈: {traceback.format_exc()}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


# 步骤2：用户画像分析
@app.route('/step2', methods=['GET', 'POST'])
def step2():
    if request.method == 'POST':
        # 获取产品描述和用户邮箱
        conversation = json.loads(request.form['conversation'])
        
        # 从对话中提取临时任务ID
        temp_task_id = None
        for msg in conversation:
            if msg["role"] == "system" and msg["content"].startswith("temp_task_id:"):
                temp_task_id = msg["content"].split(":")[1]
                break
        
        product_description = extract_product_description(conversation)
        email = request.form.get('email', '')
        
        # 验证邮箱格式
        if not email or '@' not in email:
            return render_template('step2.html', error="请提供有效的电子邮箱地址", amount=0)
        
        # 检查是否是VIP用户
        is_vip, vip_info = is_vip_user(email)
        
        # 获取分析参数
        num_personas = int(request.form.get('num_personas', 10))
        num_simulations = int(request.form.get('num_simulations', 2))
        
        if is_vip:
            # VIP用户特殊处理
            if num_personas > vip_info['max_personas']:
                num_personas = vip_info['max_personas']
            if num_simulations > vip_info['max_simulations']:
                num_simulations = vip_info['max_simulations']
            amount = 0
        else:
            # 非VIP用户的限制
            if num_personas > 40:
                num_personas = 40
            if num_simulations > 2:
                num_simulations = 2
            
            # 快速尝鲜版特殊处理
            if num_personas == 2:
                num_simulations = 2
                amount = 0
            else:
                # 计算费用
                total_people = num_personas * num_simulations
                invite_code = request.form.get('valid_invite_code', '')
                
                if invite_code and verify_and_use_invite_code(invite_code)[0]:
                    num_personas = 10
                    num_simulations = 2
                    amount = 0
                    increment_invite_code_usage(invite_code)
                else:
                    amount = min(40, max(5, total_people // 2))
        
        # 创建新的任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        tasks[task_id] = {
            'id': task_id,
            'email': email,
            'product_description': product_description,
            'num_personas': num_personas,
            'num_simulations': num_simulations,
            'status': 'pending',
            'amount': amount,
            'is_vip': is_vip,
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'progress': {'percentage': 0}
        }
        save_tasks(tasks=tasks, tasks_file=TASKS_FILE)
        
        # 如果是付费任务且不是VIP用户，发送通知邮件并显示付款页面
        if amount > 0 and not is_vip:
            send_payment_notification(task_id, amount, email)
            tasks[task_id]['status'] = 'pending_payment'
            save_tasks(tasks=tasks, tasks_file=TASKS_FILE)
            qr_code_path = f"static/payment_codes/{amount}元.jpg"
            return render_template('step2.html', 
                                task_id=task_id, 
                                email=email, 
                                product_description=product_description,
                                num_personas=num_personas,
                                num_simulations=num_simulations,
                                amount=amount,
                                qr_code_path=qr_code_path,
                                task=tasks[task_id])
        
        # VIP用户或免费任务直接启动
        thread = threading.Thread(
            target=run_analysis_task, 
            args=(task_id, product_description, num_personas, num_simulations,
                  tasks, task_stop_flags,
                  TASKS_FILE, MODEL_POOL, app)
        )
        thread.daemon = True
        thread.start()
        
        return render_template('step2.html', 
                            task_id=task_id, 
                            email=email, 
                            product_description=product_description,
                            num_personas=num_personas,
                            num_simulations=num_simulations,
                            amount=0,
                            task=tasks[task_id])
    
    return redirect(url_for('step1'))

@app.route('/api/task/<task_id>/start', methods=['POST'])
def start_task_api(task_id):
    # 添加一个简单的密码保护
    key = request.args.get('key')
    if key != ADMIN_PASSWORD:
        return jsonify({'error': '未授权访问'}), 403
        
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 只有等待付款的任务可以启动
    if task['status'] != 'pending_payment':
        return jsonify({'error': '只能启动等待付款的任务'}), 400
    
    # 更新任务状态
    task['status'] = 'pending'
    save_tasks(tasks=tasks, tasks_file=TASKS_FILE)
    
    # 启动任务
    thread = threading.Thread(
        target=run_analysis_task, 
        args=(task_id, task['product_description'], 
              task['num_personas'], task['num_simulations'],
              tasks, task_stop_flags,
              TASKS_FILE, MODEL_POOL, app)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': '任务已启动'})

# 获取任务状态API
@app.route('/api/task/<task_id>/status')
def task_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    # 计算预计完成时间
    estimated_time = None
    if task['status'] in ['generating_personas', 'simulating_reactions'] and 'start_time' in task:
        elapsed = time.time() - task['start_time']
        progress = task.get('progress', {}).get('percentage', 0)
        
        # Only calculate remaining time when progress is meaningful (> 5%)
        if progress > 5:
            estimated_total_seconds = (elapsed / progress) * 100
            remaining_seconds = estimated_total_seconds - elapsed
            
            # Handle edge cases: if remaining time is negative or very small, show "即将完成"
            if remaining_seconds <= 5:
                estimated_time = "即将完成"
            else:
                # 将剩余时间转换为更友好的格式（分钟和秒）
                minutes, seconds = divmod(int(remaining_seconds), 60)
                if minutes > 60:
                    hours, minutes = divmod(minutes, 60)
                    estimated_time = f"{hours}小时{minutes}分钟"
                elif minutes > 0:
                    estimated_time = f"{minutes}分钟{seconds}秒"
                else:
                    estimated_time = f"{seconds}秒"
        elif progress > 0:
            # Progress is between 0-5%, show "计算中..."
            estimated_time = "计算中..."
    
    return jsonify({
        'id': task_id,
        'status': task['status'],
        'progress': task.get('progress', {'percentage': 0}),
        'estimated_completion_time': estimated_time,
        'stats': task.get('stats', {}),
        'error': task.get('error'),
        'report_url': url_for('public_report_download', task_id=task_id) if task.get('status') == 'completed' and task.get('files', {}).get('report') else None
    })

# Inline: 在step1直接创建并启动分析任务（免邮箱免支付）
@app.route('/api/inline_task', methods=['POST'])
def inline_task():
    try:
        conversation = json.loads(request.form['conversation'])
    except Exception:
        return jsonify({'error': 'invalid conversation'}), 400

    num_personas = int(request.form.get('num_personas', 2))
    num_simulations = int(request.form.get('num_simulations', 2))

    product_description = extract_product_description(conversation)
    if not product_description:
        return jsonify({'error': 'missing product description'}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'id': task_id,
        'email': 'inline@local',
        'product_description': product_description,
        'num_personas': num_personas,
        'num_simulations': num_simulations,
        'status': 'pending',
        'amount': 0,
        'is_vip': True,
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'progress': {'percentage': 0}
    }
    save_tasks(tasks=tasks, tasks_file=TASKS_FILE)

    thread = threading.Thread(
        target=run_analysis_task,
        args=(task_id, product_description, num_personas, num_simulations,
              tasks, task_stop_flags,
              TASKS_FILE, MODEL_POOL, app)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})


@app.route('/api/token_estimate', methods=['POST'])
def token_estimate():
    conversation_json = request.form.get('conversation', '[]')
    try:
        conversation = json.loads(conversation_json)
    except Exception:
        conversation = []

    num_personas = int(request.form.get('num_personas', 2) or 2)
    num_simulations = int(request.form.get('num_simulations', 2) or 2)
    product_description = extract_product_description(conversation) or ""

    estimator_system_prompt = (
        "你是Token估算器，阅读提供的系统提示、任务步骤和上下文，估计完成任务至少需要的输出token数量。"
        "只返回JSON: {\"token_estimate\": <整数>, \"reason\": \"简要说明\"}，不要使用代码块或额外解释。"
        "如果不确定，请倾向给出略大的估计。"
    )

    task_context = f"""
[产品描述]
{product_description if product_description else "未提供"}

[对话上下文]
{json.dumps(conversation, ensure_ascii=False)}

[任务参数]
- 用户画像数量: {num_personas}
- 每个画像模拟次数: {num_simulations}

[系统提示词]
persona_system_prompt:
{persona_system_prompt}

persona_reviewer_system_prompt:
{persona_reviewer_system_prompt}

simulation_system_prompt:
{simulation_system_prompt}

inquiry_system_prompt:
{inquiry_system_prompt}

refined_system_prompt:
{refined_system_prompt}

ad_generation_system_prompt:
{ad_generation_system_prompt}

ad_reviewer_system_prompt:
{ad_reviewer_system_prompt}

product_optimization_system_prompt:
{product_optimization_system_prompt}
""".strip()

    messages = [
        {"role": "system", "content": estimator_system_prompt},
        {"role": "user", "content": task_context}
    ]

    def generate():
        buffer = ""
        estimate_sent = False
        try:
            for chunk in call_ai_api_stream(messages, temp=0.2, model_pool=MODEL_POOL):
                if not chunk.startswith("data:"):
                    continue
                data_str = chunk[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                except Exception:
                    continue

                content = data.get('content', '')
                if not content:
                    continue

                if estimate_sent:
                    continue

                buffer += content
                match = re.search(r'"token_estimate"\s*:\s*(\d+)', buffer)
                if not match:
                    match = re.search(r'(\d{2,})', buffer)

                if match:
                    estimate_val = int(match.group(1))
                    if estimate_val > 0:
                        yield f"data: {json.dumps({'estimate': estimate_val}, ensure_ascii=False)}\n\n"
                        estimate_sent = True
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        if not estimate_sent:
            yield f"data: {json.dumps({'error': '未能解析token估计'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@app.route('/api/task/<task_id>/report')
def public_report_download(task_id):
    if task_id not in tasks:
        return '任务不存在', 404
    task = tasks[task_id]
    if task.get('status') != 'completed' or 'files' not in task or not task['files'].get('report'):
        return '文件未就绪', 404
    return send_file(task['files']['report'], as_attachment=True)

# 后台任务管理页面
@app.route('/admin/tasks')
def admin_tasks():
    # 添加一个简单的密码保护
    if request.args.get('key') != ADMIN_PASSWORD:
        return "Unauthorized", 401
    
    return render_template('admin_tasks.html', tasks=tasks)

# 下载任务文件
@app.route('/admin/tasks/<task_id>/download/<file_type>')
def download_task_file(task_id, file_type):
    # 添加一个简单的密码保护
    key = request.args.get('key')
    if key != ADMIN_PASSWORD:
        return '未授权访问', 403
        
    if task_id not in tasks:
        return '任务不存在', 404
        
    task = tasks[task_id]
    if task['status'] != 'completed' or 'files' not in task:
        return '文件未就绪', 404
        
    file_map = {
        'personas': task['files'].get('personas'),
        'simulations': task['files'].get('simulations'),
        'report': task['files'].get('report')
    }
    
    if file_type not in file_map or not file_map[file_type]:
        return '文件不存在', 404
        
    return send_file(file_map[file_type], as_attachment=True)

def is_task_expired(task):
    """检查任务是否过期（等待付款超过24小时）"""
    if task['status'] != 'pending_payment':
        return False
    
    try:
        # 将字符串时间转换为datetime对象
        created_time = datetime.strptime(task['created_at'], "%Y-%m-%d %H:%M:%S")
        # 检查是否超过24小时
        return datetime.now() - created_time > timedelta(hours=24)
    except Exception as e:
        print(f"检查任务过期时出错: {str(e)}")
        return False

def cleanup_expired_tasks():
    """清理过期的任务"""
    while True:
        try:
            # 找出所有过期的任务
            expired_tasks = []
            for task_id, task in tasks.items():
                if is_task_expired(task):
                    expired_tasks.append(task_id)
            
            # 删除过期任务
            for task_id in expired_tasks:
                print(f"删除过期任务: {task_id}")
                # 删除相关文件
                try:
                    conversation_file = os.path.join(CONVERSATIONS_FOLDER, f"{task_id}_conversation.json")
                    if os.path.exists(conversation_file):
                        os.remove(conversation_file)
                except Exception as e:
                    print(f"删除任务文件时出错: {str(e)}")
                
                # 从tasks字典中删除
                tasks.pop(task_id, None)
            
            # 如果有任务被删除，保存更新后的tasks
            if expired_tasks:
                save_tasks(tasks=tasks, tasks_file=TASKS_FILE)
                print(f"已清理 {len(expired_tasks)} 个过期任务")
            
            # 每小时检查一次
            time.sleep(3600)
        except Exception as e:
            print(f"清理过期任务时出错: {str(e)}")
            # 发生错误时等待较短时间后重试
            time.sleep(300)

@app.route('/api/verify_invite_code/<code>')
def verify_invite_code(code):
    valid, message = verify_and_use_invite_code(code)
    return jsonify({
        'valid': valid,
        'message': message
    })

# 添加安全头部
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# 错误处理
@app.errorhandler(400)
def bad_request_error(error):
    if request.headers.get('Accept', '').find('html') != -1:
        return render_template('error.html', error_code=400, error_message="请求格式错误"), 400
    return jsonify({"error": "Bad Request"}), 400

@app.errorhandler(404)
def not_found_error(error):
    if request.headers.get('Accept', '').find('html') != -1:
        return render_template('error.html', error_code=404, error_message="页面未找到"), 404
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(500)
def internal_error(error):
    if request.headers.get('Accept', '').find('html') != -1:
        return render_template('error.html', error_code=500, error_message="服务器内部错误"), 500
    return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/check_vip/<email>')
def check_vip(email):
    """检查用户VIP状态的API"""
    is_vip, vip_info = is_vip_user(email)
    if is_vip:
        return jsonify({
            'is_vip': True,
            'end_date': vip_info['end_date'],
            'max_personas': vip_info['max_personas'],
            'max_simulations': vip_info['max_simulations']
        })
    return jsonify({'is_vip': False})

@app.route('/api/active_models')
def get_active_models():
    """获取所有active状态的模型列表"""
    active_models = []

    for model_name, model_data in MODEL_POOL.items():
        # 检查是否有active的API key
        active_keys = model_data.get('active_keys', [])
        if active_keys:  # 只要有active的key就显示
            # 获取模型配置
            config = model_data.get('config', {})

            # 简化模型名称用于显示
            display_name = model_name.split('/')[-1]
            if 'DeepSeek-V3' in model_name:
                display_name = 'DeepSeek V3'
                description = '高性能推理模型，适合复杂分析'
            elif 'DeepSeek-R1' in model_name:
                display_name = 'DeepSeek R1'
                description = '强化学习模型，逻辑推理能力强'
            elif 'deepseek-chat' in model_name:
                display_name = 'DeepSeek Chat'
                description = '多轮对话模型，交互体验好'
            elif 'deepseek-reasoner' in model_name:
                display_name = 'DeepSeek Reasoner'
                description = '推理专用模型，适合深度思考'
            elif 'kimi-k2-turbo' in model_name.lower():
                display_name = 'Kimi K2 Turbo'
                description = '长文本处理能力强，响应快速'
            else:
                display_name = model_name.split('/')[-1]
                description = '通用AI模型'

            active_models.append({
                'value': model_name,
                'name': display_name,
                'description': description,
                'max_tokens': config.get('max_tokens', 4096),
                'temperature_default': config.get('temperature_default', 0.7)
            })

    return jsonify({'models': active_models})

# TODO：还不太清楚这个具体如何使用
# @app.route('/api/models')
# def list_models():
#     """列出所有可用的模型"""
#     # 添加一个简单的密码保护
#     key = request.args.get('key')
#     if key != 'admin123':
#         return jsonify({'error': '未授权访问'}), 403
    
#     models_info = {}
#     for model_name, model_data in MODEL_POOL.items():
#         # 移除敏感信息
#         model_config = model_data.get('config', {})
#         active_keys = model_data.get('active_keys', [])
        
#         # 安全处理API密钥信息
#         safe_keys = []
#         for key_config in active_keys:
#             # 部分隐藏API密钥
#             api_key = key_config.get('api_key', '')
#             masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '********'
            
#             # 移除敏感的Authorization头
#             safe_headers = {}
#             if 'headers' in key_config:
#                 safe_headers = {k: v for k, v in key_config['headers'].items() if k.lower() != 'authorization'}
#                 if 'authorization' in key_config['headers']:
#                     auth_header = key_config['headers']['authorization']
#                     if auth_header.lower().startswith('bearer '):
#                         masked_token = auth_header[:7] + masked_key
#                         safe_headers['authorization'] = masked_token
            
#             safe_keys.append({
#                 'api_url': key_config.get('api_url', ''),
#                 'api_key': masked_key,
#                 'headers': safe_headers,
#                 'weight': key_config.get('weight', 1),
#                 'rate_limit': key_config.get('rate_limit', 60),
#                 'status': key_config.get('status', 'active')
#             })
        
#         models_info[model_name] = {
#             'model_name': model_config.get('model_name', model_name.split('/')[-1]),
#             'max_tokens': model_config.get('max_tokens', 4096),
#             'temperature_default': model_config.get('temperature_default', 0.7),
#             'api_keys_count': len(active_keys),
#             'api_keys': safe_keys
#         }
    
#     return jsonify({
#         'models_count': len(MODEL_POOL),
#         'models': models_info
#     })

# @app.route('/api/models/status')
# def models_status():
#     """获取模型API密钥的使用状态"""
#     # 添加一个简单的密码保护
#     key = request.args.get('key')
#     if key != 'admin123':
#         return jsonify({'error': '未授权访问'}), 403
    
#     # 导入模型使用计数器
#     from models import api_call_counter, last_api_call_time
    
#     status_info = {}
#     for key_id, count in api_call_counter.items():
#         # 解析密钥ID格式: model_name:api_key
#         parts = key_id.split(':')
#         if len(parts) >= 2:
#             model_name = parts[0]
#             api_key = ':'.join(parts[1:])  # 处理api_key可能包含冒号的情况
            
#             # 隐藏部分API密钥
#             masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '********'
            
#             # 计算上次使用的时间
#             last_used = last_api_call_time.get(key_id, 0)
#             last_used_str = "从未使用"
#             if last_used > 0:
#                 import datetime
#                 last_used_str = datetime.datetime.fromtimestamp(last_used).strftime('%Y-%m-%d %H:%M:%S')
            
#             if model_name not in status_info:
#                 status_info[model_name] = []
            
#             status_info[model_name].append({
#                 'api_key': masked_key,
#                 'call_count': count,
#                 'last_used': last_used_str
#             })
    
#     return jsonify({
#         'status': status_info
#     })

if __name__ == '__main__':
    # 启动清理过期任务的后台线程
    cleanup_thread = threading.Thread(target=cleanup_expired_tasks)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    app.run(host='0.0.0.0', port=5001, debug=False) 