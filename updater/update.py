#!/usr/bin/env python
import os
import math
import datetime
import smtplib
from email.mime.text import MIMEText
from threading import Thread
from optparse import OptionParser
import logging
from collections import defaultdict
import imp
import requests
import dateutil
from dateutil.parser import parse as parse_date
from db import DB
from models import Subscription, UpdateInfoItem, Base

# Config
config_file = os.environ.get('UPDATER_CONFIGURATION', 'configuration')
config = __import__(config_file, globals(), locals(), [], -1)

# Max number of SRs to return per request (per spec it's 50)
SR_INFO_CHUNK_SIZE = 50

# Where to get notification plugins
NOTIFIERS_DIR = 'NOTIFIERS_DIR' in dir(config) and config.NOTIFIERS_DIR or os.path.abspath('notifiers')

db = DB(config.DB_STRING)
logging.basicConfig()
logger = logging.getLogger(__name__)


# FIXME: start using this
utczone = dateutil.tz.tzutc()
def parse_date_utc(date_string):
    '''Returns a naive date in UTC representing the passed-in date string.'''
    parsed = parse_date(date_string)
    if parsed.tzinfo:
        parsed = parsed.astimezone(utczone).replace(tzinfo=None)


def get_updates(since):
   url = '%s/requests.json' % config.OPEN311_SERVER
   params = {
      'start_updated_date': since.isoformat(),
      'page_size': config.OPEN311_PAGE_SIZE,
   }
   if config.OPEN311_API_KEY:
      params['api_key'] = config.OPEN311_API_KEY
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


def updated_srs_by_time():
    updates = []
    with db() as session:
        last_update_info = session.query(UpdateInfoItem).filter(UpdateInfoItem.key == 'date').first()
        # Bail out if we don't actually have any subscriptions
        if not session.query(Subscription).first():
            # but first we should clear out the last updated time
            if last_update_info:
                session.delete(last_update_info)
            # TODO: should we raise an exception here instead?
            return updates
        
        # add 1 second to the time so we don't grab the latest previous result even if it wasn't updated
        last_update_date = parse_date(last_update_info.value) + datetime.timedelta(seconds=1)
        srs = get_updates(last_update_date)
        
        # actually find the updated subscriptions
        latest_update = None
        for sr in srs:
            updated_subscriptions = session.query(Subscription).filter(Subscription.sr_id == sr['service_request_id'])
            for subscription in updated_subscriptions:
                updates.append((subscription.method, subscription.contact, sr))
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


def send_notifications(notifications):
    # split up notifications by method
    by_method = defaultdict(list)
    for notification in notifications:
        by_method[notification[0]].append(notification)
    
    notifiers = get_notifiers()
    for method, notes in by_method.iteritems():
        if method in notifiers:
            for notifier in notifiers[method]:
                logger.debug('Sending %d notifications via %s', len(notes), notifier.__name__)
                notifier.send_notifications(notes, config)
        else:
            logger.error('No notifier for "%s" - skipping %d notifications', method, len(notes))


def poll_and_notify():
    logger.debug('Getting updates from Open311...')
    notifications = updated_srs_by_time()
    
    logger.debug('Sending %d notifications...', len(notifications))
    # Need to unhardcode "email" updates so we can support things like SMS, Twitter, etc.
    # Should break up the list by update method and have a thread pool for each
    if config.THREADED_UPDATES:
        notification_count = len(notifications)
        max_threads = config.EMAIL_MAX_THREADS
        per_thread = int(math.ceil(float(notification_count) / max_threads))
        threads = []
        # Create threads
        for i in range(max_threads):
            thread_notifications = notifications[i * per_thread:(i + 1) * per_thread]
            if len(thread_notifications):
                thread = Thread(target=send_notifications, args=(thread_notifications,))
                thread.start()
                threads.append(thread)
        # Wait for threads to finish
        for thread in threads:
            thread.join()
    else:
        send_notifications(notifications)


def get_notifiers():
    notifiers = defaultdict(list) # organized by type
    for file_name in os.listdir(NOTIFIERS_DIR):
        module_name, ext = os.path.splitext(file_name)
        if ext == '.py' or os.path.isdir(os.path.join(NOTIFIERS_DIR, file_name)):
            # Warning: this will raise ImportError if the file isn't importable (that's a good thing)
            module_info = imp.find_module(module_name, [NOTIFIERS_DIR])
            module = None
            try:
                module = imp.load_module(module_name, *module_info)
            finally:
                # find_module opens the module's file, so be sure to close it here (!)
                if module_info[0]:
                    module_info[0].close()
            if module:
                logger.debug('Loading notifier: "%s"' % module.__name__)
                method = 'NOTIFICATION_METHOD' in dir(module) and module.NOTIFICATION_METHOD or module_name
                if 'send_notifications' not in dir(module):
                    logger.warning('Notifier "%s" not loaded - Notifiers must implement the function send_notifications(notifications, options)' % module_name)
                else:
                    notifiers[method].append(module)
                    
    return notifiers


def subscribe(request_id, method, address):
    '''Create a new subscription the request identified by request_id.
    @param request_id: The request to subscribe to
    @param method:     The type of subscription (e.g. 'email' or 'sms')
    @param address:    The adress to send updates to (e.g. 'someone@example.com' or '63055512345')
    '''
    
    # TODO: validate the subscription by seeing if the request_id exists via Open311?
    with db() as session:
        if not subscription_exists(request_id, method, address):
            session.add(Subscription(
                sr_id=request_id,
                method=method,
                contact=address))
        
            # If we haven't ever updated, set the last update date
            last_update_info = session.query(UpdateInfoItem).filter(UpdateInfoItem.key == 'date').first()
            if not last_update_info:
                # TODO: get the SR's updated_datetime and use that
                session.add(UpdateInfoItem(key='date', value=datetime.datetime.now()))


def subscription_exists(request_id, method, address):
    '''Check whether a subscription already exists for the given request id with the specified method and address.
    @param request_id: The request to subscribe to
    @param method:     The type of subscription (e.g. 'email' or 'sms')
    @param address:    The adress to send updates to (e.g. 'someone@example.com' or '63055512345')
    '''
    
    with db() as session:
        existing = session.query(Subscription).\
            filter(Subscription.sr_id == request_id).\
            filter(Subscription.method == method).\
            filter(Subscription.contact == address).\
            first()
        return existing != None


def initialize():
    with db() as session:
        # Ensure we have a last updated date
        last_update_info = session.query(UpdateInfoItem).filter(UpdateInfoItem.key == 'date').first()
        a_subscription = session.query(Subscription).first()
        if a_subscription and not last_update_info:
            # this is an invalid state! Could raise an error, but just attempt to repair for now
            # default to 12am this morning for endpoints that update daily
            start_date = datetime.datetime.combine(datetime.date.today(), datetime.time())
            session.add(UpdateInfoItem(key='date', value=start_date))
            logger.warning('Found a subscription but no last updated time.\nSetting last update to %s', start_date)


def initialize_db():
    with db() as session:
        db.create(Base)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-i", "--initialize", dest="initialize_db", action="store_true", help="Initialize the database.")
    # parser.add_option("-d", "--date", dest="start_date", help="Start datetime in the format 'YYYY-MM-DDTHH:MM:SS'", default=None)
    (options, args) = parser.parse_args()
    
    if options.initialize_db:
        initialize_db()
    else:
        initialize()
        poll_and_notify()
    