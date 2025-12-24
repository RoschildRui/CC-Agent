import json

INVITE_CODES_FILE = '../../data/inviteData/invite_codes.json'
# 邀请码相关函数
def load_invite_codes():
    try:
        with open(INVITE_CODES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_invite_codes(codes):
    with open(INVITE_CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=4)

def verify_and_use_invite_code(code):
    codes = load_invite_codes()
    if code not in codes:
        return False, "邀请码不存在"
    
    code_data = codes[code]
    if code_data['used_count'] >= code_data['use_times']:
        return False, "邀请码已达到使用次数上限"
    
    return True, "邀请码有效"

def increment_invite_code_usage(code):
    codes = load_invite_codes()
    if code in codes:
        codes[code]['used_count'] += 1
        save_invite_codes(codes)