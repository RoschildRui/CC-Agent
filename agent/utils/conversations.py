import os
import time
import json

def save_conversation(task_id, conversation, 
                      conversation_file=None):
    """
    保存对话历史到单独的文件
    task_id: 任务ID
    conversation: 对话历史
    conversation_file: 对话历史文件路径
    """
    try:
        conversation_file = os.path.join(conversation_file, f"{task_id}_conversation.json")
        conversation_data = {
            'conversation': conversation,
            'saved_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        print(f"对话历史保存成功: {task_id}")
    except Exception as e:
        print(f"保存对话历史时出错: {str(e)}")

def load_conversation(task_id, conversation_file=None):
    """
    加载指定任务的对话历史
    task_id: 任务ID
    conversation_file: 对话历史文件路径
    """
    try:
        conversation_file = os.path.join(conversation_file, f"{task_id}_conversation.json")
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"加载对话历史时出错: {str(e)}")
        return None

def rename_conversation_file(old_task_id, new_task_id, 
                             conversation_file=None):
    """
    重命名对话历史文件
    old_task_id: 旧任务ID
    new_task_id: 新任务ID
    conversation_file: 对话历史文件路径
    """
    try:
        old_file = os.path.join(conversation_file, f"{old_task_id}_conversation.json")
        new_file = os.path.join(conversation_file, f"{new_task_id}_conversation.json")
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
            print(f"对话历史文件重命名成功: {old_task_id} -> {new_task_id}")
            return True
    except Exception as e:
        print(f"重命名对话历史文件时出错: {str(e)}")
    return False

# 提取产品描述
def extract_product_description(conversation):
    for msg in reversed(conversation):
        if msg["role"] == "assistant" and "【产品描述】" in msg["content"]:
            description_text = msg["content"]
            start_index = description_text.find("【产品描述】")
            if start_index != -1:
                start_index += len("【产品描述】：")
                end_index = description_text.find("\n\n", start_index)
                if end_index == -1:
                    end_index = len(description_text)
                return description_text[start_index:end_index].strip()
    return ""