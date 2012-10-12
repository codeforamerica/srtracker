Service Request Tracker
=======================

This web application is built for the City of Chicago as an interface to service requests submitted through their 311 system. It uses Chicago's Open311 API---including Chicago-specific extensions---to provide listings, lookups and subscription capabilities.

It includes the following components:
 - A web application for listing service requests, searching for a specific service request based on ID, and subscribing to email updates for specific service requests
 - A python script (in `/updater`) that checks the Open311 endpoint for 

![Screenshot of SR Tracker](https://raw.github.com/codeforamerica/srtracker/master/screenshot.png)

Installation & Configuration
----------------------------

To install:

    pip install -r requirements.txt
    cp configuration.py.example configuration.py
    cd updater
    ln -s configuration.py ../configuration.py
    # edit configuration.py as described below

SRTracker is broken into two components: the web app and the updater, which polls an Open311 endpoint and sends notifications about updated service requests. They can be configured together or separately.

By default, SRTracker will look for a file named `configuration.py` in its directory. Alternatively, you can specify a path to the config file in the environment variable `SRTRACKER_CONFIGURATION` (this is especially useful for services like Heroku). The updater will use this path as well unless you also specify a separate `UPDATER_CONFIGURATION` env var.

The configuration file itself should be a python file with the following vars:

- `DEBUG`: True or False for debug mode
- `SECRET_KEY`: A random string used as an encryption key for cookies, etc.
- `OPEN311_SERVER`: URL to the Open311 endpoint you are using
- `OPEN311_API_KEY`: The API Key for the Open311 server
- `DB_STRING`: DB connection string for storing subscriptions
- `EMAIL_HOST`: Hostname for the SMTP server to send updates
- `EMAIL_PORT`: Port for the SMTP server to send updates
- `EMAIL_USER`: Username for the SMTP server to send updates
- `EMAIL_PASS`: Password for the SMTP server to send updates
- `EMAIL_FROM`: Email address updates should be sent from
- `EMAIL_SSL`: True or False for whether to use SSL to send updates
- `SRTRACKER_URL`: URL for SRTracker, e.g. 'http://localhost:5000/'. This is used to generate links in updates.

If you want to do all your configuration via environment vars, point `SRTRACKER_CONFIGURATION` at `configuration_environ.py`. It'll read in all above vars from your environment. This is great for services like Heroku.

To run:

    python app.py

_If you are using Apache with mod_wsgi, you'll also want to make sure you configure the app before calling `run()` on it in your .wsgi file. The easiest method is to setup your configuration as above and do the following in your .wsgi file:_

```
from app import app as application
application.config.from_envvar('SRTRACKER_CONFIGURATION')
```


Chicago-specific Open311 Extensions
-----------------------------------

This application relies upon extensions to the [Open311 GeoReport v2 Spec](http://wiki.open311.org/GeoReport_v2) that are specific to Chicago (for the time being). These include:

- `updated_at` parameter: allows sorting requests by when they were updated, not just initially requests
- `notes` field: individual requests may have additional "follow-on" requests that define additional work/activities related to the initial request which are exposed in the `notes` field of an individual service request

## Contributing
In the spirit of [free software][free-sw], **everyone** is encouraged to help
improve this project.

[free-sw]: http://www.fsf.org/licensing/essays/free-sw.html

Here are some ways *you* can contribute:

* by using alpha, beta, and prerelease versions
* by reporting bugs
* by suggesting new features
* by translating to a new language
* by writing or editing documentation
* by writing specifications
* by writing code (**no patch is too small**: fix typos, add comments, clean up
  inconsistent whitespace)
* by refactoring code
* by closing [issues][]
* by reviewing patches
* [financially][]

[issues]: https://github.com/codeforamerica/straymapper/issues
[financially]: https://secure.codeforamerica.org/page/contribute

## Submitting an Issue

We use the [GitHub issue tracker][issues] to track bugs and features. Before submitting a bug report or feature request, check to make sure it hasn't already been submitted. You can indicate support for an existing issue by voting it up. When submitting a bug report, please include a [Gist][] that includes a stack trace and any details that may be necessary to reproduce the bug, including your gem version, Ruby version, and operating system. Ideally, a bug report should include a pull request with failing specs.

[gist]: https://gist.github.com/

## Submitting a Pull Request
1. Fork the project.
2. Create a topic branch.
3. Implement your feature or bug fix.
6. Commit and push your changes.
7. Submit a pull request.

## Copyright
Copyright (c) 2012 Code for America. See [LICENSE][] for details.

[license]: https://github.com/codeforamerica/srtracker/blob/master/LICENSE
