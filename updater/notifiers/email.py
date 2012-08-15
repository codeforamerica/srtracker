import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

# Notifier interface
NOTIFICATION_METHOD = 'email'

# Notifier interface
def send_notifications(notifications, options):
    '''
    Sends notifications via SMTP e-mail.
    '''
    # get email server
    SMTPClass = options.EMAIL_SSL and smtplib.SMTP_SSL or smtplib.SMTP
    smtp = SMTPClass(options.EMAIL_HOST, options.EMAIL_PORT)
    smtp.login(options.EMAIL_USER, options.EMAIL_PASS)
    
    template_env = Environment(loader=FileSystemLoader(options.TEMPLATE_PATH))
    
    # actually send emails
    for notification in notifications:
        send_email_notification(notification[1], notification[2], smtp, options, template_env)

    smtp.quit()


def send_email_notification(address, sr, smtp, options, template_env):
    from_address = options.EMAIL_FROM or options.EMAIL_USER
    details_url = options.SR_DETAILS_URL.format(sr_id=sr['service_request_id'])
    img_path = options.SR_TRACKER_IMG
    
    subject = 'Chicago 311: Your %s issue has been updated.' % sr['service_name']
    
    html_template = template_env.get_template('email.html')
    html_body = html_template.render(sr=sr, details_url=details_url, img=img_path)
    text_template = template_env.get_template('email.txt')
    text_body = text_template.render(sr=sr, details_url=details_url, img=img_path)
    
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = address
    message.attach(MIMEText(text_body, 'plain'))
    message.attach(MIMEText(html_body, 'html'))

    smtp.sendmail(from_address, [address], message.as_string())
    