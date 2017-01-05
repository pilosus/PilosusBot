from datetime import datetime
from flask import current_app, flash, redirect, request, render_template, url_for
from flask_login import current_user, login_required
from ..models import Permission, Sentiment, Language
from ..decorators import admin_required, permission_required
from ..utils import lang_code_to_lang_name as code2name
from .forms import SentimentForm, LanguageForm
from .. import db
from . import admin


# redirect
@admin.route('/')
@login_required
@permission_required(Permission.MODERATE)
def index():
    return redirect(url_for('.sentiments'))


# sentiments
@admin.route('/sentiments', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE)
def sentiments():
    form = SentimentForm()
    if form.validate_on_submit():
        sentiment = Sentiment(author=current_user._get_current_object(),
                              language_id=form.language.data,
                              body=form.body.data,
                              score=form.score.data,
                              timestamp=form.timestamp.data)
        db.session.add(sentiment)
        flash('Your sentiment has been published.', 'success')
        return redirect(url_for('.sentiments'))
    page = request.args.get('page', 1, type=int)
    pagination = Sentiment.query.order_by(Sentiment.timestamp.desc()).paginate(
        page, per_page=current_app.config['APP_ITEMS_PER_PAGE'], error_out=False
    )
    sentiments_paginated = pagination.items
    return render_template('admin/sentiments.html',
                           form=form,
                           sentiments=sentiments_paginated,
                           datetimepicker=datetime.utcnow(),
                           pagination=pagination)


@admin.route('/edit-sentiment/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MODERATE)
def edit_sentiment(id):
    sentiment = Sentiment.query.get_or_404(id)

    if not current_user == sentiment.author and not current_user.can(Permission.ADMINISTER):
        flash('The sentiment can be edited by either its author or a site administrator.',
              'warning')
        return redirect(url_for('.sentiments'))

    form = SentimentForm()
    if form.validate_on_submit():
        sentiment.body = form.body.data
        sentiment.score = form.score.data
        sentiment.language_id = form.language.data
        sentiment.timestamp = form.timestamp.data

        db.session.add(sentiment)

        flash('The sentiment has been updated.', 'success')
        return redirect(url_for('.sentiments'))

    form.body.data = sentiment.body
    form.score.data = sentiment.score
    form.language.data = sentiment.language_id
    form.timestamp.data = datetime.utcnow()

    return render_template('admin/edit_sentiment.html',
                           form=form,
                           datetimepicker=datetime.utcnow(),
                           )


@admin.route('/remove-sentiment/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def remove_sentiment(id):
    sentiment = Sentiment.query.get_or_404(id)

    if current_user != sentiment.author or \
            not current_user.can(Permission.ADMINISTER):
        flash('The sentiment can be removed by either its author or a site administrator.',
              'warning')
    else:
        db.session.delete(sentiment)
        flash('The sentiment has been removed.', 'success')

    return redirect(url_for('.sentiments'))


# languages
@admin.route('/languages', methods=['GET', 'POST'])
@login_required
@admin_required
def languages():
    form = LanguageForm()
    if form.validate_on_submit():
        lang = Language(code=form.code.data)
        db.session.add(lang)
        flash('Your language has been published.', 'success')
        return redirect(url_for('.languages'))
    page = request.args.get('page', 1, type=int)
    #pagination = Language.query.order_by(Language.code.desc()).paginate(
    #    page, per_page=current_app.config['APP_ITEMS_PER_PAGE'], error_out=False
    #)
    pagination = Language.query.outerjoin(Sentiment).\
        group_by(Language.id).\
        order_by(db.func.count(Sentiment.id).desc()).paginate(
        page, per_page=current_app.config['APP_ITEMS_PER_PAGE'], error_out=False
    )
    languages_paginated = pagination.items
    return render_template('admin/languages.html',
                           form=form,
                           languages=languages_paginated,
                           pagination=pagination)


@admin.route('/language/<code>', methods=['GET', 'POST'])
@login_required
@admin_required
def language(code):
    lang = Language.query.filter_by(code=code).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = Sentiment.query.filter_by(language=lang).paginate(
       page, per_page=current_app.config['APP_ITEMS_PER_PAGE'], error_out=False
    )
    sentiments_paginated = pagination.items
    return render_template('admin/lang_sentiments.html',
                           language=lang,
                           sentiments=sentiments_paginated,
                           pagination=pagination)


@admin.route('/remove-language/<code>', methods=['GET', 'POST'])
@login_required
@admin_required
def remove_language(code):
    lang = Language.query.filter_by(code=code).first_or_404()
    db.session.delete(lang)
    flash('Your language and all associated sentiments have been deleted.', 'success')
    return redirect(url_for('.languages'))
