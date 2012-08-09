import os
from flask import Flask, render_template, request, abort, redirect, url_for, make_response, session
import requests
import iso8601
import updater

# Config
DEBUG = True
OPEN311_SERVER = 'localhost:5000'
OPEN311_API_KEY = ''
PASSWORD_PROTECTED = False
SECRET_KEY = 'please_please_change_this!'

app = Flask(__name__)

@app.before_request
def password_protect():
    if app.config['PASSWORD_PROTECTED']:
        auth = request.authorization
        if not auth or auth.password != app.config['PASSWORD']:
            # Tell the browser to do basic auth
            return make_response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.route("/")
def index():
    return "Chicago Nightly 311";


@app.route("/requests")
def redirect_request():
    if 'request_id' in request.args:
        return redirect(url_for('show_request', request_id=request.args['request_id']))
    else:
        abort(404)


@app.route("/requests/<request_id>")
def show_request(request_id):
    # TODO: Should probably use Three or something nice for this...
    url = '%s/requests/%s.json' % (app.config['OPEN311_SERVER'], request_id)
    params = {'extensions': 'true', 'legacy': 'false'}
    if app.config['OPEN311_API_KEY']:
        params['api_key'] = app.config['OPEN311_API_KEY']
    r = requests.get(url, params=params)
    if r.status_code == 404:
        # TODO: need a template
        # Log this?
        return ("There is no service request on file for #%s" % request_id, 404, None)
    elif r.status_code != 200:
        # TODO: need a template
        # TODO: log this, since we really shouldn't receive errors
        return ("There was an error getting data about service request #%s" % request_id, 404, None)
        
    sr = r.json
    if sr:
        sr[0]['requested_datetime'] = iso8601.parse_date(sr[0]['requested_datetime'])
        for note in sr[0]['notes']:
            note['datetime'] = iso8601.parse_date(note['datetime'])
        
        sr[0]['notes'].reverse()
        
        subscribed = False
        if sr[0]['status'] == 'open' and session.get('email', None):
            # TODO: when subscription service supports more than e-mail, 
            # we should probably be able to show all your subscriptions here
            subscribed = updater.subscription_exists(request_id, 'email', session.get('email', ''))
        
        body = render_template('service_request.html', sr=sr[0], subscribed=subscribed)
        return (body, 200, None)
    
    else:
        # TODO: need a template
        return ("There is no service request on file for #%s" % request_id, 404, None)


@app.route("/subscribe/<request_id>", methods=["POST"])
def subscribe(request_id):
    email = request.form.get('update_email')
    # TODO: validate email
    if email:
        updater.subscribe(request_id, 'email', email)
        # TODO: should we get back a secret subscription key and use that instead?
        session['email'] = email
    return redirect(url_for('show_request', request_id=request_id))



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
    