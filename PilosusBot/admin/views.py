from flask_login import login_required
from ..models import Permission
from ..decorators import admin_required, permission_required
from . import admin


@admin.route('/sentiments')
@login_required
@permission_required(Permission.MODERATE)
def sentiments():
    pass


@admin.route('/edit-sentiment/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def edit_sentiment(id):
    pass


@admin.route('/remove-sentiment/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def remove_sentiment(id):
    pass

