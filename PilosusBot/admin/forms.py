from flask import current_app
from flask_wtf import FlaskForm
from polyglot.detect import langids as langs
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, DateTimeField
from wtforms.validators import DataRequired, Required, Length, Regexp
from flask_pagedown.fields import PageDownField
from ..models import Sentiment, Language
from ..utils import is_valid_lang_code, is_valid_lang_name
from ..exceptions import ValidationError


class SentimentForm(FlaskForm):
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


class LanguageForm(FlaskForm):
    code = SelectField("Language code",
                       validators=[DataRequired(),
                                   Length(2, 3, "Two-letter or three-letter code "
                                                "in compliance with ISO 639-1 codes")])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(LanguageForm, self).__init__(*args, **kwargs)

        # prepopulate field with language not in use yet
        used_langs = set([i.code for i in Language.query.all()])
        all_langs = set(langs.isoLangs.keys())
        not_used = all_langs - used_langs
        self.code.choices = sorted([(lang, "{0} ({1})".format(lang, langs.isoLangs[lang]['name']))
                                    for lang in not_used])

    #def validate_code(self, field):
    #    if not is_valid_lang_code(field.data):
    #        raise ValidationError('Language code not found in the list of ISO 631-1 codes.')
    #
    #    if Language.query.filter_by(code=field.data).first():
    #        raise ValidationError('Language code already in use.')
