import smtplib
from email.mime.text import MIMEText

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
    
    # actually send emails
    for notification in notifications:
        send_email_notification(notification[1], notification[2], smtp, options)

    smtp.quit()


def send_email_notification(address, sr, smtp, options):
    from_address = options.EMAIL_FROM or options.EMAIL_USER
    details_url = options.SR_DETAILS_URL.format(sr_id=sr['service_request_id'])
    subject = 'Chicago 311: Your %s issue has been updated.' % sr['service_name']
    body = ''
    if sr['status'] == 'open':
        body = '''Service Request #%s (%s) has been updated. You can see more information about at:\n\n    %s''' % (sr['service_request_id'], sr['service_name'], details_url)
    else:
        body = '''Service Request #%s (%s) has been completed! You can see more about it at:\n\n    %s''' % (sr['service_request_id'], sr['service_name'], details_url)

    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = address

    smtp.sendmail(from_address, [address], message.as_string())
    