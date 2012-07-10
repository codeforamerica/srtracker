import os
from flask import Flask, render_template, request, abort, redirect, url_for
import requests
import iso8601

# Config
DEBUG = True
OPEN311_SERVER = 'http://ec2-50-16-81-245.compute-1.amazonaws.com/api'
OPEN311_API_KEY = 'WelcomeToTheChicagoView'

app = Flask(__name__)

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
    url = '%s/requests/%s.json?api_key=%s' % (app.config['OPEN311_SERVER'], request_id, app.config['OPEN311_API_KEY'])
    r = requests.get(url)
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
    
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port)