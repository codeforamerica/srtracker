# -*- coding: utf-8 -*-

import os
import datetime
import re
from flask import Flask, render_template, request, abort, redirect, url_for, make_response, session, flash
import requests
import iso8601
import pytz
import updater

# Config
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'configuration.py')
DEBUG = True
OPEN311_SERVER = 'http://localhost:5000'
OPEN311_API_KEY = ''
PASSWORD_PROTECTED = False
SECRET_KEY = 'please_please_change_this!'

app = Flask(__name__)

@app.before_request
def password_protect():
    # don't password-protect images (for e-mail!)
    if app.config['PASSWORD_PROTECTED'] and not request.path.startswith('/static/img'):
        auth = request.authorization
        if not auth or auth.password != app.config['PASSWORD']:
            # Tell the browser to do basic auth
            return make_response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})


#--------------------------------------------------------------------------
# ROUTES
#--------------------------------------------------------------------------

@app.route("/")
def index():
    url = '%s/requests.json' % app.config['OPEN311_SERVER']
    params = {'extensions': 'true', 'legacy': 'false'}
    if app.config['OPEN311_API_KEY']:
        params['api_key'] = app.config['OPEN311_API_KEY']
    r = requests.get(url, params=params)
    if r.status_code != 200:
        app.logger.error('OPEN311: Failed to load recent requests from Open311 server. Status Code: %s, Response: %s', r.status_code, r.text)
        service_requests = None
    else:
        service_requests = r.json
    
    return render_template('index.html', service_requests=service_requests)


@app.route("/requests/")
def request_search():
    if 'request_id' in request.args:
        return redirect(url_for('show_request', request_id=request.args['request_id']))
    else:
        abort(404)


@app.route("/requests/<request_id>", methods=["GET", "POST"])
def show_request(request_id):
    request_id = request_id.lstrip('#')
    
    # receive subscription
    form_errors = []
    submitted_email = None
    if request.method == 'POST':
        submitted_email = request.form.get('update_email')
        if submitted_email:
            success = subscribe_to_sr(request_id, submitted_email)
            if not success:
                form_errors.append('Please use a valid e-mail address.')
    
    # TODO: Should probably use Three or something nice for this...
    url = '%s/requests/%s.json' % (app.config['OPEN311_SERVER'], request_id)
    params = {'extensions': 'true', 'legacy': 'false'}
    if app.config['OPEN311_API_KEY']:
        params['api_key'] = app.config['OPEN311_API_KEY']
    r = requests.get(url, params=params)
    if r.status_code == 404:
        # TODO: how to generalize this?
        # Chicago's SR IDs are always \d\d-\d{8}, if we get just digits, reformat and try again
        request_id_digits = re.sub(r'\D', '', request_id)
        if len(request_id_digits) == 8:
            # Try prepending the year if it's only 8 digits
            request_id_digits = datetime.date.today().strftime('%y') + request_id_digits
        if len(request_id_digits) == 10:
            reformatted = '%s-%s' % (request_id_digits[:2], request_id_digits[2:])
            if reformatted != request_id:
                return redirect(url_for('show_request', request_id=reformatted))
        
        # It would be nice to log this for analytical purposes (what requests are being checked that we can't show?)
        # but that would be better done through GA or KISS Metrics than through server logging
        # TODO: need a template
        return render_template('error_no_sr.html', request_id=request_id), 404
        
    elif r.status_code != 200:
        # TODO: need a template
        app.logger.error('OPEN311: Error (not 404) loading data for SR %s', request_id)
        return render_template('error_311_api.html', request_id=request_id), 500
        
    srs = r.json
    if srs:
        sr = fixup_sr(srs[0], request_id)
        
        if 'requested_datetime' in sr:
            sr['requested_datetime'] = iso8601.parse_date(sr['requested_datetime'])
        
        # sometimes an SR doesn't include notes even though there should always be an "opened" note
        if 'notes' not in sr:
            sr['notes'] = []
        
        relevant_notes = 0
        for note in sr['notes']:
            note['datetime'] = iso8601.parse_date(note['datetime'])
            if note['type'] in ('follow_on', 'follow_on_created', 'activity', 'closed'):
                relevant_notes += 1
        
        # add follow-on closure data, fix types, etc, etc
        by_id = {}
        for note in sr['notes']:
            if note['type'] in ('follow_on', 'follow_on_created', 'follow_on_closed'):
                note_sr_id = note['extended_attributes']['service_request_id']
                
                # old-style is just "follow_on" for everything related to follow-ons
                # new-style is "follow_on_created" and "follow_on_closed"
                # update old notes so templates don't get crazy complicated :(
                if note['type'] == 'follow_on_created' or note['description'].endswith('Created'):
                    note['type'] = 'follow_on_created'
                    by_id[note_sr_id] = note
                    
                elif note['type'] == 'follow_on_closed' or note['description'].endswith('Closed'):
                    note['type'] = 'follow_on_closed'
                    if note_sr_id in by_id:
                        original = by_id[note_sr_id]
                        original['extended_attributes']['closed_datetime'] = note['datetime']
        
        # if there's no activity yet, show 'under review'
        if relevant_notes == 0:
            sr['notes'].append({
                'type': 'activity',
                'summary': 'Under review by %s staff' % sr.get('agency_responsible', '')
            })
        
        subscribed = False
        if sr['status'] == 'open' and session.get('addr', None):
            # TODO: when subscription service supports more than e-mail, 
            # we should probably be able to show all your subscriptions here
            subscribed = updater.subscription_exists(request_id, 'email', session.get('addr', ''))
            
        # test media
        # sr['media_url'] = sr['media_url'] or 'http://farm5.staticflickr.com/4068/4286605571_c1a1751fdc_n.jpg'
        
        body = render_template('service_request.html', sr=sr, subscribed=subscribed, errors=form_errors, submitted_email=submitted_email)
        return (body, 200, None)
    
    else:
        return render_template('error_no_sr.html', request_id=request_id), 404


@app.route("/subscribe/<request_id>", methods=["POST"])
def subscribe(request_id):
    email = request.form.get('update_email')
    if email:
        success = subscribe_to_sr(request_id, email)
        if not success:
            flash('Please use a valid e-mail address.', 'error')
    return redirect(url_for('show_request', request_id=request_id))


@app.route("/unsubscribe/<subscription_key>", methods=["GET", "POST"])
def unsubscribe(subscription_key):
    subscription = updater.subscription_for_key(subscription_key)
    if subscription:
        sr_id = subscription.sr_id
        updater.unsubscribe_with_key(subscription_key)
        destination = url_for('show_request', request_id=sr_id)
    else:
        destination = url_for('index')
        
    flash(u'You‘ve been unsubscribed from this service request. You will no longer receive e-mails when it is updated.')
    return redirect(destination)


#--------------------------------------------------------------------------
# ERRORS
#--------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error_404.html'), 404


@app.errorhandler(500)
def generic_error(error):
    return render_template('error_generic.html'), 500


#--------------------------------------------------------------------------
# FILTERS
#--------------------------------------------------------------------------

# Friendly time by Sean Vieira (http://flask.pocoo.org/snippets/33/)
@app.template_filter()
def friendly_time(dt, past_="ago", future_="from now", default="just now"):
    """
    Returns string representing "time since"
    or "time until" e.g.
    3 days ago, 5 hours from now etc.
    """
    
    if dt == None:
        return ''

    if isinstance(dt, basestring):
        dt = iso8601.parse_date(dt)
        # ensure the date is naive for comparison to utcnow
        if dt.tzinfo:
            dt = dt.astimezone(pytz.utc).replace(tzinfo=None)

    now = datetime.datetime.utcnow()
    if now > dt:
        diff = now - dt
        dt_is_past = True
    else:
        diff = dt - now
        dt_is_past = False

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:

        if period:
            return "%d %s %s" % (period, \
                singular if period == 1 else plural, \
                past_ if dt_is_past else future_)

    return default


#--------------------------------------------------------------------------
# UTILITIES
#--------------------------------------------------------------------------

def fixup_sr(sr, request_id=None):
    '''
    Fix up an SR to try and ensure some basic info.
    (In Chicago's API, any field can be missing, even if it's required.)
    '''
    
    if 'service_request_id' not in sr:
        sr['service_request_id'] = request_id or sr.get('token', 'UNKNOWN')
        
    if 'status' not in sr:
        sr['status'] = 'open'
        
    if 'service_name' not in sr:
        sr['service_name'] = 'Miscellaneous Services'
        
    return sr


def subscribe_to_sr(request_id, email):
    # validate e-mail
    match = re.match(r'[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,4}$', email, re.IGNORECASE)
    if match:
        key = updater.subscribe(request_id, 'email', email)
        if key:
            # TODO: should we use the subscription key instead?
            session['addr'] = email
            session.permanent = True
            return True
        else:
            app.logger.error('Error creating a subscription for %s on %s', email, request_id)
        
    return False


#--------------------------------------------------------------------------
# INIT
#--------------------------------------------------------------------------

def bool_from_string(value):
    return value in (True, 'True', 'true', 'T', 't', '1')

def bool_from_env(envvar, default=False):
    return bool_from_string(os.environ.get(envvar, default))

if __name__ == "__main__":
    app.config.from_object(__name__)
    # we want to support a nice fallback, so use from_pyfile directly instead of from_envvar
    config_path = os.environ.get('SRTRACKER_CONFIGURATION', DEFAULT_CONFIG_PATH)
    if os.path.isfile(config_path):
        app.config.from_pyfile(config_path)
    else:
        app.debug = bool_from_env('DEBUG', app.debug)
        app.secret_key = os.environ.get('SECRET_KEY', app.secret_key)
        app.config['OPEN311_SERVER'] = os.environ.get('OPEN311_SERVER', OPEN311_SERVER)
        app.config['OPEN311_API_KEY'] = os.environ.get('OPEN311_API_KEY', OPEN311_API_KEY)
        app.config['PASSWORD_PROTECTED'] = bool_from_env('PASSWORD_PROTECTED', PASSWORD_PROTECTED)
        app.config['PASSWORD'] = os.environ.get('PASSWORD', '')
    
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port)
    