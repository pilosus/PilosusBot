#!/usr/bin/env python

"""
Create a Flask application and push an application context,
which will be set throughout the entire life of the process.

Celery needs access to celery instance in order to use Celery
configuration set up using app's config file,  which in turn
uses dotenv (environment variables).

Celery workers should be launched as follows:
(venv) $ celery -A celery_launcher.celery worker -Q assess -l info --hostname=assess-server@%h
(venv) $ celery -A celery_launcher.celery worker -Q select -l info --hostname=select-server@%h
(venv) $ celery -A celery_launcher.celery worker -Q send -l info --hostname=send-server@%h
"""

import os
from PilosusBot import celery, create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()
