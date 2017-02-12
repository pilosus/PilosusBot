import forgery_py
import json
import random
import unittest
from datetime import datetime
from unittest.mock import patch
from flask import current_app, url_for
from PilosusBot import create_app, db
from PilosusBot.models import Role, Language, User, Sentiment
from PilosusBot.utils import lang_code_to_lang_name
from tests.helpers import MockSentimentForm, MockSentimentModel
from polyglot.detect import langids as langs
from werkzeug.datastructures import Headers


class AdminTestCase(unittest.TestCase):
    maxDiff = None
    items_per_page = current_app.config['APP_ITEMS_PER_PAGE']

    def setUp(self):
        # create an app with testing config
        self.app = create_app('testing')

        # push context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # create all db
        db.create_all()

        # pre-fill db with minimal needed things
        Role.insert_roles()
        Language.insert_basic_languages()

        # werkzeug test client
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        # destroy session
        db.session.remove()

        # drop all db
        db.drop_all()

        # remove app context
        self.app_context.pop()

    def create_user(self, role_name='Administrator', email='admin@example.com',
                    username='admin', password='test', invited=True, confirmed=True):
        role = Role.query.filter_by(name=role_name).first()
        user = User(email=email,
                    username=username,
                    role=role,
                    password=password,
                    invited=invited,
                    confirmed=confirmed)
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, email='admin@example.com', password='test', follow_redirects=True):
        response = self.client.post(url_for('auth.login'),
                                    data=dict(email=email, password=password),
                                    follow_redirects=follow_redirects)
        return response

    def create_languages(self, langs_list=None):
        if langs_list is None:
            langs_list = langs.isoLangs.keys()

        for lang in langs_list:
            l = Language(code=lang)
            db.session.add(l)

        db.session.commit()

    def remove_langs(self, langs_list=None):
        if langs_list is None:
            langs_list = Language.query.all()

        for lang in langs_list:
            db.session.delete(lang)

        db.session.commit()

    def test_admin_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_csrf_disabled(self):
        self.assertFalse(current_app.config['WTF_CSRF_ENABLED'])

    def test_admin_index_anonymous(self):
        response = self.client.get(url_for('admin.index'), follow_redirects=True)
        data = response.get_data(as_text=True)

        self.assertIn('Please log in to access this page', data,
                      'Failed to redirect anonymous user to a login page')

    def test_admin_index_valid_user(self):
        admin = self.create_user()
        login_response = self.login()
        index_reponse = self.client.get(url_for('admin.index'), follow_redirects=True)
        index_data = index_reponse.get_data(as_text=True)

        self.assertIn('Create Sentiment', index_data,
                      'Failed to redirect authenticated user '
                      'with proper permissions to admin.sentiments page.')

    def test_sentiments_get_pagination(self):
        admin = self.create_user()
        login_response = self.login()

        Sentiment.generate_fake(count=((self.items_per_page * 2) + 2))
        sentiments = Sentiment.query.order_by(Sentiment.timestamp.desc())

        response_page1 = self.client.get(url_for('admin.sentiments'),
                                         follow_redirects=True)
        data_page1 = response_page1.get_data(as_text=True)

        response_page2 = self.client.get(url_for('admin.sentiments', page=2),
                                         follow_redirects=True)
        data_page2 = response_page2.get_data(as_text=True)

        response_page3 = self.client.get(url_for('admin.sentiments', page=3),
                                         follow_redirects=True)
        data_page3 = response_page3.get_data(as_text=True)

        self.assertIn(sentiments.paginate(page=1,
                                          per_page=self.items_per_page).
                      items[0].body_html,
                      data_page1,
                      'Failed to show a sentiment on the proper page.')
        self.assertIn(sentiments.paginate(page=2,
                                          per_page=self.items_per_page).
                      items[0].body_html,
                      data_page2)
        self.assertIn(sentiments.paginate(page=3,
                                          per_page=self.items_per_page).
                      items[0].body_html,
                      data_page3)

    @patch('PilosusBot.admin.views.Sentiment')
    @patch('PilosusBot.admin.views.SentimentForm')
    def test_sentiments_post(self, mock_form, mock_sentiment):
        mock_form.return_value = MockSentimentForm()
        mock_sentiment.return_value = MockSentimentModel()

        admin = self.create_user()
        login_response = self.login()

        text = forgery_py.lorem_ipsum.sentences(5)
        latin = Language.query.filter_by(code='la').first()

        submit_response = self.client.post(url_for('admin.sentiments',
                                                   data=dict(body=text,
                                                             score=random.random(),
                                                             language=latin.id,
                                                             timestamp=datetime.utcnow()),
                                           follow_redirects=True))
        data_submit = submit_response.get_data(as_text=True)

        mock_form.assert_called()
        mock_sentiment.assert_called()

        # cannot redirect for some reasons
        # instead of awkward monkey-patching it's better to use
        # functional testing with Selenium
        self.assertIn('Redirecting.', data_submit,
                      'Failed to submit valid sentiment form data '
                      'from a valid user.')

    def test_edit_sentiment_get_neither_admin_nor_author(self):
        admin = self.create_user()
        Sentiment.generate_fake(count=10)
        sentiment = Sentiment.query.first()

        user = self.create_user(role_name='Moderator', email='user@example.com',
                                username='user', password='test')

        login_response = self.login(email='user@example.com', password='test')

        response = self.client.get(url_for('admin.edit_sentiment', id=sentiment.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('can be edited by either its author or a site administrator',
                      data, 'Failed to forbid editing to a user who is neither '
                            'an author nor administrator.')

    def test_edit_sentiment_get_admin(self):
        admin = self.create_user()
        Sentiment.generate_fake(count=10)
        sentiment_admin = Sentiment.query.first()

        login_response = self.login()
        response = self.client.get(url_for('admin.edit_sentiment', id=sentiment_admin.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn(sentiment_admin.body,
                      data, 'Failed to show sentiment editing form to an admin.')

    def test_edit_sentiment_get_author_non_admin(self):
        user = self.create_user(role_name='Moderator', email='user@example.com',
                                username='user', password='test')
        Sentiment.generate_fake(count=10)
        sentiment_user = Sentiment.query.first()

        login_response = self.login(email='user@example.com', password='test')
        response = self.client.get(url_for('admin.edit_sentiment', id=sentiment_user.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn(sentiment_user.body,
                      data, 'Failed to show sentiment editing form to an non-admin author.')

    @patch('PilosusBot.admin.views.db.session.add')
    @patch('PilosusBot.admin.views.Sentiment')
    @patch('PilosusBot.admin.views.SentimentForm')
    def test_edit_sentiment_post(self, mock_form, mock_sentiment, mock_db):
        mock_form.return_value = MockSentimentForm()
        mock_sentiment.return_value = MockSentimentModel()
        mock_db.side_effect = lambda *args, **kwargs: True

        admin = self.create_user()
        login_response = self.login()

        Sentiment.generate_fake(count=10)
        sentiment = Sentiment.query.first()

        text = forgery_py.lorem_ipsum.sentences(5)
        latin = Language.query.filter_by(code='la').first()

        submit_response = self.client.post(url_for('admin.edit_sentiment', id=sentiment.id),
                                           data=dict(body=text,
                                                     score=random.random(),
                                                     language=latin.id,
                                                     timestamp=datetime.utcnow()),
                                           follow_redirects=False)
        data_submit = submit_response.get_data(as_text=True)

        mock_form.assert_called()

        self.assertIn('Redirecting.', data_submit,
                      'Failed to update sentiment edited by a valid user.')

    def test_remove_sentiment_admin(self):
        admin = self.create_user()
        login_response = self.login()

        Sentiment.generate_fake(count=10)
        sentiment = Sentiment.query.first()

        response = self.client.get(url_for('admin.remove_sentiment',
                                           id=sentiment.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)

        self.assertIn('The sentiment has been removed', data,
                      'Failed to allow sentiment removal by an administrator.')

    def test_remove_sentiment_author_non_admin(self):
        user = self.create_user(role_name='Moderator',
                                email='user@example.com',
                                username='user',
                                password='test')

        latin = Language.query.filter_by(code='la').first()
        text = forgery_py.lorem_ipsum.sentences(5)

        sentiment = Sentiment(author=user,
                              language_id=latin.id,
                              body=text,
                              score=0.5,
                              timestamp=datetime.utcnow())

        login_response = self.login(email='user@example.com',
                                          password='test')

        response = self.client.get(url_for('admin.remove_sentiment',
                                           id=sentiment.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('The sentiment has been removed', data,
                      'Failed to allow sentiment removal by its author.')

    def test_remove_sentiment_neither_author_nor_admin(self):
        user1 = self.create_user(role_name='Moderator',
                                 email='user1@example.com',
                                 username='user1',
                                 password='test')
        user2 = self.create_user(role_name='Moderator',
                                 email='user2@example.com',
                                 username='user2',
                                 password='test')

        latin = Language.query.filter_by(code='la').first()
        text = forgery_py.lorem_ipsum.sentences(5)

        sentiment = Sentiment(author=user1,
                              language_id=latin.id,
                              body=text,
                              score=0.5,
                              timestamp=datetime.utcnow())

        user2_login_response = self.login(email='user2@example.com',
                                          password='test')

        response = self.client.get(url_for('admin.remove_sentiment',
                                           id=sentiment.id),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)

        self.assertIn('either its author or a site administrator', data,
                      'Failed to forbid sentiment removal for a user '
                      'who neither an author nor administrator.')

    def test_languages_get(self):
        admin = self.create_user()
        login_response = self.login()

        # remove existing languages in order to avoid db IntegrityError
        self.remove_langs()

        languages = [lang for lang in langs.isoLangs if len(lang) == 2]
        self.create_languages(langs_list=languages)

        # 2 full pages + 1 page with 1 item
        number_of_items = 2 * self.items_per_page + 1

        for i in range(number_of_items):
            # descending number of sentiments generated
            # as we loop over list of languages
            Sentiment.generate_fake(count=(number_of_items - i),
                                    language_code=languages[i % len(languages)])

        lang_page1 = Language.query.filter_by(
            code=languages[0]).first()
        lang_page2 = Language.query.filter_by(
            code=languages[self.items_per_page]).first()
        lang_page3 = Language.query.filter_by(
            code=languages[number_of_items % len(languages)]).first()

        response_page1 = self.client.get(url_for('admin.languages',
                                                 page=1),
                                         follow_redirects=True)
        data_page1 = response_page1.get_data(as_text=True)

        response_page2 = self.client.get(url_for('admin.languages',
                                                 page=2),
                                         follow_redirects=True)
        data_page2 = response_page2.get_data(as_text=True)

        response_page3 = self.client.get(url_for('admin.languages',
                                                 page=3),
                                         follow_redirects=True)
        data_page3 = response_page3.get_data(as_text=True)

        self.assertIn('{lang_name}, {lang_count} sentiments'.
                      format(lang_name=lang_code_to_lang_name(lang_page1.code),
                             lang_count=lang_page1.sentiments.count()),
                      data_page1,
                      'Failed to show language with largest number of '
                      'sentiments in it on the first page.')

        self.assertIn('{lang_name}, {lang_count} sentiments'.
                      format(lang_name=lang_code_to_lang_name(lang_page2.code),
                             lang_count=lang_page2.sentiments.count()),
                      data_page2,
                      'Failed to show language on the proper page.')

        self.assertIn('{lang_name}, {lang_count} sentiments'.
                      format(lang_name=lang_code_to_lang_name(lang_page3.code),
                             lang_count=lang_page3.sentiments.count()),
                      data_page3,
                      'Failed to show language with the least number '
                      'of sentiments on the last page.')

    def test_languages_post(self):
        admin = self.create_user()
        login_response = self.login()
        self.remove_langs()

        submit_response = self.client.post(url_for('admin.languages'),
                                           data=dict(code='en'),
                                           follow_redirects=True)
        data_submit = submit_response.get_data(as_text=True)

        self.assertIn('Your language has been published',
                      data_submit,
                      'Failed to submit new language code.')
        self.assertIn('English, 0 sentiments',
                      data_submit,
                      'Failed to redirect after new language submission.')

    def test_language_get(self):
        admin = self.create_user()
        login_response = self.login()

        # 2 full pages + 1 page with 1 item on it
        number_of_items = 2 * self.items_per_page + 1
        Sentiment.generate_fake(count=number_of_items)

        latin = Language.query.filter_by(code='la').first()

        sentiments_page1 = Sentiment.query.\
            filter_by(language=latin).paginate(page=1,
                                               per_page=self.items_per_page)
        sentiments_page2 = Sentiment.query.\
            filter_by(language=latin).paginate(page=2,
                                               per_page=self.items_per_page)
        sentiments_page3 = Sentiment.query.\
            filter_by(language=latin).paginate(page=3,
                                               per_page=self.items_per_page)

        response_page1 = self.client.get(url_for('admin.language',
                                                 code='la',
                                                 page=1),
                                         follow_redirects=True)
        data_page1 = response_page1.get_data(as_text=True)

        response_page2 = self.client.get(url_for('admin.language',
                                                 code='la',
                                                 page=2),
                                         follow_redirects=True)
        data_page2 = response_page2.get_data(as_text=True)

        response_page3 = self.client.get(url_for('admin.language',
                                                 code='la',
                                                 page=3),
                                         follow_redirects=True)
        data_page3 = response_page3.get_data(as_text=True)

        self.assertIn(sentiments_page1.items[0].body_html,
                      data_page1)
        self.assertIn(sentiments_page2.items[0].body_html,
                      data_page2)
        self.assertIn(sentiments_page3.items[0].body_html,
                      data_page3)

    def test_remove_language(self):
        admin = self.create_user()
        login_response = self.login()
        latin = Language.query.filter_by(code='la').first()
        Sentiment.generate_fake(count=10, language_code=latin.code)

        submit_response = self.client.post(url_for('admin.remove_language',
                                                   code=latin.code),
                                           follow_redirects=True)
        data_submit = submit_response.get_data(as_text=True)

        self.assertIn('Your language and all associated sentiments have been deleted',
                      data_submit,
                      'Failed to remove language.')

        sentiments = Sentiment.query.filter_by(language=latin).all()
        self.assertEqual(sentiments, [],
                         'Failed to remove sentiments associated '
                         'with the language removed.')

    def test_remove_page_not_found_html(self):
        admin = self.create_user()
        login_response = self.login()

        submit_response = self.client.post(url_for('admin.remove_language',
                                                   code='no_such_language_code'),
                                           follow_redirects=True)
        data_submit = submit_response.get_data(as_text=True)

        self.assertEqual(submit_response.status_code, 404)
        self.assertIn('Page Not Found', data_submit)

    def test_remove_page_not_found_json(self):
        admin = self.create_user()
        login_response = self.login()

        headers = Headers()
        headers.add('Accept', 'application/json')

        response = self.client.post(url_for('admin.remove_language',
                                            code='no_such_language_code'),
                                    content_type='application/json',
                                    follow_redirects=True,
                                    headers=headers)

        response_json = json.loads(response.data)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_json['error'], 'not found')
