import os
from flask import Flask, render_template, request, abort, redirect, url_for, make_response
import requests
import iso8601

# Config
DEBUG = True
OPEN311_SERVER = 'localhost:5000'
OPEN311_API_KEY = ''
PASSWORD_PROTECTED = False

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
    params = {}
    if app.config['OPEN311_API_KEY']:
        params['api_key'] = app.config['OPEN311_API_KEY']
    r = requests.get(url, params=params)
    sr = r.json
    
    if sr:
        sr[0]['requested_datetime'] = iso8601.parse_date(sr[0]['requested_datetime'])
        for activity in sr[0]['activities']:
            activity['datetime'] = iso8601.parse_date(activity['datetime'])
        
        sr[0]['activities'].reverse()
        
        body = render_template('service_request.html', sr=sr[0])
        return (body, 200, None)
    
    else:
        return ("No such service request", 404, None)



if __name__ == "__main__":
    app.config.from_object(__name__)
    if 'DEBUG' in os.environ:
        app.debug = os.environ['DEBUG'] == 'True' and True or False
    if 'OPEN311_SERVER' in os.environ:
        app.config['OPEN311_SERVER'] = os.environ['OPEN311_SERVER']
    if 'OPEN311_API_KEY' in os.environ:
        app.config['OPEN311_API_KEY'] = os.environ['OPEN311_API_KEY']
    
    app.config['PASSWORD_PROTECTED'] = 'PASSWORD_PROTECTED' in os.environ and (os.environ['PASSWORD_PROTECTED'] == 'True') or False
    app.config['PASSWORD'] = 'PASSWORD' in os.environ and os.environ['PASSWORD'] or ''
    
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port)