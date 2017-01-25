import unittest
from flask import current_app, json, url_for
from werkzeug.datastructures import Headers
#from flask_testing import TestCase
from PilosusBot import create_app, db
from PilosusBot.models import Language, Permission, Role, Sentiment, User
from tests.helpers import TelegramUpdates, HTTP


"""
Unit-/integrational-tests for webhook blueprint

See more about unittesting in Flask applications:
flask.pocoo.org/docs/latest/testing/
http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.Client
https://pythonhosted.org/Flask-Testing/
"""


class WebhooksTestCase(unittest.TestCase):
    def setUp(self):
        """Method called before each unit-test"""
        # create app, set TESTING flag to disable error catching
        self.app = create_app('testing')

        # push app context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # create databases, see config.py for testing db settings
        db.create_all()

        # pre-fill db with minimal needed things
        Role.insert_roles()
        Language.insert_basic_languages()
        User.generate_fake(10)
        Sentiment.generate_fake(100)

        # Werkzeug Client to make requests
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        """Method called after each unit-test"""
        # remove current db session
        db.session.remove()

        # remove db itself
        db.drop_all()

        # remove app context
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_handle_only_post(self):
        response = self.client.get(TelegramUpdates.URL_HANDLE_WEBHOOK)
        self.assertTrue(response.status_code == 405,
                        'Failed to restrict allowed method to POST only')

    def test_handle_empty_input(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for empty input')

        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for empty input')

    def test_handle_bad_id_bad_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_BAD_ID_BAD_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'bad reply_message_id and bad text length')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'bad reply_message_id and bad text length')

    def test_handle_ok_id_bad_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_OK_ID_BAD_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'bad text length')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'bad text length')

    def test_handle_bad_id_ok_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_BAD_ID_OK_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'bad reply_message_id')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'bad reply_message_id')

    def test_handle_malformed_Message(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_MESSAGE),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'a malformed Message')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'a malformed Message')

    def test_handle_malformed_Chat_of_Message(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_CHAT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'a malformed Chat of the Message')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'a malformed Chat of the Message')

    def test_handle_update_id_already_used(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_SAME_UPDATE_ID),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for an Update with '
                        'an ID already used')
        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for an Update with '
                         'an ID already used')

    def test_handle_valid_input(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_OK_ID_OK_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for a valid input')
        self.assertNotEqual({}, response.data,
                            'Failed to return a non-empty JSON for a valid input')
        self.assertEqual(TelegramUpdates.TEXT_OK_ID_OK_TEXT,
                         json.loads(response.data),
                         'Failed to return an Update itself for a valid input Update')

    def test_sethook_only_post(self):
        response = self.client.get(TelegramUpdates.URL_HANDLE_WEBHOOK)
        self.assertTrue(response.status_code == 405,
                        'Failed to restrict allowed method to POST only')

    def test_sethook_not_authenticated_user(self):
        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertEqual(response.status_code, 403,
                         'Failed to forbid access for a non-authenticated user')

    def test_sethook_moderator_user(self):
        moderator_role = Role.query.filter_by(name='Moderator').first()
        moderator = User(email='moderator@example.com',
                         username='test',
                         role=moderator_role,
                         password='test',
                         confirmed=True,
                         )
        db.session.add(moderator)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('moderator@example.com', 'test'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 403,
                         'Failed to forbid access for a moderator user')

    def test_sethook_administrator_user(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        # Werkzeug's test client doesn't have embedded
        # Basic HTTP Authentication out of box like requests have,
        # so we have to implement it by making up headers.
        # see also
        # http://stackoverflow.com/a/30248823/4241180
        # http://stackoverflow.com/a/27643297/4241180
        # http://blog.bstpierre.org/flask-testing-auth
        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 200,
                         'Failed to allow access for an administrator user')

        response_json = json.loads(response.data)
        self.assertTrue(response_json['ok'] is False)
        self.assertEqual(response_json['error_code'], 400,
                         'Failed to return error code 400 '
                         'when setting non-HTTPS Webhook URL: {}'.
                         format(response_json['description']))
        self.assertEqual(response_json['url'], url_for('webhook.handle_webhook', _external=True),
                         'Failed to return a JSON with the URL of the Webhook handing view '
                         'for an authorized user')

    def test_unsethook_administrator_user(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        # Werkzeug's test client doesn't have embedded
        # Basic HTTP Authentication out of box like requests have,
        # so we have to implement it by making up headers.
        # see also
        # http://stackoverflow.com/a/30248823/4241180
        # http://stackoverflow.com/a/27643297/4241180
        # http://blog.bstpierre.org/flask-testing-auth
        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        response = self.client.post(TelegramUpdates.URL_UNSET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 200,
                         'Failed to return status code 200 '
                         'when unsetting Webhook URL by the administrator user')

        response_json = json.loads(response.data)
        self.assertEqual(response_json['url'], '',
                         'Failed to return an empty field for the URL in JSON '
                         'when unsetting Webhook URL by the administrator user')

    def test_finish(self):
        self.fail('Finish tests!')