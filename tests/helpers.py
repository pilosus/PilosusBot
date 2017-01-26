import base64
import forgery_py
import math
import random
import sys
from flask import url_for, current_app


class TelegramUpdates(object):
    URL_HANDLE_WEBHOOK = url_for('webhook.handle_webhook', _external=True)
    URL_SET_WEBHOOK = url_for('webhook.set_webhook', action='set', _external=True)
    URL_UNSET_WEBHOOK = url_for('webhook.set_webhook', action='unset', _external=True)
    HEADERS = {'Content-Type': 'application/json'}
    UPDATE_ID = random.randint(100, sys.maxsize)
    TEXT_BIT = forgery_py.lorem_ipsum.sentences(5)[:current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN']]
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


class MockResponse(object):
    """
    Mimic requests.post response with status_code attribute and json() method
    """
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class HTTP(object):
    @staticmethod
    def basic_auth(login, password):
        """
        Return HTTP basic authentication string encoded.
        :param login: str (login or email)
        :param password:  str
        :return: tuple of two
        """
        auth_str = '{login}:{password}'.format(login=login, password=password).encode('ascii')
        auth_str_b64_encoded = base64.b64encode(auth_str).decode('ascii')
        return 'Authorization', 'Basic ' + auth_str_b64_encoded

    @staticmethod
    def mocked_requests_post(url, json, files, timeout):
        """
        The method is called with the same arguments that original requests.post is called.

        Set status code as an attribute to mimic requests.post API.
        Given JSON extended with the keys Telegram uses in reply.
        """
        # this is Python 3.5+
        # we need to extend
        data = {**json, **{'ok': False, 'error_code': 400, 'description': None}}
        return MockResponse(data, 200)

    @staticmethod
    def mocked_indicoio():
        pass
