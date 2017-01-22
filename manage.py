#!/usr/bin/env python

"""
Entry point of the PilosusBot application
"""

import os

from PilosusBot import create_app, db
from PilosusBot.models import User, Role, Permission, Language, Sentiment

from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from dotenv import load_dotenv

# load env variables from `.env` file, like Heroku does
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Permission=Permission,
                Language=Language, Sentiment=Sentiment)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='PilosusBot/*')
    COV.start()


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def initialize():
    """Create all databases, initialize migration scripts before deploying."""
    from flask_migrate import init
    db.create_all()
    init()


@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import migrate, upgrade
    from PilosusBot.models import Role, User, Language
    from PilosusBot.utils import download_polyglot_dicts

    # generate an initial migration
    migrate()

    # migrate database to latest revision
    upgrade()

    # insert roles
    Role.insert_roles()

    # create admin
    User.add_admin()

    # insert languages
    Language.insert_basic_languages()

    # download third-party files needed for the app
    download_polyglot_dicts()

if __name__ == '__main__':
    manager.run()
