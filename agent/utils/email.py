from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_report_email(email, task_id, report_path):
    """发送报告邮件到用户邮箱"""
    try:
        # Email configuration from environment variables
        smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        sender_email = os.getenv("SENDER_EMAIL", "")
        password = os.getenv("SENDER_PASSWORD", "")

        # 创建邮件
        msg = MIMEMultipart()
        # 使用简单格式以符合QQ邮箱RFC要求
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = f"您的产品用户分析报告 - 任务 {task_id[:8]}"

        # 邮件正文
        body = f"""您好！

您的产品用户分析报告已生成完成。
任务ID: {task_id[:8]}

报告已作为附件发送，请查收。
如有任何问题，请随时联系我们。

产品设计不易，希望用户分析对您有所启发，祝好！
产品用户分析团队"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 添加报告附件
        try:
            with open(report_path, 'rb') as f:
                attachment = MIMEApplication(f.read())  # 使用MIMEApplication替代MIMEText
                
                # 修改文件名后缀，避免QQ邮箱的HTML安全提示
                original_filename = os.path.basename(report_path)
                if original_filename.lower().endswith('.html'):
                    # 将.html改为.html.
                    safe_filename = original_filename
                else:
                    safe_filename = original_filename
                
                attachment.add_header('Content-Disposition', f'attachment; filename="{safe_filename}"')
                msg.attach(attachment)
                print(f"添加附件成功: {safe_filename}")
        except Exception as e:
            print(f"添加附件时出错: {str(e)}，将发送不含附件的邮件")

        # 使用SSL连接发送邮件
        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                # 先测试连接
                server.ehlo()
                # 登录
                server.login(sender_email, password)
                # 发送
                server.sendmail(sender_email, [email], msg.as_string())
            print(f"邮件发送成功: {task_id}")
            return True
        except smtplib.SMTPException as e:
            print(f"SMTP错误: {str(e)}")
            return False
        except Exception as e:
            print(f"发送邮件时出错: {str(e)}")
            return False
            
    except Exception as e:
        print(f"准备邮件时出错: {str(e)}")
        return False
    
def send_payment_notification(task_id, amount, user_email):
    """发送付款通知邮件"""
    try:
        # Email configuration from environment variables
        smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        sender_email = os.getenv("SENDER_EMAIL", "")
        password = os.getenv("SENDER_PASSWORD", "")

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = sender_email  # Send to admin (same as sender)
        msg['Subject'] = f"新任务等待付款 - 任务ID: {task_id[:8]}"

        # 邮件正文
        body = f"""新任务等待付款：

任务ID: {task_id}
用户邮箱: {user_email}
金额: {amount}元

请查看后台管理页面处理此任务。
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 发送邮件
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, [msg['To']], msg.as_string())
        print(f"付款通知邮件发送成功: {task_id}")
        return True
    except Exception as e:
        print(f"发送付款通知邮件时出错: {str(e)}")
        return False
