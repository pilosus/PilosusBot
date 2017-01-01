from flask import render_template, redirect, request, url_for, flash, \
    current_app
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User, Permission, Role
from ..email import send_email
from ..decorators import permission_required
from ..utils import generate_password
from .forms import LoginForm, RegistrationForm, ChangePasswordForm,\
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm,\
    InviteRequestForm, InviteAcceptForm


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('info.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    registration_open = current_app.config['APP_REGISTRATION_OPEN']
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('info.index'))
        flash('Invalid username or password.', 'warning')
    return render_template('auth/login.html', form=form,
                           registration_open=registration_open)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('info.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_app.config['APP_REGISTRATION_OPEN'] is False:
        flash('Registration for new users is by invitation only. Please contact administration.', 'info')
        return redirect(url_for('info.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        flash('Your account already confirmed.', 'warning')
        return redirect(url_for('info.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'warning')
    return redirect(url_for('info.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.', 'info')
    return redirect(url_for('info.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been updated.', 'success')
            return redirect(url_for('info.index'))
        else:
            flash('Invalid password.', 'warning')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('info.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
            flash('An email with instructions to reset your password has been '
                  'sent to you.', 'info')
        else:
            flash('No such email registered.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('info.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('info.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.', 'success')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('info.index'))
    return render_template('auth/reset_password.html', form=form)


# TODO
@auth.route('/invite', methods=['GET', 'POST'])
@permission_required(Permission.ADMINISTER)
def invite_request():
    form = InviteRequestForm()
    if form.validate_on_submit():
        role = Role.query.get_or_404(form.role.data)
        user = User(email=form.email.data,
                    password=generate_password(10),
                    invited=True,
                    role=role)
        db.session.add(user)
        db.session.commit()
        token = user.generate_invite_token()
        send_email(user.email, 'Invitation to participate',
                   'auth/email/invite', id=user.id, token=token)
        flash('An invitation has been sent by email.', 'info')
        return redirect(url_for('info.index'))
    # TODO
    page = request.args.get('page', 1, type=int)
    # find invited users, sort them so that unconfirmed comes first,
    # sort then all users by date
    pagination = User.query.order_by(User.invited).\
                 order_by(User.confirmed.asc()).\
                 order_by(User.member_since.desc()).paginate(
                     page, per_page=current_app.config['APP_ITEMS_PER_PAGE'],
                     error_out=False)
    users = pagination.items
    return render_template('auth/invite_request.html', form=form,
                           users=users, pagination=pagination)


@auth.route('/invite/<int:id>/<token>', methods=['GET', 'POST'])
def invite_accept(id, token):   
    if not current_user.is_anonymous:
        flash('Invites are for new users only.', 'warning')
        return redirect(url_for('info.index'))
    form = InviteAcceptForm()
    user = User.query.filter_by(id=id).first()
    if user is None:
        flash('You are not among the invitees.', 'danger')
        return redirect(url_for('info.index'))
    else:
        if user.confirmed:
            flash('You have previously confirmed your account. Please log in.',
                  'info')
            return redirect(url_for('auth.login'))
    if form.validate_on_submit():
        if user.accept_invite(token=token,
                              username=form.username.data,
                              new_password=form.password.data):
            flash('You have confirmed your account. Thanks!', 'success')
        else:
            flash('The confirmation link is invalid or has expired.', 'warning')
        return redirect(url_for('info.index'))
    # TODO
    return render_template('auth/invite_accept.html', form=form, user=user)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.', 'info')
            return redirect(url_for('info.index'))
        else:
            flash('Invalid email or password.', 'warning')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.', 'success')
    else:
        flash('Invalid request.', 'warning')
    return redirect(url_for('info.index'))


