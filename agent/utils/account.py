import json
from datetime import datetime

VIP_USERS_FILE = '../../data/accountData/vip_users.json'

# 加载VIP用户信息
def load_vip_users():
    try:
        with open('vip_users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def is_vip_user(email):
    vip_users = load_vip_users()
    if email in vip_users:
        user_info = vip_users[email]
        # 检查会员是否过期
        end_date = datetime.strptime(user_info['end_date'], '%Y-%m-%d')
        if end_date > datetime.now() and user_info['status'] == 'active':
            return True, user_info
    return False, None