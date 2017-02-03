import unittest
from flask import url_for
from PilosusBot import create_app, db
from PilosusBot.models import Language, Role
from PilosusBot.info.errors import forbidden, page_not_found, \
    internal_server_error
from werkzeug.datastructures import Headers


class InfoTestCase(unittest.TestCase):
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

    def test_index_view(self):
        response = self.client.get(url_for('info.index'))
        self.assertTrue(response.status_code == 200,
                        'Failed to render index page for info view')

    def test_info_custom_errors_returning_json(self):
        error_403_msg, error_403_code = forbidden('foo')
        self.assertIn('Forbidden', error_403_msg)
        self.assertEqual(error_403_code, 403)

        error_404_msg, error_404_code = page_not_found('bar')
        self.assertIn('Page Not Found', error_404_msg)
        self.assertEqual(error_404_code, 404)

        error_500_msg, error_500_code = internal_server_error('baz')
        self.assertIn('Internal Server Error', error_500_msg)
        self.assertEqual(error_500_code, 500)

    def test_info_page_not_found(self):
        headers = Headers()
        headers.add('Accept', 'application/json')

        response = self.client.get('/a',
                                   content_type='application/json',
                                   follow_redirects=True,
                                   headers=headers)

        self.assertEqual(response.status_code, 404)

    def test_info_method_not_allowed(self):
        headers = Headers()
        headers.add('Accept', 'application/json')

        response = self.client.put('/',
                                   content_type='application/json',
                                   follow_redirects=True,
                                   headers=headers)

        self.assertEqual(response.status_code, 405,
                         'Failed to return Method Not Allowed error'
                         'when PUT method invoked for GET only view')
