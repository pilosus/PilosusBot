import base64
import math
import random
import requests
import sys
import unittest
from flask import current_app, json, url_for
from werkzeug.datastructures import Headers
#from flask_testing import TestCase
from PilosusBot import create_app, db
from PilosusBot.models import Language, Permission, Role, Sentiment, User


"""
Unit-/integrational-tests for webhook blueprint

See more about unittesting in Flask applications:
flask.pocoo.org/docs/latest/testing/
http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.Client
https://pythonhosted.org/Flask-Testing/
"""


class TelegramUpdates(object):
    URL_HANDLE_WEBHOOK = url_for('webhook.handle_webhook')
    URL_SET_WEBHOOK = url_for('webhook.set_webhook', action='set', _external=True)
    URL_UNSET_WEBHOOK = url_for('webhook.set_webhook', action='unset', _external=True)
    HEADERS = {'Content-Type': 'application/json'}
    UPDATE_ID = random.randint(100, sys.maxsize)
    TEXT_BIT = "We're all mad here. "
    TEXT = TEXT_BIT * math.ceil(current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] / len(TEXT_BIT))

    EMPTY = {}
    # message_id number that should not trigger bot response (id % settings != 0),
    # text length that should not trigger bot response either (shorter than defined in config)
    TEXT_BAD_ID_BAD_TEXT = {
        "update_id": UPDATE_ID,
        "message": {
          "date": 1441645532,
          "chat": {
             "last_name": "Test Lastname",
             "id": 1111111,
             "type": "private",
             "first_name": "Test Firstname",
             "username": "Testusername"
          },
          "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] + 1,
          "from": {
             "last_name": "Test Lastname",
             "id": 1111111,
             "first_name": "Test Firstname",
             "username": "Testusername"
          },
          "text": "Hello World"
        }
    }
    TEXT_OK_ID_BAD_TEXT = {
        "update_id": random.randint(100, sys.maxsize),
        "message": {
            "date": 1441645532,
            "chat": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "type": "private",
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] * 100,
            "from": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "text": "Hello World"
        }
    }
    TEXT_BAD_ID_OK_TEXT = {
        "update_id": random.randint(100, sys.maxsize),
        "message": {
            "date": 1441645532,
            "chat": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "type": "private",
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] + 1,
            "from": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "text": TEXT
        }
    }
    TEXT_MALFORMED_NO_MESSAGE = {
        "update_id": random.randint(100, sys.maxsize),
    }
    TEXT_MALFORMED_NO_CHAT = {
        "update_id": random.randint(100, sys.maxsize),
        "message": {
            "date": 1441645532,
            "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] * 100,
            "from": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "text": TEXT
        }
    }
    TEXT_SAME_UPDATE_ID = {
        "update_id": UPDATE_ID,
        "message": {
            "date": 1441645532,
            "chat": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "type": "private",
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] * 100,
            "from": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "text": TEXT
        }
    }
    TEXT_OK_ID_OK_TEXT = {
        "update_id": random.randint(100, sys.maxsize),
        "message": {
            "date": 1441645532,
            "chat": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "type": "private",
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "message_id": current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] * 100,
            "from": {
                "last_name": "Test Lastname",
                "id": 1111111,
                "first_name": "Test Firstname",
                "username": "Testusername"
            },
            "text": TEXT
        }
    }


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
                        'GET method not allowed, only POST')

    def test_handle_empty_input(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertTrue(response.status_code == 200,
                        'POST request with empty JSON payload should return '
                        'status code 200')

        self.assertEqual({}, json.loads(response.data),
                         'POST request with empty JSON payload should return '
                         'empty JSON')

    def test_handle_bad_id_bad_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_BAD_ID_BAD_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Update with bad reply_message_id and bad text length '
                         'should return empty JSON')

    def test_handle_ok_id_bad_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_OK_ID_BAD_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Update with bad text length should return empty JSON')

    def test_handle_bad_id_ok_text(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_BAD_ID_OK_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Update with bad reply_message_id should return empty JSON')

    def test_handle_malformed_Message(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_MESSAGE),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Malformed Update did not return empty JSON')

    def test_handle_malformed_Chat_of_Message(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_CHAT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Malformed Update with no chat did not return empty JSON')

    def test_handle_update_id_already_used(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_SAME_UPDATE_ID),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertEqual({}, json.loads(response.data),
                         'Update with update_id already registered did not return empty JSON')

    def test_handle_valid_input(self):
        response = self.client.post(TelegramUpdates.URL_HANDLE_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.TEXT_OK_ID_OK_TEXT),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response.status_code == 200)
        self.assertNotEqual({}, response.data,
                            'Correct Update did not return valid JSON')
        self.assertEqual(TelegramUpdates.TEXT_OK_ID_OK_TEXT,
                         json.loads(response.data),
                         'Correct Update should return the Update itself.')

    def test_sethook_only_post(self):
        response = self.client.get(TelegramUpdates.URL_HANDLE_WEBHOOK)
        self.assertTrue(response.status_code == 405,
                        'GET method not allowed, only POST')

    def test_sethook_not_authenticated_user(self):
        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps(TelegramUpdates.EMPTY),
                                    follow_redirects=True,
                                    headers=TelegramUpdates.HEADERS)

        self.assertEqual(response.status_code, 403,
                         'Forbidden for non-administrators.')

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
        auth_str = 'moderator@example.com:test'.encode('ascii')
        headers.add('Authorization', 'Basic ' + base64.b64encode(auth_str).decode('ascii'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 403,
                         'Forbidden for non-administrators.')

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
        auth_str = 'admin@example.com:test'.encode('ascii')
        headers.add('Authorization', 'Basic ' + base64.b64encode(auth_str).decode('ascii'))

        response = self.client.post(TelegramUpdates.URL_SET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 200,
                         'Only users with Permission.ADMINISTER have access'
                         'to a sethook view')

        response_json = json.loads(response.data)
        self.assertTrue(response_json['ok'] is False)
        self.assertEqual(response_json['error_code'], 400,
                         'Webhook requires HTTPS url, otherwise error 400 returned')
        self.assertEqual(response_json['url'], url_for('webhook.handle_webhook', _external=True),
                         'Setting Webhook url by the authorized user should return url'
                         'of the handle_webhook view')

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
        auth_str = 'admin@example.com:test'.encode('ascii')
        headers.add('Authorization', 'Basic ' + base64.b64encode(auth_str).decode('ascii'))

        response = self.client.post(TelegramUpdates.URL_UNSET_WEBHOOK,
                                    data=json.dumps({}),
                                    follow_redirects=True,
                                    headers=headers)

        self.assertEqual(response.status_code, 200,
                         'Only users with Permission.ADMINISTER have access'
                         'to a sethook view')

        response_json = json.loads(response.data)
        self.assertEqual(response_json['url'], '',
                         'Unsetting Webhook url by the authorized user should return empty url')

    def test_sethook_finish(self):
        self.fail('Finish tests!')