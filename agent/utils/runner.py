from .report_generate import generate_report
from .tasks import update_task_status
from .persona_generate import generate_user_personas
from .simulatiton_generate import simulate_user_reactions
from .email import send_report_email
import time
import os
import json

from .web_search_pipeline import (
    build_web_context_block,
    decide_web_search_queries,
    pick_large_model_name,
    run_web_search_session,
    summarize_web_docs_with_llm,
)

def run_analysis_task(task_id, product_description,
                       num_personas, num_simulations,
                       tasks, task_stop_flags,
                       TASKS_FILE, MODEL_POOL, app):
    """运行分析任务"""
    try:
        # 初始化中止标志
        task_stop_flags[task_id] = False
        
        # 快速尝鲜版特殊处理：强制设置为2次模拟
        if num_personas == 2:
            num_simulations = 2
        else:
            # 非极速尝鲜版才应用常规限制
            num_personas = min(40, num_personas)
            num_simulations = min(2, num_simulations)
        
        # 估算token（粗略：画像*模拟*800）
        total_tokens = max(800, num_personas * num_simulations * 800)

        # 更新任务状态
        update_task_status(task_id, status='running', tasks=tasks, tasks_file=TASKS_FILE)
        tasks[task_id]['start_time'] = time.time()
        tasks[task_id]['progress'] = {
            'current_step': 'pending',
            'completed': 0,
            'total': 100,
            'percentage': 0,
            'used_tokens': 0,
            'total_tokens': total_tokens
        }
        
        # 检查是否被中止
        if task_stop_flags.get(task_id):
            raise Exception("任务已被中止")
        
        # 1. 生成用户画像
        personas = generate_user_personas(task_id, product_description, num_personas, 
                                          tasks=tasks, tasks_file=TASKS_FILE, 
                                          model_pool=MODEL_POOL, app=app)
        
        # 检查是否被中止
        if task_stop_flags.get(task_id):
            raise Exception("任务已被中止")
        
        # 2. 模拟用户反应
        tasks[task_id]['status'] = 'simulating_reactions'
        all_simulation_results = []

        # (Optional) Web search context for the simulation phase (task-level).
        web_session = None
        web_context = ""
        try:
            web_intent = (
                "We are about to run user-reaction simulations for the following product.\n"
                "If useful, propose web-search queries to understand relevant market context, common alternatives, pricing, and constraints.\n\n"
                f"Product:\n{product_description}"
            )
            should_search, queries, _ = decide_web_search_queries(
                user_intent=web_intent, model_pool=MODEL_POOL, model_name=pick_large_model_name(MODEL_POOL)
            )
            if should_search:
                web_session = run_web_search_session(queries)
                web_context = build_web_context_block(web_session)
        except Exception as e:
            print(f"Web search (simulation phase) skipped due to error: {e}")
        
        for i, persona in enumerate(personas):
            # 检查是否被中止
            if task_stop_flags.get(task_id):
                raise Exception("任务已被中止")
            
            # 更新进度
            pct = round(((i + 1) / len(personas)) * 90, 1)
            used_tokens = int(total_tokens * pct / 100)
            tasks[task_id]['progress'] = {
                'current_step': 'simulations',
                'completed': i + 1,
                'total': len(personas),
                'percentage': pct,
                'used_tokens': used_tokens,
                'total_tokens': total_tokens
            }
            
            simulation_results = simulate_user_reactions(task_id, product_description, persona,
                                                         num_simulations, model_pool=MODEL_POOL,
                                                         web_context=web_context)
            all_simulation_results.extend(simulation_results)
        
        # 更新进度到95%，表示开始生成报告
        tasks[task_id]['progress'] = {
            'current_step': 'generating_report',
            'completed': 95,
            'total': 100,
            'percentage': 95,
            'used_tokens': int(total_tokens * 0.95),
            'total_tokens': total_tokens
        }
        
        # 保存模拟结果
        personas_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_personas.json")
        simulations_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_simulations.json")
        report_file = os.path.join(app.config['REPORTS_FOLDER'], f"{task_id}_report.html")
        
        # 保存模拟结果
        with open(simulations_file, 'w', encoding='utf-8') as f:
            json.dump(all_simulation_results, f, ensure_ascii=False, indent=2)
        
        # 3. 生成统计
        stats = {}
        if all_simulation_results:
            # 基础统计
            total_simulations = len(all_simulation_results)
            
            # 意愿指标统计
            would_try_count = sum(1 for sim in all_simulation_results if sim.get('would_try') == True)
            would_buy_count = sum(1 for sim in all_simulation_results if sim.get('would_buy') == True)
            must_have_count = sum(1 for sim in all_simulation_results if sim.get('is_must_have') == True)
            would_recommend_count = sum(1 for sim in all_simulation_results if sim.get('would_recommend') == True)
            
            would_try_percentage = (would_try_count / total_simulations) * 100
            would_buy_percentage = (would_buy_count / total_simulations) * 100
            must_have_percentage = (must_have_count / total_simulations) * 100
            would_recommend_percentage = (would_recommend_count / total_simulations) * 100
            
            # 依赖程度统计
            dependency_counts = {"痛苦": 0, "可以接受": 0, "无所谓": 0}
            for sim in all_simulation_results:
                dep = sim.get('dependency_level')
                if dep in dependency_counts:
                    dependency_counts[dep] += 1
            
            dependency_percentages = {key: (value / total_simulations * 100) 
                                   for key, value in dependency_counts.items()}
            
            # 用户类型统计
            user_type_counts = {}
            for sim in all_simulation_results:
                user_type = sim.get('user_type', '未知')
                user_type_counts[user_type] = user_type_counts.get(user_type, 0) + 1
            
            user_type_percentages = {key: (value / total_simulations * 100) 
                                   for key, value in user_type_counts.items()}
            
            # 使用频率统计
            usage_frequency_counts = {}
            for sim in all_simulation_results:
                freq = sim.get('usage_frequency', '未知')
                usage_frequency_counts[freq] = usage_frequency_counts.get(freq, 0) + 1
            
            usage_frequency_percentages = {key: (value / total_simulations * 100) 
                                        for key, value in usage_frequency_counts.items()}
            
            # 地域分布统计
            location_counts = {}
            for sim in all_simulation_results:
                location = sim.get('location', '未知')
                location_counts[location] = location_counts.get(location, 0) + 1
            
            location_percentages = {key: (value / total_simulations * 100) 
                                 for key, value in location_counts.items()}
            
            # 采用障碍统计（提取出现频率最高的几个关键词）
            barrier_keywords = {}
            for sim in all_simulation_results:
                barrier = sim.get('barrier_to_adoption', '')
                if barrier and barrier != "未提供" and barrier != "模拟出错":
                    # 简单分词
                    keywords = [k.strip() for k in barrier.replace('，', ',').split(',')]
                    for k in keywords:
                        if k and len(k) > 1:
                            barrier_keywords[k] = barrier_keywords.get(k, 0) + 1
            
            # 找出出现频率最高的5个障碍
            top_barriers = sorted(barrier_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
            
            stats = {
                'would_try_percentage': round(would_try_percentage, 1),
                'would_buy_percentage': round(would_buy_percentage, 1),
                'must_have_percentage': round(must_have_percentage, 1),
                'would_recommend_percentage': round(would_recommend_percentage, 1),
                'dependency_percentages': {k: round(v, 1) for k, v in dependency_percentages.items()},
                'user_type_percentages': {k: round(v, 1) for k, v in user_type_percentages.items()},
                'usage_frequency_percentages': {k: round(v, 1) for k, v in usage_frequency_percentages.items()},
                'location_percentages': {k: round(v, 1) for k, v in location_percentages.items()},
                'top_barriers': dict(top_barriers),
                'total_personas': len(personas),
                'total_simulations': total_simulations
            }
        
        # 更新进度到97%，准备生成报告
        tasks[task_id]['progress'] = {
            'current_step': 'generating_report',
            'completed': 97,
            'total': 100,
            'percentage': 97,
            'used_tokens': int(total_tokens * 0.97),
            'total_tokens': total_tokens
        }
        
        # Build a single LLM summary for all web-search documents used in simulation phase (if any).
        web_summary = ""
        web_references_md = ""
        if web_session and web_session.all_docs():
            try:
                web_summary = summarize_web_docs_with_llm(
                    web_session, model_pool=MODEL_POOL, model_name=pick_large_model_name(MODEL_POOL)
                )
                # 对于报告，只包含 References (summarized)，不包含per-query summaries
                web_references_md = web_session.references_markdown(include_per_query_summaries=False)
                tasks[task_id]["web_search"] = {
                    "queries": [r.query for r in web_session.runs],
                    "summary": web_summary,
                    "references_markdown": web_references_md,
                }
            except Exception as e:
                print(f"Web search summary generation failed: {e}")

        # 生成报告
        report_path = generate_report(
            personas_file,
            simulations_file,
            report_file,
            product_description,
            web_search_summary=web_summary,
            web_search_references_markdown=web_references_md,
        )
        
        # 更新进度到99%，准备发送邮件
        tasks[task_id]['progress'] = {
            'current_step': 'sending_email',
            'completed': 99,
            'total': 100,
            'percentage': 99
        }
        
        if report_path:
            # 更新任务状态和文件列表
            tasks[task_id].update({
                'status': 'completed',
                'end_time': time.time(),
                'stats': stats,
                'files': {
                    'personas': personas_file,
                    'simulations': simulations_file,
                    'report': report_file
                }
            })
            
            # 发送报告到用户邮箱（inline免发送）
            email = tasks[task_id].get('email')
            if email and email != 'inline@local':
                email_sent = send_report_email(email, task_id, report_file)
                if not email_sent:
                    print(f"邮件发送失败: {task_id}")
            
            # 最终更新进度到100%
            update_task_status(task_id, status='completed', progress={
                'current_step': 'completed',
                'completed': 100,
                'total': 100,
                'percentage': 100,
                'used_tokens': total_tokens,
                'total_tokens': total_tokens
            }, tasks=tasks, tasks_file=TASKS_FILE)
        else:
            raise Exception("报告生成失败")
        
        return True
    except Exception as e:
        update_task_status(task_id, status='failed', tasks=tasks, tasks_file=TASKS_FILE)
        tasks[task_id]['error'] = str(e)
        print(f"任务 {task_id} 失败: {str(e)}")
        return False
