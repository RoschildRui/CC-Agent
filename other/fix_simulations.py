import json
import os

def fix_simulation_ids(file_path):
    """修复模拟结果的ID编号，按顺序重新编号"""
    try:
        # 读取原始数据
        with open(file_path, 'r', encoding='utf-8') as f:
            simulations = json.load(f)
        
        # 计算每个persona应该有多少个模拟
        sims_per_persona = 10  # 假设每个persona有10个模拟
        total_personas = len(simulations) // sims_per_persona
        
        # 重新编号
        new_simulations = []
        for i, sim in enumerate(simulations):
            # 计算当前persona编号和simulation编号
            persona_num = (i // sims_per_persona) + 1  # 从1开始
            sim_num = (i % sims_per_persona) + 1      # 从1开始
            
            # 更新ID
            new_persona_id = f"persona_{persona_num}"
            new_sim_id = f"{new_persona_id}_sim_{sim_num}"
            
            sim['persona_id'] = new_persona_id
            sim['simulation_id'] = new_sim_id
            new_simulations.append(sim)
        
        # 备份原文件
        backup_path = file_path + '.backup'
        if os.path.exists(file_path):
            os.rename(file_path, backup_path)
        
        # 写入新文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_simulations, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully fixed {len(new_simulations)} simulation IDs")
        print(f"Total personas: {total_personas}")
        print(f"Simulations per persona: {sims_per_persona}")
        print(f"Original file backed up to: {backup_path}")
        
    except Exception as e:
        print(f"Error fixing simulation IDs: {str(e)}")
        # 如果出错，尝试恢复备份
        if os.path.exists(backup_path):
            os.rename(backup_path, file_path)
            print("Restored from backup due to error")

if __name__ == "__main__":
    # 获取当前目录下的所有文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    simulation_files = [f for f in os.listdir(current_dir) if f.endswith('_simulations.json')]
    
    if not simulation_files:
        print("No simulation files found in current directory")
    else:
        for file in simulation_files:
            print(f"Processing: {file}")
            fix_simulation_ids(os.path.join(current_dir, file)) 