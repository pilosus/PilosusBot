from flask import render_template, url_for
from flask_login import login_required
from . import info


@info.route('/')
def index():
    return render_template('info/index.html')
