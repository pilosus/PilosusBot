from flask import Blueprint
from flask_httpauth import HTTPBasicAuth

webhook = Blueprint('webhook', __name__)

from . import views, errors, authentication
