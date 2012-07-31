import os
import math
import datetime
from contextlib import contextmanager
import pymongo
import requests
from dateutil.parser import parse as parse_date

# Config
OPEN311_SERVER = 'http://ec2-50-112-207-34.us-west-2.compute.amazonaws.com/api'
OPEN311_API_KEY = '901f74a39dd67e27'
OPEN311_PAGE_SIZE = 1000
DB_HOST = 'localhost'
DB_PORT = 27017
DB_USER = None
DB_PASS = None
DB_NAME = 'SRTracker'

# Max number of SRs to return per request (per spec it's 50)
SR_INFO_CHUNK_SIZE = 50


@contextmanager
def db_connection():
   connection = pymongo.Connection(DB_HOST, DB_PORT)
   db = connection[DB_NAME]
   if (DB_USER):
      db.auth(DB_USER, DB_PASS)
      
   yield db
   
   connection.close()


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
   with db_connection() as db:
      srs = map(lambda sr: sr['srid'], db.Subscriptions.find())
      for sr in get_srs(srs):
         updated_date = parse_date(sr['updated_datetime'])
         updated_subscriptions = db.Subscriptions.find({'srid': sr['service_request_id'], 'date': {'$lt': updated_date}})
         for subscription in updated_subscriptions:
            if sr['status'] == 'closed':
               db.Subscriptions.remove({'_id': subscription['_id']})
            else:
               subscription['date'] = updated_date
               # TODO: this should be done after the query
               db.Subscriptions.save(subscription)
            updates.append((subscription, sr))
            
   return updates


def updated_srs_by_time():   
   updates = []
   with db_connection() as db:
      now = datetime.datetime.now()
      update_info = db.UpdateInfo.find_one()
      srs = get_updates(update_info['date'])
         
      # actually find the updated subscriptions
      latest_update = None
      for sr in srs:
         updated_subscriptions = db.Subscriptions.find({'srid': sr['service_request_id']})
         for subscription in updated_subscriptions:
            updates.append((subscription, sr))
            if sr['status'] == 'closed':
               db.Subscriptions.remove({'_id': subscription['_id']})
               
         sr_update_time = parse_date(sr['updated_datetime'])
         if latest_update == None or latest_update < sr_update_time:
            latest_update = sr_update_time
      
      # in case of systems that are slow to update or batch updates (e.g. nightly),
      # don't update the last update time unless we actually got some results
      # and set the last update time to the most recent SR we received
      if latest_update:
         db.UpdateInfo.update({'_id': update_info['_id']}, {'$set': {'date': latest_update}})
         
   return updates


def subscribe(request_id, notification_method):
   method, address = notification_method.split(':', 1)
   if method not in KNOWN_METHODS:
      return False
   
   with connect_db() as db:
      existing = db.Subscription.find_one({'srid': request_id, 'contact': notification_method})
      if not existing:
         subscription = {
            # could potentially use "[srid]|[contact]" for _id...
            'srid': request_id,
            'contact': notification_method,
            'date': datetime.datetime(1900, 1, 1)
         }
         db.Subscriptions.insert(subscription)


def initialize():
   with connect_db() as db:
      basic_info = db.UpdateInfo.find_one()
      if not basic_info:
         basic_info = {
            'date': datetime.datetime(1900, 1, 1)
         }
         db.UpdateInfo.insert(basic_info)


# if __name__ == "__main__":
   # updated_srs_by_time
   
   
    # app.config.from_object(__name__)
    # if 'DEBUG' in os.environ:
    #     app.debug = os.environ['DEBUG'] == 'True' and True or False
    # if 'OPEN311_SERVER' in os.environ:
    #     app.config['OPEN311_SERVER'] = os.environ['OPEN311_SERVER']
    # if 'OPEN311_API_KEY' in os.environ:
    #     app.config['OPEN311_API_KEY'] = os.environ['OPEN311_API_KEY']
    # 
    # app.config['PASSWORD_PROTECTED'] = 'PASSWORD_PROTECTED' in os.environ and (os.environ['PASSWORD_PROTECTED'] == 'True') or False
    # app.config['PASSWORD'] = 'PASSWORD' in os.environ and os.environ['PASSWORD'] or ''
    # 
    # port = int(os.environ.get('PORT', 5100))
    # app.run(host='0.0.0.0', port=port)
    