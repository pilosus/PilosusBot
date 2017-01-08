import random
import sys
import unittest
from flask import current_app, json, url_for
#from flask_testing import TestCase
from PilosusBot import create_app, db
from PilosusBot.models import Role, Language


"""
Unit-/integrational-tests for webhook blueprint

See more about unittesting in Flask applications:
flask.pocoo.org/docs/latest/testing/
http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.Client
https://pythonhosted.org/Flask-Testing/
"""


class TelegramUpdates(object):
    URL = url_for('webhook.handle_webhook')
    HEADERS = {'Content-Type': 'application/json'}
    UPDATE_ID = random.randint(100, sys.maxsize)
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
            "text": "A" * (current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] - 1)
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
            "text": "A" * (current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] + 1)
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
            "text": "A" * (current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] + 1)
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
            "text": "A" * (current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] + 1)
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
            "text": "A" * (current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] + 1)
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

    def create_app(self):
        """Mandatory method for Flask-Testing returning app instance"""
        return create_app('testing')

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_handle_webhook(self):
        response_not_allowed = self.client.get(TelegramUpdates.URL)
        self.assertTrue(response_not_allowed.status_code == 405,
                        'GET method not allowed, only POST')

        response_to_empty_json_posted = self.client.post(TelegramUpdates.URL,
                                                         data=json.dumps(TelegramUpdates.EMPTY),
                                                         follow_redirects=True,
                                                         headers=TelegramUpdates.HEADERS)

        self.assertTrue(response_to_empty_json_posted.status_code == 200,
                        'POST request with empty JSON payload did not return code 200')

        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_to_empty_json_posted.data,
                         'POST request with empty JSON payload did not return back empty JSON')

        response_bad_id_bad_text = self.client.post(TelegramUpdates.URL,
                                                    data=json.dumps(TelegramUpdates.TEXT_BAD_ID_BAD_TEXT),
                                                    follow_redirects=True,
                                                    headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_bad_id_bad_text.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_bad_id_bad_text.data,
                         'Update with bad reply_message_id and bad text length did not return empty JSON')

        response_ok_id_bad_text = self.client.post(TelegramUpdates.URL,
                                                   data=json.dumps(TelegramUpdates.TEXT_OK_ID_BAD_TEXT),
                                                   follow_redirects=True,
                                                   headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_ok_id_bad_text.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_ok_id_bad_text.data,
                         'Update with bad text length did not return empty JSON')

        response_bad_id_ok_text = self.client.post(TelegramUpdates.URL,
                                                   data=json.dumps(TelegramUpdates.TEXT_BAD_ID_OK_TEXT),
                                                   follow_redirects=True,
                                                   headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_bad_id_ok_text.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_bad_id_ok_text.data,
                         'Update with bad reply_message_id did not return empty JSON')

        response_malformed_msg = self.client.post(TelegramUpdates.URL,
                                                  data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_MESSAGE),
                                                  follow_redirects=True,
                                                  headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_malformed_msg.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_malformed_msg.data,
                         'Malformed Update did not return empty JSON')

        response_malformed_chat = self.client.post(TelegramUpdates.URL,
                                                   data=json.dumps(TelegramUpdates.TEXT_MALFORMED_NO_CHAT),
                                                   follow_redirects=True,
                                                   headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_malformed_chat.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_malformed_chat.data,
                         'Malformed Update with no chat did not return empty JSON')

        response_same_update_id = self.client.post(TelegramUpdates.URL,
                                                   data=json.dumps(TelegramUpdates.TEXT_SAME_UPDATE_ID),
                                                   follow_redirects=True,
                                                   headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_same_update_id.status_code == 200)
        self.assertEqual((json.dumps({}) + '\n').encode('utf-8'),
                         response_same_update_id.data,
                         'Update with update_id already registered did not return empty JSON')

        response_ok_id_ok_text = self.client.post(TelegramUpdates.URL,
                                                  data=json.dumps(TelegramUpdates.TEXT_OK_ID_OK_TEXT),
                                                  follow_redirects=True,
                                                  headers=TelegramUpdates.HEADERS)
        self.assertTrue(response_ok_id_ok_text.status_code == 200)
        self.assertNotEqual((json.dumps({}) + '\n').encode('utf-8'),
                            response_ok_id_ok_text.data,
                            'Correct Update did not return valid JSON')

        #
        self.fail('select_db_sentiment celery task line 100 fails if there are no sentiments to choose from!')