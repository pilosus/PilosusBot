import os
import tempfile
import unittest
from unittest.mock import patch, call
from flask import current_app, json, url_for
from werkzeug.datastructures import Headers
from PilosusBot import create_app, db
from PilosusBot.models import Language, Role, Sentiment, User
from PilosusBot.exceptions import ValidationError
from PilosusBot.webhook.errors import page_not_found, method_not_allowed, \
    internal_server_error
from tests.helpers import TelegramUpdates, HTTP, MockCappedCollection
from qr import CappedCollection


"""
Unit-/integrational-tests for webhook blueprint

See more about unittesting in Flask applications:
flask.pocoo.org/docs/latest/testing/
http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.Client
https://pythonhosted.org/Flask-Testing/
"""


class WebhooksTestCase(unittest.TestCase):
    maxDiff = None

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
        Sentiment.generate_fake(25)

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

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_only_post(self, mocked_send_to_chat, mocked_celery_chain):
        response = self.client.get(TelegramUpdates.URL_HANDLE_WEBHOOK)
        self.assertTrue(response.status_code == 405,
                        'Failed to restrict allowed method to POST only')

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_empty_input(self, mocked_send_to_chat, mocked_celery_chain):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertTrue(response.status_code == 200,
                        'Failed to return status code 200 for empty input')

        self.assertEqual({}, json.loads(response.data),
                         'Failed to return an empty JSON for empty input')

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_bad_id_bad_text(self, mocked_send_to_chat, mocked_celery_chain):
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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_ok_id_bad_text(self, mocked_send_to_chat, mocked_celery_chain):
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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_bad_id_ok_text(self, mocked_send_to_chat, mocked_celery_chain):
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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_malformed_Message(self, mocked_send_to_chat, mocked_celery_chain):
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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_malformed_Chat_of_Message(self, mocked_send_to_chat, mocked_celery_chain):
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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch.object(CappedCollection, 'elements', lambda *args, **kwargs: [TelegramUpdates.UPDATE_ID])
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_update_id_already_used(self, mocked_send_to_chat, mocked_celery_chain):
        # we don't need to test celery tasks in the view
        # that's objective for a separate test suite
        mocked_send_to_chat.return_value = None
        mocked_celery_chain.return_value = None

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

        mocked_send_to_chat.apply_async.assert_called_with(args=[{}])

        with self.assertRaises(AssertionError) as chain_err:
            mocked_celery_chain.assert_called()

        self.assertIn("Expected 'celery_chain' to have been called",
                      str(chain_err.exception))
        self.assertEqual(mocked_celery_chain.call_args_list, [])

    @patch('PilosusBot.processing.CappedCollection', MockCappedCollection.get_mock())
    @patch('PilosusBot.webhook.views.celery_chain')
    @patch('PilosusBot.webhook.views.send_message_to_chat')
    def test_handle_valid_input(self, mocked_send_to_chat, mocked_celery_chain):
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
        # watch out! parse_update eliminates Updates with message_id already processed
        # so we have to use not parsed Update here
        mocked_update = {'chat_id': TelegramUpdates.TEXT_OK_ID_OK_TEXT['message']['chat']['id'],
                         'reply_to_message_id': TelegramUpdates.TEXT_OK_ID_OK_TEXT['message']['message_id'],
                         'text': TelegramUpdates.TEXT_OK_ID_OK_TEXT['message']['text']}
        mocked_celery_chain.assert_called_with(mocked_update)

        with self.assertRaises(AssertionError) as send_err:
            mocked_send_to_chat.assert_called()

        self.assertIn("Expected 'send_message_to_chat' to have been called",
                      str(send_err.exception))
        self.assertEqual(mocked_send_to_chat.call_args_list, [])

    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_sethook_only_post(self, mock_requests):
        response = self.client.get(TelegramUpdates.URL_HANDLE_WEBHOOK)
        self.assertTrue(response.status_code == 405,
                        'Failed to restrict allowed method to POST only')

        with self.assertRaises(AssertionError) as err:
            mock_requests.assert_called()

        self.assertIn("Expected 'post' to have been called", str(err.exception))
        self.assertEqual(mock_requests.call_args_list, [])

    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_sethook_not_authenticated_user(self, mock_requests):
        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertEqual(response.status_code, 403,
                         'Failed to forbid access for a non-authenticated user')

        with self.assertRaises(AssertionError) as err:
            mock_requests.assert_called()

        self.assertIn("Expected 'post' to have been called", str(err.exception))

    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_sethook_moderator_user(self, mock_requests):
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
        with self.assertRaises(AssertionError) as err:
            mock_requests.assert_called()

        self.assertIn("Expected 'post' to have been called", str(err.exception))

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_sethook_administrator_user(self, mock_requests):
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
        mock_requests.assert_called()
        self.assertIn(call(files=None,
                           json={'url': TelegramUpdates.URL_HANDLE_WEBHOOK,
                                 'max_connections': current_app.config['SERVER_MAX_CONNECTIONS'],
                                 'allowed_updates': []},
                           timeout=current_app.config['TELEGRAM_REQUEST_TIMEOUT_SEC'] * 60,
                           url=current_app.config['TELEGRAM_URL'] + 'setWebhook'),
                      mock_requests.call_args_list)

    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_unsethook_administrator_user(self, mock_requests):
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
        mock_requests.assert_called()
        self.assertIn(call(files=None,
                           json={'url': '',
                                 'max_connections': current_app.config['SERVER_MAX_CONNECTIONS'],
                                 'allowed_updates': []},
                           timeout=current_app.config['TELEGRAM_REQUEST_TIMEOUT_SEC'] * 60,
                           url=current_app.config['TELEGRAM_URL'] + 'setWebhook'),
                      mock_requests.call_args_list)

    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_setwebhook_with_SSL_certificate(self, mock_requests):
        # set up SSL certificate
        tmp_cert_file = os.path.join(tempfile.gettempdir(), "SSL.cert")
        with open(tmp_cert_file, 'wb') as fp:
            fp.write(b'SSL Certificate Content')

        # add administrator
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        # make a request
        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        new_config = {'TELEGRAM_URL': current_app.config['TELEGRAM_URL'],
                      'SERVER_PUBLIC_KEY': tmp_cert_file,
                      'SERVER_MAX_CONNECTIONS': current_app.config['SERVER_MAX_CONNECTIONS'],
                      'TELEGRAM_REQUEST_TIMEOUT_SEC': current_app.config['TELEGRAM_REQUEST_TIMEOUT_SEC']
                      }

        with patch.dict(current_app.config, new_config):
            response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                        data=json.dumps({}),
                                        follow_redirects=True,
                                        headers=headers)

            self.assertEqual(current_app.config['SERVER_PUBLIC_KEY'], tmp_cert_file)
            self.assertEqual(response.status_code, 200,
                             'Failed to return status code 200 '
                             'when setting Webhook URL by the administrator user '
                             'with SSL certificate specified')
            mock_requests.assert_called()

    @patch('requests.post')
    def test_setting_webhook_with_exception_raised(self, mock_requests):
        from requests.exceptions import RequestException
        mock_requests.side_effect = RequestException('Boom!')

        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        response_json = json.loads(response.data)
        self.assertEqual(response_json['error_code'], 599,
                         'Failed to return error code 599 when RequestException is thrown')
        mock_requests.assert_called()

    def test_unauthorized_access_to_get_token(self):
        response = self.client.get(url_for('webhook.get_token'),
                                   data=json.dumps(TelegramUpdates.EMPTY),
                                   follow_redirects=True,
                                   headers=TelegramUpdates.HEADERS)

        self.assertEqual(response.status_code, 401,
                         'Failed to forbid access for a non-authorized user')

    def test_authorized_access_to_get_token(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        response = self.client.get(url_for('webhook.get_token'),
                                   data=json.dumps(TelegramUpdates.EMPTY),
                                   follow_redirects=True,
                                   headers=headers)

        self.assertEqual(response.status_code, 200,
                         'Failed to give access for a valid authorized user')

        response_json = json.loads(response.data)
        self.assertEqual(response_json['expiration'], 3600)

    def test_login_required_blank_password(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', ''))

        response = self.client.post(TelegramUpdates.URL_UNSET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 403,
                         'Failed to return status code 403 '
                         'when unsetting Webhook URL by the '
                         'valid user with blank password')

    def test_login_required_incorrect_password(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'wrong'))

        response = self.client.post(TelegramUpdates.URL_UNSET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 403,
                         'Failed to return status code 403 '
                         'when unsetting Webhook URL by the '
                         'valid user with incorrect password')

    def test_login_required_incorrect_username(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('incorrect_username', 'test'))

        response = self.client.post(TelegramUpdates.URL_UNSET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 403,
                         'Failed to return status code 403 '
                         'when unsetting Webhook URL by the '
                         'user with incorrect username')

    @patch('requests.post', side_effect=ValidationError('Boom!', 400))
    def test_bad_request_response(self, mock_requests):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=True,
                     )
        db.session.add(admin)
        db.session.commit()

        headers = Headers()
        headers.add(*HTTP.basic_auth('admin@example.com', 'test'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 400,
                         'Failed to return status code 400 '
                         'when ValidationError is raised')
        mock_requests.assert_called()

    def test_webhook_custom_errors_returning_json(self):
        error_404 = page_not_found('foo')
        error_405 = method_not_allowed('bar')
        error_500 = internal_server_error('baz')

        # error functions return flask Response object
        # http://flask.pocoo.org/docs/0.12/api/#flask.Response
        self.assertEqual(error_404.status_code, 404)
        self.assertEqual(error_405.status_code, 405)
        self.assertEqual(error_500.status_code, 500)

