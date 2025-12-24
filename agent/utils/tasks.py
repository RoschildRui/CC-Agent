import json
import os

def save_tasks(tasks=None, tasks_file=None):
    """
    将任务数据保存到文件
    tasks: 任务数据
    tasks_file(json): 任务数据文件路径
    """
    try:
        # 创建一个副本，移除不需要保存的数据
        tasks_to_save = {}
        for task_id, task in tasks.items():
            task_copy = task.copy()
            # 移除不需要保存的临时数据
            task_copy.pop('start_time', None)
            tasks_to_save[task_id] = task_copy
        
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
        print("任务数据保存成功")
    except Exception as e:
        print(f"保存任务数据时出错: {str(e)}")

def load_tasks(tasks_file=None):
    """
    从文件加载任务数据
    tasks_file(json): 任务数据文件路径
    """
    try:
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r', encoding='utf-8') as f:
                loaded_tasks = json.load(f)
                return loaded_tasks
        return {}
    except Exception as e:
        print(f"加载任务数据时出错: {str(e)}")
        return {}
    
# 在任务状态更新后保存任务数据
def update_task_status(task_id, status, progress=None, tasks=None, tasks_file=None):
    """
    更新任务状态并保存
    task_id: 任务ID
    status: 任务状态
    progress: 任务进度
    tasks: 任务数据
    tasks_file: 任务数据文件路径
    """
    if task_id in tasks:
        tasks[task_id]['status'] = status
        if progress is not None:
            tasks[task_id]['progress'] = progress
        save_tasks(tasks=tasks, tasks_file=tasks_file)

def stop_task(task_id, tasks=None, tasks_file=None, task_stop_flags=None):
    """
    中止指定的任务
    task_id: 任务ID
    tasks: 任务数据
    tasks_file: 任务数据文件路径
    task_stop_flags: 任务中止标志
    """
    if task_id in tasks:
        task_stop_flags[task_id] = True
        update_task_status(task_id, status='stopped', progress={
            'current_step': 'stopped',
            'completed': 0,
            'total': 100,
            'percentage': 0
        }, tasks=tasks, tasks_file=tasks_file)
        return True
    return False

