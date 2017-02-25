##########
PilosusBot
##########

PilosusBot is a `Telegram bot`_ written in Python Flask. It reads Telegram chat messages,
calculates sentiment scores (polarity score) and replies with the randomly selected message
of the matching polarity.

.. contents:: Table of Contents

================
About PilosusBot
================

-----
Stack
-----

Application is based on **Flask**, a light-weight Python web framework
that gets use of Werkzeug toolkit and Jinja2 template engine. Although
Flask works fine with both Python 2 and 3, PilosusBot's written with
**Python 3** in focus.

Database-agnostic, application uses **SQLAlchemy** ORM, which enables
user to choose between DBMS ranging from a simple SQLite to an
enterprise solution of user's choice.

Asynchronous tasks tackled with **Celery** distributed task queue,
which is to be used with a message broker
**RabbitMQ**.

**Redis** is used for bounded in-memory queue for tracking messages
processed so far.

The app relies on `indicoio`_ API for sentiment analysis as well as
Telegram Bot API. It also uses `Sentry`_ for real-time error tracking.
Make sure you get API tokens before you started app's deployment.

As a fallback for ``indicoio`` API (paid service) app uses `polyglot`_
package for natural language processing. Installing it may be tricky
requiring ``icu`` and ``libicu-devel`` packages being installed to
your OS.

==================
Deployment & Usage
==================

Based on `Pili App`_, PilosusBot follows its same steps of deployment.
``manage.py`` options are basically the same as in ``Pili`` too.
Please, refer to ``Pili``'s documentation for help.

---------
.env file
---------

``.env`` file is kept under project's root directory. It's an entry point of app's
configuration and deployment. Standard ``.env`` file may look like this::

  ### Testing/Development/Production switch
  FLASK_CONFIG=production

  ### Flask Variables
  SECRET_KEY=...
  DATABASE_URL=postgresql+psycopg2://user:passwd@your_db_server:5432/your_prod_db
  TEST_DATABASE_URL=postgresql+psycopg2://user:passwd@127.0.0.1:5432/your_testing_db

  ### Server
  SERVER_MAX_CONNECTIONS=30


  ### Mail server
  MAIL_USERNAME=...
  MAIL_PASSWORD=...
  MAIL_SERVER=...
  MAIL_PORT=587
  MAIL_USE_TLS=True

  ### Celery
  CELERY_BROKER_URL=amqp://guest@localhost//
  CELERY_RESULT_BACKEND=rpc://
  CELERY_QUEUE_ASSESS=assess
  CELERY_QUEUE_SELECT=select
  CELERY_QUEUE_SEND=send

  ## App
  APP_ADMIN_EMAIL=...
  APP_ADMIN_NAME=...

  ### Third-Party API
  TELEGRAM_TOKEN=...
  INDICO_TOKEN=...
  SENTRY_DSN_SECRET=...
  SENTRY_DSN_PUBLIC=...


See also ``config.py`` for more configuration options.

=======
Credits
=======

The app partly relies on Miguel Grinberg's `Flasky`_ code (e.g. authentication module and DB models),
which is a Flask application developed as an example for the excellent `Flask Web Development`_ book.
Go grab your copy of the book, it's absolutely worth it!

.. _Flasky: https://github.com/miguelgrinberg/flasky
.. _Flask Web Development: http://shop.oreilly.com/product/0636920031116.do
.. _Telegram bot: https://core.telegram.org/bots
.. _Pili App: https://github.com/pilosus/pili
.. _indicoio: https://indico.io/
.. _polyglot: http://polyglot.readthedocs.io/en/latest/
.. _Sentry: https://sentry.io/

=======
License
=======

See `LICENSE` file.
