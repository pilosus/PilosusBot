#!/usr/bin/env python

import os
from dotenv import load_dotenv
from collections import namedtuple

# load env variables from `.env` file, like Heroku does
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Base configuration options.
    """
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Mb
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY')

    INDICO_TOKEN = os.environ.get('INDICO_TOKEN')
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    TELEGRAM_URL = "https://api.telegram.org/bot{key}/".\
        format(key=TELEGRAM_TOKEN)

    SERVER_PUBLIC_KEY = os.environ.get('SERVER_PUBLIC_KEY', None)
    SERVER_MAX_CONNECTIONS = os.environ.get('SERVER_MAX_CONNECTIONS') or 40

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT', 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    CELERY_RESULT_BACKEND = os.environ.get('CELERY_BROKER_URL')
    CELERY_BROKER_URL = os.environ.get('CELERY_RESULT_BACKEND')
    CELERY_INSTEAD_THREADING = os.environ.get('CELERY_INSTEAD_THREADING', None)

    DEQUE_HOST = os.environ.get('DEQUE_HOST', 'localhost')
    DEQUE_PORT = os.environ.get('DEQUE_PORT', 6379)
    DEQUE_KEY = os.environ.get('DEQUE_KEY', 'UpdateIDs')
    DEQUE_MAX_LEN = os.environ.get('DEQUE_MAX_LEN') or 20

    APP_NAME = 'PilosusBot'
    APP_ADMIN_EMAIL = os.environ.get('APP_ADMIN_EMAIL')
    APP_ADMIN_NAME = os.environ.get('APP_ADMIN_NAME')
    APP_REGISTRATION_OPEN = os.environ.get('APP_REGISTRATION_OPEN', False)
    APP_ITEMS_PER_PAGE = os.environ.get('APP_ITEMS_PER_PAGE', 20)
    APP_MAIL_SUBJECT_PREFIX = os.environ.get('APP_MAIL_SUBJECT_PREFIX') or APP_NAME
    APP_MAIL_SENDER = '{0} Mailer <{1}>'.format(APP_NAME, MAIL_USERNAME)

    APP_LANGUAGES = ['ru', 'de', 'en', 'fr']
    APP_LANG_FALLBACK = 'ru'
    APP_ALLOWED_TAGS = ['b', 'strong', 'i', 'a', 'code', 'pre']
    APP_ALLOWED_ATTRIBUTES = {'a': ['href']}

    # access named tuple like this: APP_SCORE_LEVELS[0.5].desc
    # desc - description, css - css class
    Score = namedtuple('Score', ['desc', 'css'])
    APP_SCORE_LEVELS = {0.0: Score('Very negative', 'danger'),
                        0.25: Score('Negative', 'warning'),
                        0.375: Score('Slightly negative', 'warning'),
                        0.5: Score('Neutral', 'default'),
                        0.625: Score('Slightly positive', 'info'),
                        0.75: Score('Positive', 'info'),
                        1.0: Score('Very positive', 'success'),
                        }

    APP_UPDATE_TEXT_THRESHOLD_LEN = os.environ.get('APP_UPDATE_TEXT_THRESHOLD_LEN') or 100

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """
    Development server configuration.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    """
    Testing server configuration.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """
    Production-ready configuration.
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data.sqlite')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.PILI_MAIL_SENDER,
            toaddrs=[cls.PILI_ADMIN],
            subject=cls.PILI_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    """
    Heroku Platform configufation.
    """
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


class UnixConfig(ProductionConfig):
    """
    Unix server configuration.
    """
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        ## log to syslog
        # write to /var/log/messages
        # can be configured to write to a separate log file
        # see docs
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'unix': UnixConfig,

    'default': DevelopmentConfig,
}

# env var FLASK_CONFIG should be set to one of these options,
# otherwise DevelopmentConfig is loaded
