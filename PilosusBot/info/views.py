from flask_login import login_required
from . import info


@info.route('/')
@login_required
def index():
    return 'OK'
