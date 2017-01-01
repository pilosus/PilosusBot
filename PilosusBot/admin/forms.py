from flask import current_app
from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, DateTimeField
from wtforms.validators import DataRequired, Required, Length, Regexp
from flask_pagedown.fields import PageDownField
from ..models import Sentiment, Language


class SentimentForm(Form):
    body = PageDownField("Text", validators=[DataRequired()])
    score = SelectField("Score", coerce=float, default=0.5)
    language = SelectField("Language", coerce=int, default=1)
    timestamp = DateTimeField("Date and time", format='%Y-%m-%d %H:%M:%S')
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(SentimentForm, self).__init__(*args, **kwargs)
        self.levels = current_app.config['APP_SCORE_LEVELS']
        self.score.choices = sorted([(key, "{0} ({1})".format(self.levels[key].desc, str(key)))
                                     for key in self.levels], key=lambda x: x[0])
        self.language.choices = [(lang.id, lang.code) for lang in
                                 Language.query.order_by(Language.code).all()]

    # TODO validation for language and score