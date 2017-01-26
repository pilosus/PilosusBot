import unittest
from PilosusBot import create_app, db, celery
from PilosusBot.models import Role, Language
from PilosusBot.tasks import celery_chain, assess_message_score, \
    select_db_sentiment, send_message_to_chat


class UtilsTestCase(unittest.TestCase):
    def setUp(self):
        """Method called before each unit-test"""
        # create app, set TESTING flag to disable error catching
        self.app = create_app('testing')

        # push app context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # make celery tasks eager
        # celery emulates the API and behavior of AsyncResult,
        # except the result is already evaluated.
        celery.conf.update(CELERY_ALWAYS_EAGER=True)

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

    def test_finish(self):
        self.fail('Finish tests!')
