import os
import math
import datetime
from contextlib import contextmanager
import smtplib
from email.mime.text import MIMEText
import requests
import dateutil
from dateutil.parser import parse as parse_date
from db import DB
from models import Subscription, UpdateInfoItem

# Config
OPEN311_SERVER = 'http://localhost:5000/api'
OPEN311_API_KEY = ''
OPEN311_PAGE_SIZE = 1000
DB_STRING = 'postgresql://localhost:5432/srtracker'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 465
EMAIL_USER = 'test@example.com'
EMAIL_PASS = ''
EMAIL_FROM = 'test@example.com'
EMAIL_SSL = True

# Max number of SRs to return per request (per spec it's 50)
SR_INFO_CHUNK_SIZE = 50
# Supported notification methods
KNOWN_METHODS = ('email')

db = DB(DB_STRING)


# FIXME: start using this
utczone = dateutil.tz.tzutc()
def parse_date_utc(date_string):
    '''Returns a naive date in UTC representing the passed-in date string.'''
    parsed = parse_date(date_string)
    if parsed.tzinfo:
        parsed = parsed.astimezone(utczone).replace(tzinfo=None)


def get_srs(sr_list):
   url = '%s/requests.json' % OPEN311_SERVER
   num_requests = int(math.ceil(len(sr_list) / float(SR_INFO_CHUNK_SIZE)))
   results = []
   for chunk in range(num_requests):
      srs = sr_list[SR_INFO_CHUNK_SIZE * chunk : SR_INFO_CHUNK_SIZE * (chunk + 1)]
      params = {'service_request_id': ','.join(srs)}
      if OPEN311_API_KEY:
         params['api_key'] = OPEN311_API_KEY
      request = requests.get(url, params=params)
      if request.status_code == requests.codes.ok:
         results.extend(request.json)
      else:
         # TODO: raise exception?
         break
   return results


def get_updates(since):
   url = '%s/requests.json' % OPEN311_SERVER
   params = {
      'start_updated_date': since.isoformat(),
      'page_size': OPEN311_PAGE_SIZE,
   }
   if OPEN311_API_KEY:
      params['api_key'] = OPEN311_API_KEY
   # paging starts at 1 (not 0)
   page = 1
   results = []
   while page:
      params['page'] = page
      request = requests.get(url, params=params)
      if request.status_code == requests.codes.ok:
         result = request.json
         results.extend(result)
         page = len(result) > 0 and page + 1 or 0
      else:
         # TODO: raise exception?
         break
   
   return results


def updated_srs_by_subscription():   
    updates = []
    with db() as session:
        srs = [item[0] for item in session.query(distinct(Subscription.sr_id)).all()]
        for sr in get_srs(srs):
            updated_date = parse_date(sr['updated_datetime'])
            updated_subscriptions = session.query(Subscriptions).\
                filter(Subscription.sr_id == sr['service_request_id']).\
                filter(Subscription.updated < updated_date)
            for subscription in updated_subscriptions:
                updates.append((subscription.contact, sr))
                if sr['status'] == 'closed':
                    # Remove subscriptions for SRs that have been completed
                    session.delete(subscription)
                else:
                    subscription.updated = updated_date
                    
    return updates


def updated_srs_by_time():
    updates = []
    with db() as session:
        now = datetime.datetime.now()
        last_update_info = session.query(UpdateInfoItem).filter(UpdateInfoItem.key == 'date').first()
        # add 1 second to the time so we don't grab the latest previous result even if it wasn't updated
        last_update_date = parse_date(last_update_info.value) + datetime.timedelta(seconds=1)
        srs = get_updates(last_update_date)
        
        # actually find the updated subscriptions
        latest_update = None
        for sr in srs:
            updated_subscriptions = session.query(Subscription).filter(Subscription.sr_id == sr['service_request_id'])
            for subscription in updated_subscriptions:
                updates.append((subscription.contact, sr))
                if sr['status'] == 'closed':
                    session.delete(subscription)
            
            # track the latest update time so we know when to start from next time we poll
            sr_update_time = parse_date(sr['updated_datetime'])
            if latest_update == None or latest_update < sr_update_time:
                latest_update = sr_update_time
        
        # in case of systems that are slow to update or batch updates (e.g. nightly),
        # don't update the last update time unless we actually got some results
        # and set the last update time to the most recent SR we received
        if latest_update:
            last_update_info.value = latest_update.isoformat()
    
    return updates


def send_notification(contact, sr):
    method, address = contact.split(':', 1)
    # this should have some more dynamic method of loading 
    # the function associated with a particular method
    if method == 'email':
        send_email_notification(address, sr)


def send_email_notification(address, sr):
    SMTPClass = EMAIL_SSL and smtplib.SMTP_SSL or smtplib.SMTP
    smtp = SMTPClass(EMAIL_HOST, EMAIL_PORT)
    smtp.login(EMAIL_USER, EMAIL_PASS)
    
    subject = 'Chicago 311: Your %s issue has been updated.' % sr['service_name']
    message = MIMEText('''Service Request %s (%s) has been updated. Here's the deets: (not)''' % (sr['service_request_id'], sr['service_name']))
    message['Subject'] = subject
    message['From'] = EMAIL_FROM
    message['To'] = address
    
    smtp.sendmail(EMAIL_FROM, [address], message.as_string())
    smtp.quit()


def poll_and_notify():
    notifications = updated_srs_by_time()
    # FIXME: This should be threads, subprocesses, eventlets or something more concurrent
    for notification in notifications:
        send_notification(*notification)


def subscribe(request_id, notification_method):
    method, address = notification_method.split(':', 1)
    if method not in KNOWN_METHODS:
        return False
    
    with db() as session:
        # FIXME: this check should really just be at the DB level to prevent race conditions
        existing = session.query(Subscription).\
            filter(Subscription.sr_id == request_id).\
            filter(Subscription.contact == notification_method).\
            first()
        if not existing:
            session.add(Subscription(
                sr_id=request_id,
                contact=notification_method,
                updated=datetime.datetime(1900, 1, 1)))


def initialize():
    with db() as session:
        # Ensure we have a last updated date
        last_update_info = session.query(UpdateInfoItem).filter(UpdateInfoItem.key == 'date').first()
        if not last_update_info:
            # default to 12am this morning for endpoints that update daily
            start_date = datetime.datetime.combine(datetime.date.today(), datetime.time())
            session.add(UpdateInfoItem(key='date', value=start_date))


if __name__ == "__main__":
    initialize()
    poll_and_notify()
    