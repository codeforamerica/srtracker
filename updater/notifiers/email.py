# Copyright (C) 2012-2013, Code for America
# This is open source software, released under a standard 3-clause
# BSD-style license; see the file LICENSE for details.

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from dateutil.parser import parse as parse_date

SUBJECT_KEY = 'Subject:'

# Notifier interface
NOTIFICATION_METHOD = 'email'

# Notifier interface
def send_notifications(notifications, options):
    '''
    Sends notifications via SMTP e-mail.
    '''
    # get email server
    SMTPClass = options['EMAIL_SSL'] and smtplib.SMTP_SSL or smtplib.SMTP
    smtp = SMTPClass(options['EMAIL_HOST'], options['EMAIL_PORT'])
    
    # Don't try and log in without a username and password. 
    # Remove one of these from the config or make it the empty string to disable login.
    username = options.get('EMAIL_USER', None)
    password = options.get('EMAIL_PASS', None)
    if username and password:
        smtp.login(username, password)
    
    template_env = Environment(loader=FileSystemLoader(options['TEMPLATE_PATH']))
    
    # actually send emails
    for notification in notifications:
        send_email_notification(notification[1], notification[2], notification[3], smtp, options, template_env)

    smtp.quit()


def send_email_notification(address, subscription_key, sr, smtp, options, template_env):
    # parse dates in SR (in case the template wants to display them)
    # could potentially do this in the core updater instead of the mail plugin
    sr['requested_datetime'] = parse_date(sr['requested_datetime'])
    sr['updated_datetime'] = parse_date(sr['updated_datetime'])
    if 'notes' in sr:
        for note in sr['notes']:
            note['datetime'] = parse_date(note['datetime'])
    
    # basic stuff needed for sending and templates
    from_address = options.get('EMAIL_FROM', options.get('EMAIL_USER', ''))
    default_subject = 'Chicago 311: Your %s issue has been %s' % (sr['service_name'], sr['status'] == 'open' and 'updated.' or 'completed!')
    details_url = options['SR_DETAILS_URL'].format(sr_id=sr['service_request_id'])
    unsubscribe_url = options['SR_UNSUBSCRIBE_URL'].format(key=subscription_key)
    img_path = options['SR_TRACKER_IMG']
    
    # render message template
    html_template = template_env.get_template('email.html')
    text_template = template_env.get_template('email.txt')
    html_body = html_template.render(sr=sr, details_url=details_url, img=img_path, subject=default_subject, unsubscribe_url=unsubscribe_url)
    text_body = text_template.render(sr=sr, details_url=details_url, img=img_path, subject=default_subject, unsubscribe_url=unsubscribe_url)
    
    # get subject
    html_subject, html_body = subject_from_message(html_body)
    text_subject, text_body = subject_from_message(text_body)
    subject = html_subject or text_subject or default_subject
    
    # create the actual message
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = address
    message.attach(MIMEText(text_body, 'plain'))
    message.attach(MIMEText(html_body, 'html'))
    
    # and send!
    smtp.sendmail(from_address, [address], message.as_string())


def subject_from_message(text):
    '''
    If the is in the format: "Subject: [subject]\n\n[content]"
    then pull off the first two lines and return a tuple of subject and content.
    If not in the above format, return null for subject and the original string for content.
    '''
    parts = text.split('\n', 2)
    subject = None
    body = text
    if len(parts) > 2 and parts[0].startswith(SUBJECT_KEY) and parts[1] == '':
        subject = parts[0][len(SUBJECT_KEY):].strip()
        body = parts[2]
        
    return (subject, body)
