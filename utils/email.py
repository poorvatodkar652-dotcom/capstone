import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, subject, body_html):
    """
    Utility function to send emails automatically.
    Requires MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD in .env.
    """
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    mail_use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'

    if not all([mail_server, mail_port, mail_username, mail_password]):
        print(f"DEBUG: Missing SMTP credentials. Skip sending email to {to_email}.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = mail_username
        msg['To'] = to_email

        part = MIMEText(body_html, "html")
        msg.attach(part)

        port = int(mail_port)
        server = smtplib.SMTP(mail_server, port)
        if mail_use_tls:
            server.starttls()
            
        server.login(mail_username, mail_password)
        server.sendmail(mail_username, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False
