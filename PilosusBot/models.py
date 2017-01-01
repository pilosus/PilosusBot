import hashlib
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
from .exceptions import ValidationError
from flask_login import UserMixin, AnonymousUserMixin
from . import db, login_manager
from .utils import generate_password


class Permission:
    """Permission for App's users.

    READ:
        - default, no rights

    MODERATE:
        - add/update items to dictionary

    ADMINISTER:
        - god mode enabled!

    """
    READ = 0x01
    MODERATE = 0x02
    ADMINISTER = 0x04


class Role(db.Model):
    """
    Each user assigned to a role. Role defined with permissions.
    """
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.READ, True),
            'Moderator': (Permission.READ |
                       Permission.MODERATE, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    """
    App's User.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    invited = db.Column(db.Boolean)
    avatar_hash = db.Column(db.String(32))
    sentiments = db.relationship('Sentiment', backref='author', lazy='dynamic')

    def suspend(self):
        suspended = Role.query.filter(Role.name == 'User').first()
        self.role = suspended
        db.session.add(self)
        return True

    @staticmethod
    def add_admin():
        """Create app's administrator.

        Roles should be inserted to the database prior to creation of
        the administrator user.
        """
        import random
        import string

        admin_role = Role.query.filter_by(permissions=0xff).first()
        admin = User.query.filter_by(email=current_app.config['APP_ADMIN_EMAIL']).first()
        if not admin:
            admin_user = User(email=current_app.config['APP_ADMIN_EMAIL'],
                              username=current_app.config['APP_ADMIN_NAME'],
                              password=generate_password(10),
                              role=admin_role,
                              confirmed=True)
            db.session.add(admin_user)
            db.session.commit()

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        writer_role = Role.query.filter_by(name='Writer').first()
        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     role=writer_role,
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['APP_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_invite_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'accept_invite': self.id})

    def accept_invite(self, token, username, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception:
            return False
        if data.get('accept_invite') != self.id:
            return False
        self.confirmed = True
        self.username = username
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def has_role(self, role_name):
        return self.role.name == role_name

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

    def has_role(self, role_name):
        return False

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Language(db.Model):
    """
    Language codes in compliance with ISO 639-1 standard.
    """
    __tablename__ = 'languages'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(2), index=True, unique=True)
    name = db.Column(db.String(30), nullable=True)
    sentiments = db.relationship('Sentiment', backref='language', lazy='dynamic',
                                 cascade='all, delete-orphan')

    @staticmethod
    def insert_basic_languages():
        langs = current_app.config['APP_LANGUAGES']
        for l in langs:
            lang = Language.query.filter_by(code=l).first()
            if lang is None:
                lang = Language(code=l)
                db.session.add(lang)
        db.session.commit()


class Sentiment(db.Model):
    """
    Sentiment with given polarity (is_negative).

    If is_negative True, then sentiment is negative (polarity is -1).
    Else if is_negative False, then sentiment is positive (polarity is +1).
    Else if is_negative is None, then sentiment is neutral (polarity 0).
    """
    __tablename__ = 'sentiments'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    score = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            user = User.query.offset(randint(0, user_count - 1)).first()
            p = Sentiment(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                          timestamp=forgery_py.date.date(True),
                          author=user,
                          language='en',
                          )
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = current_app.config['APP_ALLOWED_TAGS']
        allowed_attrs = current_app.config['APP_ALLOWED_ATTRIBUTES']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=allowed_attrs, strip=True))

    def to_json(self):
        json_sentiment = {
            #'url': url_for('api.get_post', id=self.id, _external=True), # TODO
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_sentiment

    @staticmethod
    def from_json(json_sentiment):
        body = json_sentiment.get('body')
        if body is None or body == '':
            raise ValidationError('sentiment does not have a body')
        return Sentiment(body=body)

    def __repr__(self):
        return '<Sentiment %r>' % self.body

db.event.listen(Sentiment.body, 'set', Sentiment.on_changed_body)

