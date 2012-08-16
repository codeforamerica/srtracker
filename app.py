import os
import datetime
from flask import Flask, render_template, request, abort, redirect, url_for, make_response, session
import requests
import iso8601
import pytz
import updater

# Config
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


@app.route("/requests")
def redirect_request():
    if 'request_id' in request.args:
        return redirect(url_for('show_request', request_id=request.args['request_id']))
    else:
        abort(404)


@app.route("/requests/<request_id>")
def show_request(request_id):
    request_id = request_id.lstrip('#')
    
    # TODO: Should probably use Three or something nice for this...
    url = '%s/requests/%s.json' % (app.config['OPEN311_SERVER'], request_id)
    params = {'extensions': 'true', 'legacy': 'false'}
    if app.config['OPEN311_API_KEY']:
        params['api_key'] = app.config['OPEN311_API_KEY']
    r = requests.get(url, params=params)
    if r.status_code == 404:
        # It would be nice to log this for analytical purposes (what requests are being checked that we can't show?)
        # but that would be better done through GA or KISS Metrics than through server logging
        # TODO: need a template
        return render_template('no_service_request_found.html', rid=request_id)
        
    elif r.status_code != 200:
        # TODO: need a template
        app.logger.error('OPEN311: Error (not 404) loading data for SR %s', request_id)
        return ("There was an error getting data about service request #%s" % request_id, 404, None)
        
    srs = r.json
    if srs:
        sr = srs[0]
        sr['requested_datetime'] = iso8601.parse_date(sr['requested_datetime'])
        for note in sr['notes']:
            note['datetime'] = iso8601.parse_date(note['datetime'])
        
        # add follow-on closure data
        by_id = {}
        for note in sr['notes']:
            if note['type'] == 'follow_on':
                note_sr_id = note['extended_attributes']['service_request_id']
                if note_sr_id in by_id:
                    if note['description'].endswith('Closed'):
                        original = by_id[note_sr_id]
                        original['extended_attributes']['closed_datetime'] = note['datetime']
                else:
                    by_id[note_sr_id] = note
        
        sr['notes'].reverse()
        
        subscribed = False
        if sr['status'] == 'open' and session.get('email', None):
            # TODO: when subscription service supports more than e-mail, 
            # we should probably be able to show all your subscriptions here
            subscribed = updater.subscription_exists(request_id, 'email', session.get('email', ''))
        
        body = render_template('service_request.html', sr=sr, subscribed=subscribed)
        return (body, 200, None)
    
    else:
        return render_template('no_service_request_found.html', rid=request_id)


@app.route("/subscribe/<request_id>", methods=["POST"])
def subscribe(request_id):
    email = request.form.get('update_email')
    # TODO: validate email
    if email:
        updater.subscribe(request_id, 'email', email)
        # TODO: should we get back a secret subscription key and use that instead?
        session['email'] = email
    return redirect(url_for('show_request', request_id=request_id))


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
# INIT
#--------------------------------------------------------------------------

if __name__ == "__main__":
    app.config.from_object(__name__)
    app.debug = os.environ.get('DEBUG', str(app.debug)) == 'True'
    app.secret_key = os.environ.get('SECRET_KEY', app.secret_key)
    app.config['OPEN311_SERVER'] = os.environ.get('OPEN311_SERVER', OPEN311_SERVER)
    app.config['OPEN311_API_KEY'] = os.environ.get('OPEN311_API_KEY', OPEN311_API_KEY)
    app.config['PASSWORD_PROTECTED'] = os.environ.get('PASSWORD_PROTECTED', str(PASSWORD_PROTECTED)) == 'True'
    app.config['PASSWORD'] = os.environ.get('PASSWORD', '')
    
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port)
    