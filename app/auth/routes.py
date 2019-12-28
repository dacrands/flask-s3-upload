import boto3
from flask import current_app, render_template, flash, redirect, \
                    url_for, request, jsonify
from flask_login import login_user, logout_user, current_user

from app import db
from app.models import User
from app.auth import bp
from app.auth.email import auth_email, reset_email
from app.utils import login_required

s3 = boto3.resource('s3')

# Form Validator Constants
MIN_USERNAME_LEN = 6
MAX_USERNAME_LEN = 20
MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 30


@bp.route('/verify')
def verify():
    """
    Verifies user token, redirects if token is invalid
    """
    token = request.args.get('token')
    if token:
        user_id = User.verify_email_token(token)
        if not user_id:
            flash('That token is invalid. It may have expired. \
            Please request a new one.')
            return redirect(url_for('auth.index'))
        user = User.query.get(user_id)
        user.is_verified = True
        db.session.commit()
        login_user(user)
        return redirect(url_for('auth.index'))
    return redirect(url_for('auth.index'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Logs in user with valid credentials.

    If the user is not verified,
    the user will be sent another email with a new token.
    """
    if request.method == 'POST':
        # Check for missing form info
        try:
            username = request.form['username']
            password = request.form['password']
        except KeyError:
            return jsonify({'err': 'Missing form information'}), 400

        # Find the user
        user = User.query.filter_by(username=username).first()

        # Check if user exists or provided invalid PW
        if (not user) or (not user.check_password(password)):
            return jsonify({'err': 'Invalid username or password'}), 400

        # If the user is not verified, send a new email
        if not user.is_verified:
            token = user.get_email_token()
            auth_email('welcome@justfiles.com',
                       'Verify Your Account!',
                       user.email,
                       render_template('email/verify.html', token=token))
            return jsonify({
                'err': 'Please verify your account. We just sent another email'
            }), 401

        login_user(user)
        return jsonify({'username': current_user.username, 'msg': 'Logged in'})

    return jsonify({'err': 'Please log in'}), 401


@bp.route('/logout')
@login_required
def logout():
    """
    Log the user out
    """
    logout_user()
    return jsonify({'msg': 'Logged out'})


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registers a new user if the current username
    does not exist and sends verification email.
    """
    if request.method == 'POST':
        try:
            username = request.form['username']
            user_email = request.form['email']
            password1 = request.form['password1']
            password2 = request.form['password2']
        except KeyError:
            return jsonify({'err': 'Missing part of your form'}), 400

        user_exists = User.query.filter_by(username=username).first(
        ) or User.query.filter_by(email=user_email).first()
        if user_exists:
            return jsonify({'err': 'Username or email already exists'}), 400

        if (len(username) <= MIN_USERNAME_LEN) or \
                (len(username) >= MAX_USERNAME_LEN):
            return jsonify({
                'err': 'Username must be between {0} and {1} characters'
                .format(MIN_USERNAME_LEN, MAX_USERNAME_LEN)
            }), 400

        password_len = max(len(password1), len(password2))
        if (password_len < MIN_PASSWORD_LEN) or \
                (password_len > MAX_PASSWORD_LEN):
            return jsonify({
                'err': 'Password  must be between {0} and {1} characters'
                .format(MIN_PASSWORD_LEN, MAX_PASSWORD_LEN)
            }), 400

        if password1 != password2:
            return jsonify({'err': 'Passwords do not match'}), 400

        user = User(username=username, email=user_email)
        user.set_password(password1)
        db.session.add(user)
        db.session.commit()

        token = user.get_email_token()
        auth_email('welcome@justfiles.com',
                   'Verify Your Account!',
                   user.email,
                   render_template('email/verify.html', token=token))

        s3.Bucket(current_app.config['S3_BUCKET']
                  ).put_object(Key=user.username + '/')

    return jsonify({'msg': 'User added'})


@bp.route('/user/delete', methods=['DELETE'])
@login_required
def delete_user():
    """
    Deletes a user and the user's S3 buckets
    """
    db.session.delete(current_user)
    db.session.commit()

    s3_client.delete_object(
        Bucket=current_app.config['S3_BUCKET'], Key=current_user.username + '/')
    return jsonify({'msg': 'User deleted'})
