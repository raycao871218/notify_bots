#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv
from datetime import datetime
import glob
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

class EmailNotifier:
    def __init__(self, smtp_server, smtp_port, username, password, sender, receivers):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.receivers = receivers.split(',') if isinstance(receivers, str) else receivers

    def _create_smtp_connection(self):
        """
        创建SMTP连接
        :return: (server, error_msg)
        """
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.ehlo()
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
            server.login(self.username, self.password)
            return server, None
        except smtplib.SMTPAuthenticationError:
            return None, "认证失败，请检查用户名和密码"
        except smtplib.SMTPException as e:
            return None, f"SMTP错误：{str(e)}"
        except Exception as e:
            return None, f"连接错误：{str(e)}"

    def send_message(self, subject, message, content_type="html"):
        """
        发送邮件
        :param subject: 邮件主题
        :param message: 邮件内容
        :param content_type: 内容类型（html或plain）
        :return: 是否发送成功
        """
        # 创建SMTP连接
        server, error_msg = self._create_smtp_connection()
        if not server:
            print(f"错误：无法连接到SMTP服务器")
            print(f"原因：{error_msg}")
            return False

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = f"{Header('Log Notifier', 'utf-8')} <{self.sender}>"
            msg['To'] = ','.join(self.receivers)
            msg['Subject'] = Header(subject, 'utf-8')

            # 添加邮件内容
            msg.attach(MIMEText(message, content_type, 'utf-8'))

            # 发送邮件
            server.send_message(msg)
            print("✓ SMTP服务器连接成功！")
            print(f"✓ 邮件服务器: {self.smtp_server}")
            print("✓ 邮件发送成功！")
            return True

        except Exception as e:
            print(f"发送邮件时出错：{str(e)}")
            return False
        finally:
            try:
                server.quit()
            except Exception:
                pass

def load_env_config():
    """
    从环境变量加载邮件配置
    :return: (smtp_server, smtp_port, username, password, sender, receivers, log_dir)
    """
    # 加载.env文件
    load_dotenv()
    
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    sender = os.getenv('EMAIL_SENDER')
    receivers = os.getenv('EMAIL_RECEIVERS')
    log_dir = os.getenv('LOG_DIR', '/var/log')
    
    if not all([smtp_server, username, password, sender, receivers]):
        print("错误：环境变量中缺少必要的配置项")
        print("请确保在.env文件中设置了以下变量：")
        print("- SMTP_SERVER")
        print("- SMTP_PORT (可选，默认587)")
        print("- SMTP_USERNAME")
        print("- SMTP_PASSWORD")
        print("- EMAIL_SENDER")
        print("- EMAIL_RECEIVERS")
        print("- LOG_DIR (可选，默认为/var/log)")
        sys.exit(1)
        
    return smtp_server, smtp_port, username, password, sender, receivers, log_dir

def find_log_file(log_dir, date_str=None):
    """
    根据日期查找日志文件
    :param log_dir: 日志目录
    :param date_str: 日期字符串 (YYYY-MM-DD)
    :return: 日志文件路径列表
    """
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            search_pattern = os.path.join(log_dir, f"*{date_str}*.log")
        except ValueError:
            print(f"错误：日期格式不正确，应为YYYY-MM-DD，例如：2024-03-20")
            sys.exit(1)
    else:
        # 如果没有指定日期，使用今天的日期
        date_str = datetime.now().strftime('%Y-%m-%d')
        search_pattern = os.path.join(log_dir, f"*{date_str}*.log")

    print(f"正在搜索日志文件...")
    print(f"日志目录: {log_dir}")
    print(f"搜索模式: {search_pattern}")
    
    # 检查目录是否存在
    if not os.path.exists(log_dir):
        print(f"错误：日志目录 {log_dir} 不存在！")
        sys.exit(1)
        
    # 列出目录中的所有文件
    print("\n目录中的文件：")
    for file in os.listdir(log_dir):
        print(f"- {file}")

    log_files = glob.glob(search_pattern)
    if not log_files:
        print(f"\n未找到{date_str}的日志文件")
        print("请确认：")
        print(f"1. 日志文件名中包含日期 {date_str}")
        print(f"2. 日志文件扩展名为 .log")
        print(f"3. 您有权限访问该目录和文件")
        sys.exit(1)
    
    return log_files

def read_log_content(log_files):
    """
    读取日志文件内容
    :param log_files: 日志文件路径列表
    :return: 日志内容
    """
    content = []
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content.append(f"<h3>{os.path.basename(log_file)}</h3>")
                content.append("<pre>")
                content.append(f.read().strip())
                content.append("</pre>")
        except Exception as e:
            print(f"读取日志文件 {log_file} 时出错：{str(e)}")
            continue
    
    return "\n".join(content) if content else "日志内容为空"

def main():
    # 检查命令行参数
    if len(sys.argv) < 2:
        print(f"使用方法: {sys.argv[0]} <消息内容>")
        print(f"或者: {sys.argv[0]} --log [YYYY-MM-DD]")
        sys.exit(1)
    
    # 加载配置
    smtp_server, smtp_port, username, password, sender, receivers, log_dir = load_env_config()
    
    # 创建通知器实例
    notifier = EmailNotifier(smtp_server, smtp_port, username, password, sender, receivers)
    
    # 处理参数
    if sys.argv[1] == '--log':
        # 日志模式
        date_str = sys.argv[2] if len(sys.argv) > 2 else None
        log_files = find_log_file(log_dir, date_str)
        message = read_log_content(log_files)
        subject = f"日志通知 - {date_str if date_str else datetime.now().strftime('%Y-%m-%d')}"
    else:
        # 普通消息模式
        message = " ".join(sys.argv[1:])
        subject = "系统通知"
    
    # 发送消息
    notifier.send_message(subject, message)

if __name__ == "__main__":
    main() 