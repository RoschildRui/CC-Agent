import json
import pandas as pd
from datetime import datetime
import os
import sys
from collections import defaultdict

def generate_report(
    personas_file,
    simulations_file,
    output_file=None,
    product_description=None,
    web_search_summary: str = "",
    web_search_references_markdown: str = "",
):
    """
    从personas和simulations JSON文件生成HTML报告，使用前端Chart.js绘制图表
    
    参数:
    personas_file: personas JSON文件路径
    simulations_file: simulations JSON文件路径
    output_file: 输出HTML文件路径，如果为None则自动生成
    product_description: 产品描述文本
    """
    # 读取数据
    try:
        with open(personas_file, 'r', encoding='utf-8') as f:
            personas = json.load(f)
    except Exception as e:
        print(f"读取personas文件时出错: {e}")
        return
        
    try:
        with open(simulations_file, 'r', encoding='utf-8') as f:
            simulations = json.load(f)
    except Exception as e:
        print(f"读取simulations文件时出错: {e}")
        return
    
    # 如果未指定输出文件，则从输入文件名生成
    if output_file is None:
        base_name = os.path.basename(personas_file).split('.')[0]
        output_file = f"{base_name}_report.html"
    
    # 标准字段列表
    standard_fields = [
        'initial_impression',
        'perceived_needs',
        'would_try',
        'would_buy',
        'is_must_have',
        'would_recommend',
        'dependency_level',
        'alternatives',
        'barrier_to_adoption',
        'feedback',
        'suggested_improvements',
        'user_type',
        'usage_frequency',
        'simulation_id',
        'persona_id',
        'simulated_at',
        'ad_copy',  # 新增广告文案字段
        'optimized_product'  # 新增优化产品描述字段
    ]
    
    # 清理模拟结果，只保留标准字段，并确保新字段的格式正确
    cleaned_simulations = []
    for sim in simulations:
        cleaned_sim = {field: sim.get(field, '') for field in standard_fields}
        
        # 处理广告文案字段
        if 'ad_copy' in sim:
            ad_copy = sim['ad_copy']
            if isinstance(ad_copy, dict):
                cleaned_sim['ad_copy'] = ad_copy
            else:
                cleaned_sim['ad_copy'] = {
                    'ad_headline': '未生成',
                    'ad_body': '未生成',
                    'key_pain_points': [],
                    'target_emotions': []
                }
        else:
            cleaned_sim['ad_copy'] = {
                'ad_headline': '未生成',
                'ad_body': '未生成',
                'key_pain_points': [],
                'target_emotions': []
            }
            
        # 处理优化产品描述字段
        if 'optimized_product' in sim:
            opt_product = sim['optimized_product']
            if isinstance(opt_product, dict):
                cleaned_sim['optimized_product'] = opt_product
            else:
                cleaned_sim['optimized_product'] = {
                    'optimized_description': '未生成',
                    'key_improvements': [],
                    'expected_benefits': [],
                    'implementation_priority': '中'
                }
        else:
            cleaned_sim['optimized_product'] = {
                'optimized_description': '未生成',
                'key_improvements': [],
                'expected_benefits': [],
                'implementation_priority': '中'
            }
            
        cleaned_simulations.append(cleaned_sim)
    
    # 创建DataFrame
    personas_df = pd.DataFrame(personas)
    simulations_df = pd.DataFrame(cleaned_simulations)
    
    # 给personas添加排序值
    user_type_order = {
        '核心用户': 1,
        '潜在用户': 2,
        '边缘用户': 3,
        '非目标用户': 4
    }
    
    frequency_order = {
        '每天多次': 1,
        '每天一次': 2,
        '每周几次': 3,
        '每月几次': 4,
        '很少使用': 5
    }
    
    # 对personas数据添加排序字段
    for persona in personas:
        user_type = persona.get('user_type', '')
        usage_frequency = persona.get('usage_frequency', '')
        
        # 设置排序值（默认为最低优先级）
        persona['user_type_order'] = user_type_order.get(user_type, 999)
        persona['frequency_order'] = frequency_order.get(usage_frequency, 999)
    
    # 先按用户类型排序，再按使用频率排序
    personas.sort(key=lambda x: (x.get('user_type_order', 999), x.get('frequency_order', 999)))
    
    # 数据统计
    total_users = len(simulations_df)
    
    # 用户类型统计
    user_types = {}
    if 'user_type' in simulations_df.columns:
        user_types = simulations_df['user_type'].fillna('未知').value_counts().to_dict()
    
    # 刚需比例计算
    must_have_percentage = 0
    if 'is_must_have' in simulations_df.columns and not simulations_df['is_must_have'].empty:
        must_have_percentage = (simulations_df['is_must_have'].fillna(False).astype(bool).sum() / total_users) * 100
    
    # 推荐意愿比例计算
    would_recommend_percentage = 0
    if 'would_recommend' in simulations_df.columns and not simulations_df['would_recommend'].empty:
        would_recommend_percentage = (simulations_df['would_recommend'].fillna(False).astype(bool).sum() / total_users) * 100
    
    # 依赖水平统计
    dependency_data = {}
    if 'dependency_level' in simulations_df.columns and not simulations_df['dependency_level'].empty:
        dependency_counts = simulations_df['dependency_level'].fillna('无所谓').value_counts()
        dependency_percentages = (dependency_counts / dependency_counts.sum() * 100).round(1)
        dependency_data = {
            'labels': dependency_percentages.index.tolist(),
            'data': dependency_percentages.values.tolist()
        }
    
    # 使用频率统计
    frequency_data = {}
    if 'usage_frequency' in simulations_df.columns and not simulations_df['usage_frequency'].empty:
        frequency_counts = simulations_df['usage_frequency'].fillna('未知').value_counts()
        frequency_percentages = (frequency_counts / frequency_counts.sum() * 100).round(1)
        frequency_data = {
            'labels': frequency_percentages.index.tolist(),
            'data': frequency_percentages.values.tolist()
        }
    
    # 地域分布统计
    location_data = {}
    if 'location' in simulations_df.columns and not simulations_df['location'].empty:
        location_counts = simulations_df['location'].fillna('未知').value_counts()
        location_percentages = (location_counts / location_counts.sum() * 100).round(1)
        location_data = {
            'labels': location_percentages.index.tolist(),
            'data': location_percentages.values.tolist()
        }
    
    # 用户类型数据准备
    user_type_data = {
        'labels': list(user_types.keys()),
        'data': list(user_types.values())
    }
    
    # 为Chart.js准备颜色
    user_type_colors = [
        'rgba(54, 162, 235, 0.7)',   # 蓝色
        'rgba(255, 159, 64, 0.7)',   # 橙色
        'rgba(75, 192, 192, 0.7)',   # 绿色
        'rgba(255, 99, 132, 0.7)'    # 红色
    ]
    
    dependency_colors = [
        'rgba(54, 162, 235, 0.7)',   # 蓝色
        'rgba(255, 159, 64, 0.7)',   # 橙色
        'rgba(255, 99, 132, 0.7)',   # 红色
        'rgba(75, 192, 192, 0.7)'    # 绿色
    ]
    
    location_colors = [
        'rgba(54, 162, 235, 0.7)',   # 蓝色
        'rgba(255, 159, 64, 0.7)',   # 橙色
        'rgba(75, 192, 192, 0.7)',   # 绿色
        'rgba(255, 99, 132, 0.7)',   # 红色
        'rgba(153, 102, 255, 0.7)',  # 紫色
        'rgba(255, 206, 86, 0.7)',   # 黄色
        'rgba(231, 233, 237, 0.7)',  # 灰色
    ]
    
    # 开始生成HTML报告
    # Web Search section commented out - references will be shown at the end of the report
    web_section_html = ""
    # if (web_search_summary or "").strip() or (web_search_references_markdown or "").strip():
    #     # Keep it simple: plain pre-wrap text to avoid layout issues.
    #     web_text = ""
    #     if (web_search_summary or "").strip():
    #         web_text += "Web search synthesis:\\n" + web_search_summary.strip() + "\\n\\n"
    #     if (web_search_references_markdown or "").strip():
    #         web_text += "References:\\n" + web_search_references_markdown.strip()
    #
    #     web_section_html = f"""
    #     <div class="section" style="background-color: #f5f7ff; border-left: 4px solid #6c63ff;">
    #         <h2 style="color: #3f3d56;">Web Search (Simulation Phase)</h2>
    #         <pre style="white-space: pre-wrap; word-break: break-word; margin: 0; font-size: 14px; line-height: 1.6;">{web_text}</pre>
    #     </div>
    #     """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>用户研究报告</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Chart.js with fixed version -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
        <style>
            body {{
                font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .header {{
                text-align: center;
                padding: 20px 0;
                margin-bottom: 30px;
                border-bottom: 1px solid #ddd;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0;
                color: #2c3e50;
                font-size: 28px;
            }}
            .date {{
                color: #7f8c8d;
                font-style: italic;
                font-size: 16px;
            }}
            .section {{
                margin: 30px 0;
                padding: 20px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #2980b9;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 10px;
                font-size: 24px;
            }}
            .section h3 {{
                color: #3498db;
                font-size: 20px;
            }}
            .stats-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-around;
                margin: 20px 0;
            }}
            .stat-box {{
                background-color: #ecf0f1;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
                text-align: center;
                flex: 1 1 200px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .stat-box h3 {{
                margin: 0;
                font-size: 16px;
                color: #7f8c8d;
            }}
            .stat-box p {{
                margin: 10px 0 0;
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .chart-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-around;
                margin: 20px 0;
            }}
            .chart {{
                flex: 1 1 350px;
                margin: 15px;
                text-align: center;
                background-color: #fff;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                height: 350px;
            }}
            .chart h3 {{
                margin-top: 0;
                font-size: 18px;
                color: #2980b9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 16px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .persona-card {{
                margin: 30px 0;
                padding: 20px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .persona-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #ecf0f1;
            }}
            .persona-title {{
                flex: 1;
            }}
            .persona-title h3 {{
                margin: 0;
                color: #2980b9;
                font-size: 20px;
            }}
            .persona-meta {{
                display: flex;
                gap: 15px;
            }}
            .persona-tag {{
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            .tag-core {{
                background-color: #e74c3c;
                color: white;
            }}
            .tag-potential {{
                background-color: #f39c12;
                color: white;
            }}
            .tag-marginal {{
                background-color: #3498db;
                color: white;
            }}
            .tag-non-target {{
                background-color: #95a5a6;
                color: white;
            }}
            .tag-frequency {{
                background-color: #1abc9c;
                color: white;
            }}
            .tag-location {{
                background-color: #9b59b6;
                color: white;
            }}
            .persona-description {{
                margin-bottom: 20px;
                line-height: 1.7;
                font-size: 16px;
            }}
            .needs-list, .scenarios-list {{
                padding-left: 20px;
                font-size: 16px;
            }}
            .needs-list li, .scenarios-list li {{
                margin-bottom: 8px;
            }}
            .simulation-card {{
                margin: 15px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #3498db;
                font-size: 16px;
            }}
            .simulation-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }}
            .simulation-title {{
                font-weight: bold;
                color: #2c3e50;
                font-size: 16px;
            }}
            .simulation-meta {{
                color: #7f8c8d;
                font-size: 14px;
            }}
            .simulation-content {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}
            .simulation-item {{
                margin-bottom: 10px;
            }}
            .simulation-item-title {{
                font-weight: bold;
                margin-bottom: 5px;
                color: #34495e;
                font-size: 16px;
            }}
            .simulation-feedback, .simulation-improvements {{
                grid-column: 1 / -1;
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-top: 10px;
            }}
            .tag-bool-true {{
                color: #27ae60;
                font-weight: bold;
            }}
            .tag-bool-false {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .alternatives-list {{
                padding-left: 20px;
                margin: 5px 0;
            }}
            .alternatives-list li {{
                margin-bottom: 3px;
            }}
            .canvas-container {{
                position: relative;
                height: 300px;
                width: 100%;
            }}
            
            /* 增强图表在移动设备上的显示 */
            .chart-wrapper {{
                overflow: hidden;
                width: 100%;
                margin-bottom: 20px;
            }}
            #userTypeChart, #dependencyChart, #frequencyChart {{
                max-width: 100%;
            }}
            
            @media (max-width: 768px) {{
                .stats-container, .chart-container {{
                    flex-direction: column;
                }}
                .simulation-content {{
                    grid-template-columns: 1fr;
                }}
                .persona-header {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                .persona-meta {{
                    margin-top: 10px;
                }}
                .chart {{
                    height: 300px;
                }}
            }}
            
            /* 针对移动设备的增强适配 */
            @media (max-width: 576px) {{
                body {{
                    padding: 10px;
                }}
                .header {{
                    padding: 15px 0;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    font-size: 22px;
                }}
                .section {{
                    padding: 15px;
                    margin: 20px 0;
                }}
                .section h2 {{
                    font-size: 20px;
                }}
                .section h3 {{
                    font-size: 18px;
                }}
                .stats-container {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                }}
                .stat-box {{
                    flex: none;
                    width: auto;
                    margin: 0;
                    padding: 10px;
                }}
                .stat-box h3 {{
                    font-size: 14px;
                }}
                .stat-box p {{
                    font-size: 20px;
                    margin-top: 5px;
                }}
                .chart {{
                    margin: 10px 0;
                    padding: 10px;
                    height: 250px;
                }}
                table {{
                    font-size: 14px;
                    display: block;
                    overflow-x: auto;
                    white-space: nowrap;
                }}
                th, td {{
                    padding: 8px 10px;
                }}
                .persona-card {{
                    padding: 15px;
                    margin: 20px 0;
                }}
                .persona-tag {{
                    font-size: 12px;
                    padding: 3px 8px;
                }}
                .simulation-card {{
                    padding: 12px;
                    margin: 12px 0;
                }}
                .simulation-item-title {{
                    font-size: 15px;
                }}
                .simulation-feedback, .simulation-improvements {{
                    padding: 12px;
                }}
            }}
            
            /* 用户反馈筛选器样式 */
            .filter-container {{
                background-color: #f8f9fa;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .filter-title {{
                font-weight: bold;
                margin-bottom: 10px;
                color: #2c3e50;
            }}
            .filter-options {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 15px;
            }}
            .filter-group {{
                flex: 1 1 200px;
            }}
            .filter-group-title {{
                font-weight: bold;
                margin-bottom: 5px;
                font-size: 14px;
                color: #34495e;
            }}
            .filter-select {{
                width: 100%;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #ddd;
                font-size: 14px;
            }}
            .filter-checkbox-group {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .filter-checkbox {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .filter-checkbox input {{
                margin: 0;
            }}
            .filter-checkbox label {{
                font-size: 14px;
            }}
            .filter-buttons {{
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }}
            .filter-button {{
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
                transition: background-color 0.2s;
            }}
            .apply-button {{
                background-color: #3498db;
                color: white;
            }}
            .apply-button:hover {{
                background-color: #2980b9;
            }}
            .reset-button {{
                background-color: #e74c3c;
                color: white;
            }}
            .reset-button:hover {{
                background-color: #c0392b;
            }}
            .persona-hidden {{
                display: none;
            }}
            @media (max-width: 768px) {{
                .filter-options {{
                    flex-direction: column;
                    gap: 10px;
                }}
                .filter-group {{
                    flex: 1 1 100%;
                }}
            }}
            
            /* 可折叠面板样式 */
            .collapsible-header {{
                cursor: pointer;
                background-color: #f1f1f1;
                padding: 10px 15px;
                margin-bottom: 10px;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: background-color 0.3s;
            }}
            .collapsible-header:hover {{
                background-color: #e9e9e9;
            }}
            .collapsible-title {{
                font-weight: bold;
                color: #2c3e50;
            }}
            .collapsible-icon {{
                font-size: 18px;
                transition: transform 0.3s;
            }}
            .rotate {{
                transform: rotate(180deg);
            }}
            .collapsible-content {{
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.3s ease-out;
            }}
            .expanded {{
                max-height: 10000px; /* 足够大的值以容纳内容 */
                transition: max-height 0.5s ease-in;
            }}
            
            /* 全部展开/收起按钮样式 */
            .toggle-all-btn {{
                display: block;
                margin: 10px 0 15px 0;
                padding: 8px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            .toggle-all-btn:hover {{
                background-color: #2980b9;
            }}
            .toggle-all-btn:before {{
                content: "⇵  ";
                font-weight: bold;
            }}
            
            /* 用户画像级别的折叠/展开按钮 */
            .feedback-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            .feedback-header h4 {{
                margin: 0;
            }}
            .persona-toggle-btn {{
                padding: 6px 12px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .persona-toggle-btn:hover {{
                background-color: #e9ecef;
            }}
            .feedback-container.collapsed {{
                display: none;
            }}
            
            /* 指标说明样式 */
            .indicator-explanations {{
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid #3498db;
            }}
            .indicator-explanations h3 {{
                color: #2c3e50;
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 18px;
                display: flex;
                align-items: center;
            }}
            .info-icon {{
                margin-right: 8px;
                font-size: 20px;
            }}
            .explanation-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
            }}
            .explanation-item {{
                background-color: white;
                border-radius: 6px;
                padding: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }}
            .explanation-item h4 {{
                color: #3498db;
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 16px;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
            }}
            .explanation-item p {{
                margin: 0;
                font-size: 14px;
                line-height: 1.5;
                color: #555;
            }}
            .explanation-item ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .explanation-item li {{
                font-size: 14px;
                margin-bottom: 5px;
                line-height: 1.5;
                color: #555;
            }}
            @media (max-width: 768px) {{
                .explanation-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            /* 新增广告文案部分 */
            .ad-copy-section {{
                margins: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
            }}
            
            .ad-copy h5 {{
                color: #2c3e50;
                margin: 0 0 10px 0;
                font-size: 1.2em;
            }}
            
            .ad-copy p {{
                color: #34495e;
                margin: 0 0 15px 0;
            }}
            
            .ad-details {{
                background: #fff;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0 0 0;
            }}
            
            /* 新增产品优化部分 */
            .product-optimization-section {{
                margins: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #28a745;
            }}
            
            .optimized-product {{
                background: #fff;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0 0 0;
            }}
            
            .optimized-product p {{
                margins: 0 0 10px 0;
            }}
            
            /* 广告文案和产品优化部分的样式 */
            .ad-copy-section, .product-optimization-section {{
                margin: 20px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            
            .ad-copy-section {{
                border-left: 4px solid #ffc107;
            }}
            
            .product-optimization-section {{
                border-left: 4px solid #28a745;
            }}
            
            .ad-copy h5 {{
                color: #2c3e50;
                margin: 0 0 10px 0;
                font-size: 1.2em;
                font-weight: bold;
            }}
            
            .ad-copy p {{
                color: #34495e;
                margin: 0 0 15px 0;
                line-height: 1.5;
            }}
            
            .ad-details {{
                background: #fff;
                padding: 15px;
                border-radius: 4px;
                margin: 10px 0 0 0;
            }}
            
            .ad-details div {{
                margin-bottom: 8px;
            }}
            
            .ad-details div:last-child {{
                margin-bottom: 0;
            }}
            
            .optimized-product {{
                background: #fff;
                padding: 15px;
                border-radius: 4px;
                margin: 10px 0 0 0;
            }}
            
            .optimized-product p {{
                margin: 0 0 15px 0;
                line-height: 1.5;
            }}
            
            .optimized-product ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            
            .optimized-product li {{
                margin-bottom: 8px;
                line-height: 1.4;
            }}
            
            .simulation-content {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
                padding: 20px;
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            
            .simulation-feedback, .simulation-improvements, .ad-copy-section, .product-optimization-section {{
                grid-column: 1 / -1;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>用户研究报告</h1>
            <p class="date">生成日期: {datetime.now().strftime('%Y-%m-%d')}</p>
        </div>

        <div class="section" style="background-color: #e8f4f8; border-left: 4px solid #3498db;">
            <h2 style="color: #2980b9;">产品描述</h2>
            <p style="color: #2c3e50; font-size: 16px; line-height: 1.6; white-space: pre-wrap;">{product_description if product_description else "未提供产品描述"}</p>
        </div>
        {web_section_html}

        <div class="section" style="background-color: #fff3cd; border-left: 4px solid #ffc107;">
            <h2 style="color: #856404;">温馨提示</h2>
            <ul style="color: #856404;">
                <li>微信直接打开可能会出现页面混乱的情况，强烈建议在电脑端下载后直接点开查看</li>
                <li>您可以根据用户反馈优化您的产品描述，然后再次模拟来观察用户反馈的变化</li>
                <li>调研人次越多，对您的产品反馈越准确</li>
            </ul>
        </div>

        <div class="section">
            <h2>1. 数据总览</h2>
            
            <div class="stats-container">
                <div class="stat-box">
                    <h3>参与调研用户总数</h3>
                    <p>{total_users}</p>
                </div>
    """
    
    # 添加用户类型统计框
    if user_types:
        for user_type, count in user_types.items():
            html_content += f"""
                <div class="stat-box">
                    <h3>{user_type}</h3>
                    <p>{count}</p>
                </div>
            """
    
    # 添加刚需比例
    if 'is_must_have' in simulations_df.columns and not simulations_df['is_must_have'].empty:
        html_content += f"""
                <div class="stat-box">
                    <h3>刚需比例</h3>
                    <p>{must_have_percentage:.1f}%</p>
                </div>
        """
    
    # 添加推荐意愿比例
    if 'would_recommend' in simulations_df.columns and not simulations_df['would_recommend'].empty:
        html_content += f"""
                <div class="stat-box">
                    <h3>推荐意愿比例</h3>
                    <p>{would_recommend_percentage:.1f}%</p>
                </div>
        """
    
    html_content += """
            </div>
            
            <!-- 添加指标解释部分 -->
            <div class="indicator-explanations">
                <h3><span class="info-icon">ℹ️</span> 指标说明</h3>
                <div class="explanation-grid">
                    <div class="explanation-item">
                        <h4>用户类型</h4>
                        <ul>
                            <li><strong>核心用户</strong>：产品的主要目标用户群体，其核心需求与产品高度匹配，使用频率高，依赖程度强。</li>
                            <li><strong>潜在用户</strong>：当前未使用或偶尔使用，但有潜力转化为核心用户的群体，需求与产品部分匹配。</li>
                            <li><strong>边缘用户</strong>：对产品有一定需求但不频繁使用，或仅使用产品部分功能的用户群体。</li>
                            <li><strong>非目标用户</strong>：不属于产品目标用户范围，与产品的需求匹配度较低的用户群体。</li>
                        </ul>
                    </div>
                    <div class="explanation-item">
                        <h4>刚需比例</h4>
                        <p>认为产品解决了"必须解决"而非"可以解决"的问题的用户百分比。刚需比例越高，表明产品满足了用户的刚性需求，市场基础越稳固。</p>
                    </div>
                    <div class="explanation-item">
                        <h4>推荐意愿</h4>
                        <p>用户愿意主动向他人推荐产品的比例，反映产品的口碑传播潜力和用户满意度。高推荐意愿通常意味着更强的病毒式增长潜力。</p>
                    </div>
                    <div class="explanation-item">
                        <h4>产品依赖水平</h4>
                        <p>指用户对产品的依赖程度。具体是指：如果产品因故下架或不可用，用户会有何种程度的不便或负面感受。依赖水平越高，说明产品在用户生活或工作中的重要性越高。</p>
                    </div>
                    <div class="explanation-item">
                        <h4>使用频率</h4>
                        <p>用户使用产品的频次分布，反映了产品的黏性和用户习惯养成情况。频率越高的产品通常表明其已深度融入用户的日常生活或工作流程。</p>
                    </div>
                    <div class="explanation-item">
                        <h4>地域分布</h4>
                        <p>用户的地理位置分布情况，反映产品在不同地区的接受程度和市场潜力。可用于制定区域营销策略和本地化需求分析。</p>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
    """
    
    # 用户类型分布图表
    if user_types:
        html_content += """
                <div class="chart">
                    <h3>用户类型分布</h3>
                    <div class="canvas-container">
                        <canvas id="userTypeChart"></canvas>
                    </div>
                </div>
        """
    
    # 产品依赖水平图表
    if dependency_data:
        html_content += """
                <div class="chart">
                    <h3>产品依赖水平</h3>
                    <div class="canvas-container">
                        <canvas id="dependencyChart"></canvas>
                    </div>
                </div>
        """
    
    # 使用频率分布图表
    if frequency_data:
        html_content += """
                <div class="chart">
                    <h3>使用频率分布</h3>
                    <div class="canvas-container">
                        <canvas id="frequencyChart"></canvas>
                    </div>
                </div>
        """
    
    # 地域分布图表
    if location_data:
        html_content += """
                <div class="chart">
                    <h3>地域分布</h3>
                    <div class="canvas-container">
                        <canvas id="locationChart"></canvas>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
    """
    
    # 添加使用频率详情表格
    if frequency_data and frequency_data['labels']:
        html_content += """
            <h3>使用频率详细统计</h3>
            <table>
                <tr>
                    <th>使用频率</th>
                    <th>用户数</th>
                    <th>百分比</th>
                </tr>
        """
        
        frequency_counts = simulations_df['usage_frequency'].value_counts()
        frequency_percentages = (frequency_counts / frequency_counts.sum() * 100).round(1)
        
        for i, freq in enumerate(frequency_data['labels']):
            count = frequency_counts[freq]
            percentage = frequency_percentages[freq]
            html_content += f"""
                <tr>
                    <td>{freq}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
            """
        
        html_content += """
            </table>
        """
    
    # 添加依赖水平详情表格
    if dependency_data and dependency_data['labels']:
        html_content += """
            <h3>产品依赖水平详细统计</h3>
            <table>
                <tr>
                    <th>依赖水平</th>
                    <th>用户数</th>
                    <th>百分比</th>
                </tr>
        """
        
        dependency_counts = simulations_df['dependency_level'].value_counts()
        dependency_percentages = (dependency_counts / dependency_counts.sum() * 100).round(1)
        
        for i, level in enumerate(dependency_data['labels']):
            count = dependency_counts[level]
            percentage = dependency_percentages[level]
            html_content += f"""
                <tr>
                    <td>{level}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
            """
        
        html_content += """
            </table>
        """
    
    html_content += """
        </div>

        <div class="section">
            <h2>2. 用户画像和反馈详情</h2>
            
            <!-- 添加筛选器 -->
            <div class="filter-container">
                <div class="filter-title">用户反馈筛选</div>
                <div class="filter-options">
                    <div class="filter-group">
                        <div class="filter-group-title">用户类型</div>
                        <select id="userTypeFilter" class="filter-select">
                            <option value="all">全部用户类型</option>
                            <option value="核心用户">核心用户</option>
                            <option value="潜在用户">潜在用户</option>
                            <option value="边缘用户">边缘用户</option>
                            <option value="非目标用户">非目标用户</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <div class="filter-group-title">使用频率</div>
                        <select id="frequencyFilter" class="filter-select">
                            <option value="all">全部使用频率</option>
                            <option value="每天多次">每天多次</option>
                            <option value="每天一次">每天一次</option>
                            <option value="每周几次">每周几次</option>
                            <option value="每月几次">每月几次</option>
                            <option value="很少使用">很少使用</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <div class="filter-group-title">地区</div>
                        <select id="locationFilter" class="filter-select">
                            <option value="all">全部地区</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <div class="filter-group-title">排序方式</div>
                        <select id="sortOrder" class="filter-select">
                            <option value="user-type">按用户类型</option>
                            <option value="frequency">按使用频率</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <div class="filter-group-title">用户反馈</div>
                        <div class="filter-checkbox-group">
                            <div class="filter-checkbox">
                                <input type="checkbox" id="wouldTryFilter" value="would_try">
                                <label for="wouldTryFilter">愿意尝试</label>
                            </div>
                            <div class="filter-checkbox">
                                <input type="checkbox" id="wouldBuyFilter" value="would_buy">
                                <label for="wouldBuyFilter">愿意购买</label>
                            </div>
                            <div class="filter-checkbox">
                                <input type="checkbox" id="isMustHaveFilter" value="is_must_have">
                                <label for="isMustHaveFilter">是刚需</label>
                            </div>
                            <div class="filter-checkbox">
                                <input type="checkbox" id="wouldRecommendFilter" value="would_recommend">
                                <label for="wouldRecommendFilter">愿意推荐</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="filter-buttons">
                    <button id="applyFiltersBtn" class="filter-button apply-button">应用筛选</button>
                    <button id="resetFiltersBtn" class="filter-button reset-button">重置筛选</button>
                </div>
                <div style="margin-top: 10px; padding: 8px 12px; background-color: #e8f7ff; border-radius: 4px; color: #0070c9; font-size: 14px;">
                    💡 提示：如果筛选结果为空，建议增加用户画像数量重新模拟，这样可以帮助您找到最适合的目标用户群体。
                </div>
            </div>
    
    """
    
    # 为每个用户画像创建一个卡片
    for persona in personas:
        persona_id = persona.get('persona_id', '')
        user_type = persona.get('user_type', '')
        usage_frequency = persona.get('usage_frequency', '')
        
        # 设置用户类型标签样式
        user_type_class = ''
        if user_type == '核心用户':
            user_type_class = 'tag-core'
        elif user_type == '潜在用户':
            user_type_class = 'tag-potential'
        elif user_type == '边缘用户':
            user_type_class = 'tag-marginal'
        elif user_type == '非目标用户':
            user_type_class = 'tag-non-target'
        
        html_content += f"""
            <div class="persona-card">
                <div class="persona-header">
                    <div class="persona-title">
                        <h3>用户画像 {persona_id}</h3>
                    </div>
                    <div class="persona-meta">
                        <span class="persona-tag {user_type_class}">{user_type}</span>
                        <span class="persona-tag tag-frequency">{usage_frequency}</span>
                        <span class="persona-tag tag-location">{persona.get('location', '未知地区')}</span>
                    </div>
                </div>
        """
        
        # 检查字段是否存在
        if 'persona_description' in persona:
            html_content += f"""
                <div class="persona-description">
                    <p>{persona.get('persona_description', '')}</p>
                </div>
            """
        
        # 检查并添加关键需求
        if 'key_needs' in persona and persona['key_needs']:
            html_content += """
                <h4>关键需求:</h4>
                <ul class="needs-list">
            """
            
            for need in persona.get('key_needs', []):
                html_content += f"<li>{need}</li>"
            
            html_content += """
                </ul>
            """
        
        # 检查并添加使用场景
        if 'usage_scenarios' in persona and persona['usage_scenarios']:
            html_content += """
                <h4>使用场景:</h4>
                <ul class="scenarios-list">
            """
            
            for scenario in persona.get('usage_scenarios', []):
                html_content += f"<li>{scenario}</li>"
            
            html_content += """
                </ul>
            """
        
        # 用户反馈部分标题和折叠控制
        feedback_count = len([sim for sim in cleaned_simulations if sim.get('persona_id', '') == persona_id])
        html_content += f"""
                <div class="feedback-header">
                    <h4>用户反馈 ({feedback_count}条):</h4>
                    <button class="persona-toggle-btn" data-state="expanded">收起全部</button>
                </div>
                <div class="feedback-container">
        """
        
        # 获取该用户画像的所有有效模拟反馈
        current_persona_simulations = [
            sim for sim in cleaned_simulations 
            if sim.get('persona_id', '') == persona_id
        ]
        
        if not current_persona_simulations:
            html_content += "<p>没有找到该用户的有效反馈数据</p>"
        else:
            # 按模拟ID排序，确保显示顺序一致
            current_persona_simulations.sort(key=lambda x: x.get('simulation_id', ''))
            
            for sim in current_persona_simulations:
                simulation_id = sim.get('simulation_id', '')
                simulated_at = sim.get('simulated_at', '')
                
                # 提取关键信息作为摘要
                would_try = "是" if sim.get('would_try', False) else "否"
                would_buy = "是" if sim.get('would_buy', False) else "否"
                is_must_have = "是" if sim.get('is_must_have', False) else "否"
                would_recommend = "是" if sim.get('would_recommend', False) else "否"
                
                # 可折叠面板头部
                html_content += f"""
                <div class="simulation-card">
                    <div class="collapsible-header">
                        <div class="collapsible-title">模拟ID: {simulation_id} | 愿意尝试: {would_try} | 愿意购买: {would_buy} | 是否刚需: {is_must_have} | 是否愿意推荐: {would_recommend}</div>
                        <div class="collapsible-icon">▼</div>
                    </div>
                    <div class="collapsible-content">
                        <div class="simulation-header">
                            <div class="simulation-title">模拟ID: {simulation_id}</div>
                            <div class="simulation-meta">模拟时间: {simulated_at}</div>
                        </div>
                        <div class="simulation-content">
                """
                
                # 动态添加模拟内容，检查每个字段是否存在
                fields_to_check = [
                    ('initial_impression', '初始印象'),
                    ('perceived_needs', '感知需求'),
                    ('would_try', '愿意尝试'),
                    ('would_buy', '愿意购买'),
                    ('is_must_have', '是否刚需'),
                    ('would_recommend', '是否愿意推荐'),
                    ('dependency_level', '依赖水平'),
                    ('barrier_to_adoption', '采用障碍')
                ]
                
                for field, title in fields_to_check:
                    if field in sim:
                        value = sim.get(field, '')
                        
                        # 对布尔值进行特殊处理
                        if isinstance(value, bool):
                            html_content += f"""
                            <div class="simulation-item">
                                <div class="simulation-item-title">{title}</div>
                                <div class="{'tag-bool-true' if value else 'tag-bool-false'}">
                                    {'是' if value else '否'}
                                </div>
                            </div>
                            """
                        else:
                            html_content += f"""
                            <div class="simulation-item">
                                <div class="simulation-item-title">{title}</div>
                                <div>{value}</div>
                            </div>
                            """
                
                # 处理备选方案列表
                if 'alternatives' in sim and isinstance(sim['alternatives'], list):
                    html_content += """
                    <div class="simulation-item">
                        <div class="simulation-item-title">备选方案</div>
                        <ul class="alternatives-list">
                    """
                    
                    for alt in sim.get('alternatives', []):
                        if isinstance(alt, str) and alt and alt != "无法确定":
                            html_content += f"<li>{alt}</li>"
                    
                    html_content += """
                        </ul>
                    </div>
                    """
                
                # 添加详细反馈
                if 'feedback' in sim and isinstance(sim['feedback'], str):
                    html_content += f"""
                    <div class="simulation-feedback">
                        <div class="simulation-item-title">详细反馈</div>
                        <div>{sim.get('feedback', '')}</div>
                    </div>
                    """
                
                # 添加改进建议
                if 'suggested_improvements' in sim and isinstance(sim['suggested_improvements'], str):
                    html_content += f"""
                    <div class="simulation-improvements">
                        <div class="simulation-item-title">改进建议</div>
                        <div>{sim.get('suggested_improvements', '')}</div>
                    </div>
                    """
                
                # 添加广告文案部分
                if 'ad_copy' in sim and isinstance(sim['ad_copy'], dict):
                    ad_copy = sim['ad_copy']
                    html_content += f"""
                    <div class="ad-copy-section">
                        <div class="simulation-item-title">广告文案建议</div>
                        <div class="ad-copy">
                            <h5>标题：{ad_copy.get('ad_headline', '未生成')}</h5>
                            <p>正文：{ad_copy.get('ad_body', '未生成')}</p>
                            <div class="ad-details">
                                <div><strong>核心痛点：</strong> {', '.join(ad_copy.get('key_pain_points', ['未指定']))}</div>
                                <div><strong>目标情感：</strong> {', '.join(ad_copy.get('target_emotions', ['未指定']))}</div>
                            </div>
                        </div>
                    </div>
                    """
                
                # 添加优化产品描述部分
                if 'optimized_product' in sim and isinstance(sim['optimized_product'], dict):
                    opt_product = sim['optimized_product']
                    html_content += f"""
                    <div class="product-optimization-section">
                        <div class="simulation-item-title">产品优化建议</div>
                        <div class="optimized-product">
                            <p><strong>优化后的产品描述：</strong><br>{opt_product.get('optimized_description', '未生成')}</p>
                            <p><strong>关键改进点：</strong></p>
                            <ul>
                                {' '.join(f'<li>{item}</li>' for item in opt_product.get('key_improvements', ['未指定']))}
                            </ul>
                            <p><strong>预期收益：</strong></p>
                            <ul>
                                {' '.join(f'<li>{item}</li>' for item in opt_product.get('expected_benefits', ['未指定']))}
                            </ul>
                            <p><strong>实施优先级：</strong> {opt_product.get('implementation_priority', '中')}</p>
                        </div>
                    </div>
                    """
                
                html_content += """
                        </div>
                    </div>
                </div>
                """
        
        html_content += """
                </div>
            </div>
        """

    # Chart.js脚本
    html_content += f"""
        </div>

        <!-- Footer moved to bottom after References section -->

        <script>
            // 准备图表数据
            document.addEventListener('DOMContentLoaded', function() {{
                // 检测浏览器类型
                const isChrome = /Chrome/.test(navigator.userAgent) && !/Edge/.test(navigator.userAgent);
                const isWechat = /MicroMessenger/i.test(navigator.userAgent);
                const isWeixin = /WeiBo/i.test(navigator.userAgent) || /MicroMessenger/i.test(navigator.userAgent);
                const isMobile = window.innerWidth < 576;
                
                // Chrome浏览器特定处理
                if (isChrome) {{
                    // 确保Chart.js完全加载
                    if (typeof Chart === 'undefined') {{
                        console.error('Chart.js未正确加载');
                        useTableFallback = true;
                    }}
                }}
                
                // 微信浏览器图表兼容处理
                if (isWeixin) {{
                    // 尝试从URL参数中检测是否需要强制表格模式
                    const forceTable = new URLSearchParams(window.location.search).get('forcetable') === '1';
                    
                    // 记录原始图表数据供可能的备用显示使用
                    window.chartData = {{
                        userTypes: {{
                            labels: {json.dumps(user_type_data['labels'])},
                            data: {json.dumps(user_type_data['data'])}
                        }},
                        dependencyLevels: {{
                            labels: {json.dumps(dependency_data.get('labels', []))},
                            data: {json.dumps(dependency_data.get('data', []))}
                        }},
                        frequency: {{
                            labels: {json.dumps(frequency_data.get('labels', []))},
                            data: {json.dumps(frequency_data.get('data', []))}
                        }},
                        location: {{
                            labels: {json.dumps(location_data.get('labels', []))},
                            data: {json.dumps(location_data.get('data', []))}
                        }}
                    }};
                    
                    // 创建微信图表备用方案 - 用表格代替图表
                    const createTableFromChart = (container, chartData, title) => {{
                        if (!chartData || !chartData.labels || !chartData.data) return;
                        
                        // 确保container是DOM元素
                        if (typeof container === 'string') {{
                            container = document.querySelector(container);
                        }}
                        
                        if (!container) return;
                        
                        // 创建标题
                        const titleEl = document.createElement('h3');
                        titleEl.textContent = title;
                        titleEl.style.fontSize = '18px';
                        titleEl.style.color = '#2980b9';
                        titleEl.style.marginBottom = '15px';
                        
                        // 创建表格
                        const table = document.createElement('table');
                        table.style.width = '100%';
                        table.style.borderCollapse = 'collapse';
                        table.style.marginBottom = '20px';
                        table.style.fontSize = '14px';
                        table.setAttribute('role', 'table');
                        table.setAttribute('aria-label', title + '数据表');
                        
                        // 添加表头
                        const thead = document.createElement('thead');
                        thead.setAttribute('role', 'rowgroup');
                        const headerRow = document.createElement('tr');
                        headerRow.setAttribute('role', 'row');
                        
                        const typeHeader = document.createElement('th');
                        typeHeader.textContent = '类型';
                        typeHeader.style.padding = '8px';
                        typeHeader.style.backgroundColor = '#f2f2f2';
                        typeHeader.style.textAlign = 'left';
                        typeHeader.style.borderBottom = '1px solid #ddd';
                        typeHeader.setAttribute('role', 'columnheader');
                        typeHeader.setAttribute('scope', 'col');
                        
                        const countHeader = document.createElement('th');
                        countHeader.textContent = '数量';
                        countHeader.style.padding = '8px';
                        countHeader.style.backgroundColor = '#f2f2f2';
                        countHeader.style.textAlign = 'right';
                        countHeader.style.borderBottom = '1px solid #ddd';
                        countHeader.setAttribute('role', 'columnheader');
                        countHeader.setAttribute('scope', 'col');
                        
                        const percentHeader = document.createElement('th');
                        percentHeader.textContent = '占比';
                        percentHeader.style.padding = '8px';
                        percentHeader.style.backgroundColor = '#f2f2f2';
                        percentHeader.style.textAlign = 'right';
                        percentHeader.style.borderBottom = '1px solid #ddd';
                        percentHeader.setAttribute('role', 'columnheader');
                        percentHeader.setAttribute('scope', 'col');
                        
                        headerRow.appendChild(typeHeader);
                        headerRow.appendChild(countHeader);
                        headerRow.appendChild(percentHeader);
                        thead.appendChild(headerRow);
                        table.appendChild(thead);
                        
                        // 计算总数
                        const total = chartData.data.reduce((sum, val) => sum + val, 0);
                        
                        // 添加数据行
                        const tbody = document.createElement('tbody');
                        tbody.setAttribute('role', 'rowgroup');
                        
                        for (let i = 0; i < chartData.labels.length; i++) {{
                            const row = document.createElement('tr');
                            row.setAttribute('role', 'row');
                            // 隔行变色
                            if (i % 2 === 1) {{
                                row.style.backgroundColor = '#f9f9f9';
                            }}
                            
                            const typeCell = document.createElement('td');
                            typeCell.textContent = chartData.labels[i];
                            typeCell.style.padding = '8px';
                            typeCell.style.borderBottom = '1px solid #ddd';
                            typeCell.setAttribute('role', 'cell');
                            
                            const countCell = document.createElement('td');
                            countCell.textContent = chartData.data[i];
                            countCell.style.padding = '8px';
                            countCell.style.textAlign = 'right';
                            countCell.style.borderBottom = '1px solid #ddd';
                            countCell.setAttribute('role', 'cell');
                            
                            // 计算百分比和颜色
                            const percent = Math.round((chartData.data[i] / total) * 100);
                            
                            const percentCell = document.createElement('td');
                            percentCell.textContent = percent + '%';
                            percentCell.style.padding = '8px';
                            percentCell.style.textAlign = 'right';
                            percentCell.style.borderBottom = '1px solid #ddd';
                            percentCell.setAttribute('role', 'cell');
                            
                            // 根据百分比设置颜色
                            if (percent > 50) {{
                                percentCell.style.color = '#27ae60'; // 绿色
                                percentCell.style.fontWeight = 'bold';
                            }} else if (percent > 25) {{
                                percentCell.style.color = '#f39c12'; // 橙色
                            }}
                            
                            row.appendChild(typeCell);
                            row.appendChild(countCell);
                            row.appendChild(percentCell);
                            tbody.appendChild(row);
                        }}
                        table.appendChild(tbody);
                        
                        // 清空并重新添加内容
                        container.innerHTML = '';
                        container.appendChild(titleEl);
                        container.appendChild(table);
                    }};
                    
                    // 尝试加载Chart.js，如果失败则使用备用表格
                    setTimeout(() => {{
                        // 检查是否强制显示表格或图表未正确渲染
                        let useTableFallback = forceTable;
                        
                        if (!useTableFallback) {{
                            try {{
                                const canvasElements = document.querySelectorAll('canvas');
                                // 检查canvas是否至少有一个没有渲染
                                let emptyCanvasFound = false;
                                
                                canvasElements.forEach(canvas => {{
                                    try {{
                                        const context = canvas.getContext('2d');
                                        const data = context.getImageData(0, 0, 1, 1).data;
                                        // 如果完全透明，认为画布是空的
                                        if (data[3] === 0) {{
                                            emptyCanvasFound = true;
                                        }}
                                    }} catch (e) {{
                                        // 如果无法获取图像数据（可能是跨域或其他错误），认为有问题
                                        console.warn('Canvas检查失败:', e);
                                        emptyCanvasFound = true;
                                    }}
                                }});
                                
                                useTableFallback = emptyCanvasFound;
                            }} catch (e) {{
                                console.warn('Canvas检查异常，使用表格备用:', e);
                                useTableFallback = true;
                            }}
                        }}
                        
                        if (useTableFallback) {{
                            // Chart.js可能未加载成功，替换为表格
                            document.querySelectorAll('.canvas-container').forEach(container => {{
                                container.style.height = 'auto';
                            }});
                            
                            // 添加微信提示信息
                            const wechatNotice = document.createElement('div');
                            wechatNotice.style.backgroundColor = '#e8f7ff';
                            wechatNotice.style.border = '1px solid #c3e6ff';
                            wechatNotice.style.padding = '10px 15px';
                            wechatNotice.style.borderRadius = '4px';
                            wechatNotice.style.marginBottom = '15px';
                            wechatNotice.style.color = '#0070c9';
                            wechatNotice.style.fontSize = '14px';
                            wechatNotice.style.lineHeight = '1.5';
                            wechatNotice.innerHTML = '提示: 微信中图表不支持完整显示，已转为表格形式。更好的体验请使用系统浏览器打开或下载至电脑端查看。';
                            
                            const chartContainer = document.querySelector('.chart-container');
                            if (chartContainer) {{
                                chartContainer.insertBefore(wechatNotice, chartContainer.firstChild);
                            }}
                            
                            try {{
                                // 更安全的选择器方式
                                const chartContainers = document.querySelectorAll('.chart');
                                
                                chartContainers.forEach(container => {{
                                    // 检查包含哪个canvas
                                    if (container.querySelector('#userTypeChart') && window.chartData.userTypes.labels.length > 0) {{
                                        createTableFromChart(container, window.chartData.userTypes, '用户类型分布');
                                    }}
                                    else if (container.querySelector('#dependencyChart') && window.chartData.dependencyLevels.labels.length > 0) {{
                                        createTableFromChart(container, window.chartData.dependencyLevels, '产品依赖水平');
                                    }}
                                    else if (container.querySelector('#frequencyChart') && window.chartData.frequency.labels.length > 0) {{
                                        createTableFromChart(container, window.chartData.frequency, '使用频率分布');
                                    }}
                                    else if (container.querySelector('#locationChart') && window.chartData.location.labels.length > 0) {{
                                        createTableFromChart(container, window.chartData.location, '地域分布');
                                    }}
                                }});
                            }} catch (e) {{
                                console.error('图表转换为表格失败:', e);
                            }}
                        }}
                    }}, 2000); // 等待2秒检查图表是否加载
                }}
                
                // 移动设备优化
                if (isMobile) {{
                    // 确保视口设置正确
                    const viewportMeta = document.querySelector('meta[name="viewport"]');
                    if (viewportMeta) {{
                        viewportMeta.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0');
                    }}
                    
                    // 调整表格适应移动视口
                    document.querySelectorAll('table').forEach(table => {{
                        if (table.offsetWidth > window.innerWidth) {{
                            table.style.display = 'block';
                            table.style.overflowX = 'auto';
                        }}
                    }});
                }}
                
                // 根据设备调整图表配置
                const commonChartOptions = {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: isMobile ? 'bottom' : 'right',
                            labels: {{
                                font: {{
                                    size: isMobile ? 12 : 14
                                }},
                                boxWidth: isMobile ? 15 : 30,
                                padding: isMobile ? 10 : 15
                            }}
                        }}
                    }}
                }};
                
                // 用户类型分布图
                const userTypeCtx = document.getElementById('userTypeChart');
                if (userTypeCtx) {{
                    new Chart(userTypeCtx, {{
                        type: 'pie',
                        data: {{
                            labels: {json.dumps(user_type_data['labels'])},
                            datasets: [{{
                                data: {json.dumps(user_type_data['data'])},
                                backgroundColor: {json.dumps(user_type_colors[:len(user_type_data['labels'])])},
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            ...commonChartOptions,
                            plugins: {{
                                ...commonChartOptions.plugins,
                                title: {{
                                    display: true,
                                    text: '用户类型分布',
                                    font: {{
                                        size: isMobile ? 16 : 18
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${{label}}: ${{value}} (${{percentage}}%)`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
                
                // 依赖水平分布图
                const dependencyCtx = document.getElementById('dependencyChart');
                if (dependencyCtx) {{
                    new Chart(dependencyCtx, {{
                        type: 'pie',
                        data: {{
                            labels: {json.dumps(dependency_data.get('labels', []))},
                            datasets: [{{
                                data: {json.dumps(dependency_data.get('data', []))},
                                backgroundColor: {json.dumps(dependency_colors[:len(dependency_data.get('labels', []))])},
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            ...commonChartOptions,
                            plugins: {{
                                ...commonChartOptions.plugins,
                                title: {{
                                    display: true,
                                    text: '产品依赖水平',
                                    font: {{
                                        size: isMobile ? 16 : 18
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            return `${{label}}: ${{value}}%`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
                
                // 地域分布图
                const locationCtx = document.getElementById('locationChart');
                if (locationCtx) {{
                    new Chart(locationCtx, {{
                        type: 'pie',
                        data: {{
                            labels: {json.dumps(location_data.get('labels', []))},
                            datasets: [{{
                                data: {json.dumps(location_data.get('data', []))},
                                backgroundColor: {json.dumps(location_colors[:len(location_data.get('labels', []))])},
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            ...commonChartOptions,
                            plugins: {{
                                ...commonChartOptions.plugins,
                                title: {{
                                    display: true,
                                    text: '地域分布',
                                    font: {{
                                        size: isMobile ? 16 : 18
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            return `${{label}}: ${{value}}%`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
                
                // 使用频率分布图
                const frequencyCtx = document.getElementById('frequencyChart');
                if (frequencyCtx) {{
                    new Chart(frequencyCtx, {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(frequency_data.get('labels', []))},
                            datasets: [{{
                                label: '使用比例',
                                data: {json.dumps(frequency_data.get('data', []))},
                                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    title: {{
                                        display: true,
                                        text: '百分比 (%)',
                                        font: {{
                                            size: isMobile ? 12 : 14
                                        }}
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: isMobile ? 12 : 14
                                        }}
                                    }}
                                }},
                                x: {{
                                    title: {{
                                        display: true,
                                        text: '使用频率',
                                        font: {{
                                            size: isMobile ? 12 : 14
                                        }}
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: isMobile ? 12 : 14
                                        }}
                                    }}
                                }}
                            }},
                            plugins: {{
                                legend: {{
                                    display: false
                                }},
                                title: {{
                                    display: true,
                                    text: '使用频率分布',
                                    font: {{
                                        size: isMobile ? 16 : 18
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            return `${{context.raw}}%`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
            }});
            
            // 用户反馈筛选功能
            (() => {{
                // 获取筛选器元素
                const userTypeFilter = document.getElementById('userTypeFilter');
                const frequencyFilter = document.getElementById('frequencyFilter');
                const locationFilter = document.getElementById('locationFilter');
                const sortOrderSelect = document.getElementById('sortOrder');
                const wouldTryFilter = document.getElementById('wouldTryFilter');
                const wouldBuyFilter = document.getElementById('wouldBuyFilter');
                const isMustHaveFilter = document.getElementById('isMustHaveFilter');
                const wouldRecommendFilter = document.getElementById('wouldRecommendFilter');
                const applyFiltersBtn = document.getElementById('applyFiltersBtn');
                const resetFiltersBtn = document.getElementById('resetFiltersBtn');
                
                // 获取所有用户画像卡片
                const personaCards = document.querySelectorAll('.persona-card');
                const personaContainer = personaCards.length > 0 ? personaCards[0].parentNode : null;
                
                // 用户类型和频率的排序优先级
                const userTypeOrder = {{
                    '核心用户': 1,
                    '潜在用户': 2,
                    '边缘用户': 3,
                    '非目标用户': 4
                }};
                
                const frequencyOrder = {{
                    '每天多次': 1,
                    '每天一次': 2,
                    '每周几次': 3,
                    '每月几次': 4,
                    '很少使用': 5
                }};
                
                // 排序函数
                function sortPersonas() {{
                    if (!personaContainer) return;
                    
                    const sortType = sortOrderSelect.value;
                    const cardsArray = Array.from(personaCards);
                    
                    cardsArray.sort((a, b) => {{
                        if (sortType === 'user-type') {{
                            // 按用户类型排序
                            const aTypeTag = a.querySelector('.persona-tag:not(.tag-frequency)');
                            const bTypeTag = b.querySelector('.persona-tag:not(.tag-frequency)');
                            
                            const aType = aTypeTag ? aTypeTag.textContent : '';
                            const bType = bTypeTag ? bTypeTag.textContent : '';
                            
                            const aOrder = userTypeOrder[aType] || 999;
                            const bOrder = userTypeOrder[bType] || 999;
                            
                            if (aOrder !== bOrder) {{
                                return aOrder - bOrder;
                            }}
                            
                            // 如果用户类型相同，按使用频率排序
                            const aFreqTag = a.querySelector('.tag-frequency');
                            const bFreqTag = b.querySelector('.tag-frequency');
                            
                            const aFreq = aFreqTag ? aFreqTag.textContent : '';
                            const bFreq = bFreqTag ? bFreqTag.textContent : '';
                            
                            return (frequencyOrder[aFreq] || 999) - (frequencyOrder[bFreq] || 999);
                        }} else {{
                            // 按使用频率排序
                            const aFreqTag = a.querySelector('.tag-frequency');
                            const bFreqTag = b.querySelector('.tag-frequency');
                            
                            const aFreq = aFreqTag ? aFreqTag.textContent : '';
                            const bFreq = bFreqTag ? bFreqTag.textContent : '';
                            
                            const aOrder = frequencyOrder[aFreq] || 999;
                            const bOrder = frequencyOrder[bFreq] || 999;
                            
                            if (aOrder !== bOrder) {{
                                return aOrder - bOrder;
                            }}
                            
                            // 如果使用频率相同，按用户类型排序
                            const aTypeTag = a.querySelector('.persona-tag:not(.tag-frequency)');
                            const bTypeTag = b.querySelector('.persona-tag:not(.tag-frequency)');
                            
                            const aType = aTypeTag ? aTypeTag.textContent : '';
                            const bType = bTypeTag ? bTypeTag.textContent : '';
                            
                            return (userTypeOrder[aType] || 999) - (userTypeOrder[bType] || 999);
                        }}
                    }});
                    
                    // 重新插入排序后的卡片
                    cardsArray.forEach(card => {{
                        personaContainer.appendChild(card);
                    }});
                }}
                
                // 应用筛选逻辑
                function applyFilters() {{
                    const selectedUserType = userTypeFilter.value;
                    const selectedFrequency = frequencyFilter.value;
                    const selectedLocation = locationFilter.value;
                    const filterWouldTry = wouldTryFilter.checked;
                    const filterWouldBuy = wouldBuyFilter.checked;
                    const filterIsMustHave = isMustHaveFilter.checked;
                    const filterWouldRecommend = wouldRecommendFilter.checked;
                    
                    // 遍历所有用户画像卡片
                    personaCards.forEach(card => {{
                        let shouldShow = true;
                        
                        // 检查用户类型
                        if (selectedUserType !== 'all') {{
                            const userTypeTag = card.querySelector('.persona-tag');
                            if (!userTypeTag || userTypeTag.textContent !== selectedUserType) {{
                                shouldShow = false;
                            }}
                        }}
                        
                        // 检查使用频率
                        if (shouldShow && selectedFrequency !== 'all') {{
                            const frequencyTag = card.querySelector('.tag-frequency');
                            if (!frequencyTag || frequencyTag.textContent !== selectedFrequency) {{
                                shouldShow = false;
                            }}
                        }}
                        
                        // 检查地区
                        if (shouldShow && selectedLocation !== 'all') {{
                            const locationTag = card.querySelector('.tag-location');
                            if (!locationTag || locationTag.textContent !== selectedLocation) {{
                                shouldShow = false;
                            }}
                        }}
                        
                        // 获取该用户的所有模拟数据
                        const simulationCards = card.querySelectorAll('.simulation-card');
                        let matchesSimulationCriteria = false;
                        
                        // 如果没有选中任何复选框，则视为通过这部分筛选
                        if (!filterWouldTry && !filterWouldBuy && !filterIsMustHave && !filterWouldRecommend) {{
                            matchesSimulationCriteria = true;
                        }} else {{
                            // 检查每个模拟数据是否符合所有选中的复选框条件
                            simulationCards.forEach(simCard => {{
                                let matchesAllChecked = true;
                                
                                // 检查"愿意尝试"
                                if (filterWouldTry) {{
                                    const wouldTryElements = simCard.querySelectorAll('.simulation-item-title');
                                    let foundWouldTry = false;
                                    for (let i = 0; i < wouldTryElements.length; i++) {{
                                        if (wouldTryElements[i].textContent.includes('愿意尝试')) {{
                                            const parentItem = wouldTryElements[i].closest('.simulation-item');
                                            if (parentItem && parentItem.querySelector('.tag-bool-true')) {{
                                                foundWouldTry = true;
                                                break;
                                            }}
                                        }}
                                    }}
                                    if (!foundWouldTry) {{
                                        matchesAllChecked = false;
                                    }}
                                }}
                                
                                // 检查"愿意购买"
                                if (matchesAllChecked && filterWouldBuy) {{
                                    const wouldBuyElements = simCard.querySelectorAll('.simulation-item-title');
                                    let foundWouldBuy = false;
                                    for (let i = 0; i < wouldBuyElements.length; i++) {{
                                        if (wouldBuyElements[i].textContent.includes('愿意购买')) {{
                                            const parentItem = wouldBuyElements[i].closest('.simulation-item');
                                            if (parentItem && parentItem.querySelector('.tag-bool-true')) {{
                                                foundWouldBuy = true;
                                                break;
                                            }}
                                        }}
                                    }}
                                    if (!foundWouldBuy) {{
                                        matchesAllChecked = false;
                                    }}
                                }}
                                
                                // 检查"是否刚需"
                                if (matchesAllChecked && filterIsMustHave) {{
                                    const isMustHaveElements = simCard.querySelectorAll('.simulation-item-title');
                                    let foundIsMustHave = false;
                                    for (let i = 0; i < isMustHaveElements.length; i++) {{
                                        if (isMustHaveElements[i].textContent.includes('是否刚需')) {{
                                            const parentItem = isMustHaveElements[i].closest('.simulation-item');
                                            if (parentItem && parentItem.querySelector('.tag-bool-true')) {{
                                                foundIsMustHave = true;
                                                break;
                                            }}
                                        }}
                                    }}
                                    if (!foundIsMustHave) {{
                                        matchesAllChecked = false;
                                    }}
                                }}
                                
                                // 检查"是否愿意推荐"
                                if (matchesAllChecked && filterWouldRecommend) {{
                                    const wouldRecommendElements = simCard.querySelectorAll('.simulation-item-title');
                                    let foundWouldRecommend = false;
                                    for (let i = 0; i < wouldRecommendElements.length; i++) {{
                                        if (wouldRecommendElements[i].textContent.includes('是否愿意推荐')) {{
                                            const parentItem = wouldRecommendElements[i].closest('.simulation-item');
                                            if (parentItem && parentItem.querySelector('.tag-bool-true')) {{
                                                foundWouldRecommend = true;
                                                break;
                                            }}
                                        }}
                                    }}
                                    if (!foundWouldRecommend) {{
                                        matchesAllChecked = false;
                                    }}
                                }}
                                
                                // 如果这个模拟数据符合所有条件，设置整个用户符合条件
                                if (matchesAllChecked) {{
                                    matchesSimulationCriteria = true;
                                }}
                            }});
                        }}
                        
                        // 只有当用户类型、使用频率和模拟数据都符合条件时，才显示该用户
                        shouldShow = shouldShow && matchesSimulationCriteria;
                        
                        // 显示或隐藏用户画像卡片
                        if (shouldShow) {{
                            card.classList.remove('persona-hidden');
                        }} else {{
                            card.classList.add('persona-hidden');
                        }}
                    }});
                    
                    // 应用排序
                    sortPersonas();
                }}
                
                // 重置所有筛选器
                function resetFilters() {{
                    userTypeFilter.value = 'all';
                    frequencyFilter.value = 'all';
                    locationFilter.value = 'all';
                    sortOrderSelect.value = 'user-type'; // 默认按用户类型排序
                    wouldTryFilter.checked = false;
                    wouldBuyFilter.checked = false;
                    isMustHaveFilter.checked = false;
                    wouldRecommendFilter.checked = false;
                    
                    // 显示所有用户画像卡片
                    personaCards.forEach(card => {{
                        card.classList.remove('persona-hidden');
                    }});
                    
                    // 重置为默认排序
                    sortPersonas();
                }}
                
                // 为Element添加closest方法的polyfill
                if (!Element.prototype.closest) {{
                    Element.prototype.closest = function(s) {{
                        var el = this;
                        do {{
                            if (el.matches(s)) return el;
                            el = el.parentElement || el.parentNode;
                        }} while (el && el.nodeType === 1);
                        return null;
                    }};
                }}
                
                // 绑定事件监听器
                if (applyFiltersBtn) {{
                    applyFiltersBtn.addEventListener('click', applyFilters);
                }}
                
                if (resetFiltersBtn) {{
                    resetFiltersBtn.addEventListener('click', resetFilters);
                }}
                
                if (sortOrderSelect) {{
                    sortOrderSelect.addEventListener('change', sortPersonas);
                }}
                
                // 页面加载后初始化排序
                sortPersonas();
                
                // 处理折叠面板功能
                const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
                
                // 初始化所有面板为收起状态
                collapsibleHeaders.forEach(header => {{
                    const content = header.nextElementSibling;
                    // 默认收起
                    content.classList.remove('expanded');
                    header.addEventListener('click', () => {{
                        // 切换内容区域的展开/收起状态
                        content.classList.toggle('expanded');
                        // 切换箭头方向
                        header.querySelector('.collapsible-icon').classList.toggle('rotate');
                    }});
                }});
            }})();
            
            // 添加全部展开/收起的功能
            (() => {{
                // 在反馈容器前添加全部展开/收起按钮
                document.querySelectorAll('.feedback-container').forEach(container => {{
                    const toggleAllBtn = document.createElement('button');
                    toggleAllBtn.textContent = '全部展开';
                    toggleAllBtn.className = 'toggle-all-btn';
                    toggleAllBtn.setAttribute('data-state', 'collapsed');
                    
                    // 将按钮插入到反馈容器前面
                    container.parentNode.insertBefore(toggleAllBtn, container);
                    
                    // 添加点击事件
                    toggleAllBtn.addEventListener('click', () => {{
                        const currentState = toggleAllBtn.getAttribute('data-state');
                        const headers = container.querySelectorAll('.collapsible-header');
                        const contents = container.querySelectorAll('.collapsible-content');
                        const icons = container.querySelectorAll('.collapsible-icon');
                        
                        if (currentState === 'collapsed') {{
                            // 全部展开
                            contents.forEach(content => content.classList.add('expanded'));
                            icons.forEach(icon => icon.classList.add('rotate'));
                            toggleAllBtn.textContent = '全部收起';
                            toggleAllBtn.setAttribute('data-state', 'expanded');
                        }} else {{
                            // 全部收起
                            contents.forEach(content => content.classList.remove('expanded'));
                            icons.forEach(icon => icon.classList.remove('rotate'));
                            toggleAllBtn.textContent = '全部展开';
                            toggleAllBtn.setAttribute('data-state', 'collapsed');
                        }}
                    }});
                }});
                
                // 处理用户画像级别的折叠/展开功能
                document.querySelectorAll('.persona-toggle-btn').forEach(btn => {{
                    btn.addEventListener('click', () => {{
                        const feedbackContainer = btn.closest('.persona-card').querySelector('.feedback-container');
                        const currentState = btn.getAttribute('data-state');
                        
                        if (currentState === 'expanded') {{
                            // 收起全部
                            feedbackContainer.classList.add('collapsed');
                            btn.textContent = '展开全部';
                            btn.setAttribute('data-state', 'collapsed');
                        }} else {{
                            // 展开全部
                            feedbackContainer.classList.remove('collapsed');
                            btn.textContent = '收起全部';
                            btn.setAttribute('data-state', 'expanded');
                        }}
                    }});
                }});
            }})();
            
            // 初始化筛选器
            const personaContainer = document.querySelector('.section');
            const personaCards = document.querySelectorAll('.persona-card');
            const userTypeFilter = document.getElementById('userTypeFilter');
            const frequencyFilter = document.getElementById('frequencyFilter');
            const locationFilter = document.getElementById('locationFilter');
            const sortOrderSelect = document.getElementById('sortOrder');
            const wouldTryFilter = document.getElementById('wouldTryFilter');
            const wouldBuyFilter = document.getElementById('wouldBuyFilter');
            const isMustHaveFilter = document.getElementById('isMustHaveFilter');
            const wouldRecommendFilter = document.getElementById('wouldRecommendFilter');
            const applyFiltersBtn = document.getElementById('applyFiltersBtn');
            const resetFiltersBtn = document.getElementById('resetFiltersBtn');
            
            // 动态加载地区选项
            const loadLocationOptions = () => {{
                const locations = new Set();
                personaCards.forEach(card => {{
                    const locationTag = card.querySelector('.tag-location');
                    if (locationTag) {{
                        locations.add(locationTag.textContent);
                    }}
                }});
                
                // 按字母顺序排序地区
                const sortedLocations = Array.from(locations).sort();
                
                // 添加地区选项
                sortedLocations.forEach(location => {{
                    const option = document.createElement('option');
                    option.value = location;
                    option.textContent = location;
                    locationFilter.appendChild(option);
                }});
            }};
            
            // 加载地区选项
            loadLocationOptions();
        </script>
    </body>
    </html>
    """

    # 在</body>前插入Web搜索引用（如果有）
    if web_search_references_markdown and web_search_references_markdown.strip():
        # 将Markdown转换为HTML（简单处理）
        references_html = web_search_references_markdown

        # 处理标题 - removed "📑 References (summarized)" subtitle since main heading "📚 参考资料" already exists
        # references_html = references_html.replace('### References (summarized)', '<h3 style="color: #2c3e50; margin-bottom: 15px; font-size: 20px;">📑 References (summarized)</h3>')
        references_html = references_html.replace('### References (summarized)', '')  # Remove the subtitle

        # 处理链接和引用格式: [1] **标题** — `url`
        import re
        # 匹配格式: [数字] **标题** — `url`
        pattern = r'\[(\d+)\]\s+\*\*([^*]+)\*\*\s+—\s+`([^`]+)`'
        references_html = re.sub(
            pattern,
            r'<div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-left: 3px solid #3498db; border-radius: 4px;">'
            r'<div style="font-weight: 600; color: #2c3e50; margin-bottom: 8px;">[\1] \2</div>'
            r'<div style="font-size: 13px; color: #7f8c8d; word-break: break-all;"><a href="\3" target="_blank" style="color: #3498db; text-decoration: none;">\3</a></div>',
            references_html
        )

        # 处理引用内容 (blockquote)
        # 匹配 "> 内容"
        references_html = re.sub(
            r'^>\s*(.+)$',
            r'<blockquote style="margin: 10px 0 0 0; padding: 10px 15px; border-left: 3px solid #bdc3c7; background: white; font-style: italic; color: #555;">\1</blockquote></div>',
            references_html,
            flags=re.MULTILINE
        )

        # 处理换行
        references_html = references_html.replace('\n\n', '<br><br>')

        # 构建References部分的HTML
        references_section = f"""

        <!-- Web Search References Section -->
        <div class="section" style="margin-top: 60px; padding: 30px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50; margin-bottom: 25px; font-size: 28px; border-bottom: 3px solid #3498db; padding-bottom: 10px; display: inline-block;">📚 参考资料</h2>
            <div style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 20px;">
                {references_html}
            </div>
        </div>

        <!-- Footer at the very bottom -->
        <div class="footer">
            <p style="text-align: center; margin-top: 40px; color: #7f8c8d;">© {datetime.now().year} 用户研究报告 | 自动生成</p>
        </div>
        """

        # 在</body>前插入
        html_content = html_content.replace('    </body>', f'{references_section}\n    </body>')

    # 将HTML内容写入文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"报告已生成: {output_file}")
        return output_file
    except Exception as e:
        print(f"写入报告文件时出错: {e}")
        return None

def main():
    """命令行入口点"""
    import argparse
    
    parser = argparse.ArgumentParser(description='根据用户画像和模拟数据生成HTML报告')
    parser.add_argument('personas_file', help='personas JSON文件路径')
    parser.add_argument('simulations_file', help='simulations JSON文件路径')
    parser.add_argument('-o', '--output', help='输出HTML文件路径（可选）')
    
    args = parser.parse_args()
    
    generate_report(args.personas_file, args.simulations_file, args.output)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # 示例用法
        print("用法示例:")
        print("python report_generator.py data/c6b6bba0-48a8-4305-b016-c30aa329b174_personas.json data/c6b6bba0-48a8-4305-b016-c30aa329b174_simulations.json -o report.html")
        print("或者在Python中导入此模块并使用generate_report函数")