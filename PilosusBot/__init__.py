from flask import Flask
from flask_bootstrap import Bootstrap
from flask_bootstrap import WebCDN
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown
from flask_wtf.csrf import CsrfProtect
from config import config, Config
from celery import Celery

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()
csrf = CsrfProtect()
celery = Celery(__name__, backend=Config.CELERY_RESULT_BACKEND,
                broker=Config.CELERY_BROKER_URL)

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'


def create_app(config_name):
    app = Flask(__name__)
    #template_filters = {name: function
    #                    for name, function in getmembers(jinja_filters)
    #                    if isfunction(function)}
    #app.jinja_env.filters.update(template_filters)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)
    csrf.init_app(app)
    celery.conf.update(app.config)

    # change jquery version with another CDN
    app.extensions['bootstrap']['cdns']['jquery'] = WebCDN(
        '//cdnjs.cloudflare.com/ajax/libs/jquery/2.1.1/'
    )

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        sslify = SSLify(app)


    # info pages
    from .info import info as info_blueprint
    app.register_blueprint(info_blueprint)

    # bot main logic
    from .webhook import webhook as webhook_blueprint
    app.register_blueprint(webhook_blueprint, url_prefix='/webhook')

    # user authentication/registration
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # administration dashboard
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # TODO
    #from .api_1_0 import api as api_1_0_blueprint
    #app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    return app
