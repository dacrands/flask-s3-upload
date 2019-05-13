import re
import os
import boto3
from functools import wraps
from botocore.exceptions import ClientError
from flask import render_template, flash, redirect, url_for, request, jsonify, render_template
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename

from app import app, db
from app.models import User, File
from app.email import auth_email, reset_email


# CONSTANTS
MIN_USERNAME_LEN = 6
MAX_USERNAME_LEN = 20
MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 30
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'xlsx'])


# Helper Functions
def allowed_file(filename):
    """
    Makes sure the file has a permitted extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """
    temp auth middleware until resolve https redirect with `login_required` from flask-login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if not app.debug:
                return redirect(url_for('login', next=request.url, _scheme='https', _external='true'))                
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# S3 Instances
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#          ROUTES
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.route('/')
@login_required
def index():
    return jsonify({
        'msg': 'This is a restricted page! {}'
        .format(current_user)
    })

#
# AUTH VIEWS
# --------------------------------------------------------- 
# Views for user `registration`, `verification`, `login`, `logout`,
# `deleting account`
# --------------------------------------------------------- 
#
@app.route('/verify')
def verify():
    """
    Verifies user token, redirects if token is invalid
    """
    token = request.args.get('token')
    if token:
        user_id = User.verify_email_token(token)
        if not user_id:
            flash('That token is invalid. It may have expired. Please request a new one.')
            return redirect(url_for('index'))        
        user = User.query.get(user_id)
        user.is_verified = True
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Logs in user with valid credentials.

    If the user is not verified, 
    the user will be sent another email with a new token.
    """
    if request.method == 'POST':
        # Make sure 
        try:
            username = request.form['username']
            password = request.form['password']
        except:
            return jsonify({'err': 'Missing form information'}), 400

        # Find the user
        user = User.query.filter_by(username=username).first()

        # If the user doesn't exist, or invalid password,
        # send back 401, invalid params
        if (not user) or (not user.check_password(password)):
            return jsonify({'err': 'Invalid username or password'}), 401

        # If the user is not verified, send a new email
        if not user.is_verified:
            token = user.get_email_token()
            auth_email('welcome@justfiles.com',
                   'Verify Your Account!',
                   user.email,
                   render_template('email/verify.html', token=token))
            return jsonify({'err': 'Please verify your account. We just sent another email'}), 401

        login_user(user)
        return jsonify({'username': current_user.username, 'msg': 'Logged in'})

    return jsonify({'err': 'Please log in'}), 403


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'msg': 'Logged out'})


@app.route('/register', methods=['GET', 'POST'])
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
        except:
            return jsonify({'err': 'Missing part of your form'}), 400

        # TODO email validation
        user_exists = User.query.filter_by(username=username).first(
        ) or User.query.filter_by(email=user_email).first()
        if user_exists:
            return jsonify({'err': 'Username or email already exists'}), 400

        if (len(username) <= 8) or (len(username) >= 20):
            return jsonify(
                {'err': 'Username must be between {0} and {1} characters'.format(MIN_USERNAME_LEN, MAX_USERNAME_LEN)}), 400

        password_len = max(len(password1), len(password2))
        if (password_len < 8) or (password_len > 20):
            return jsonify({'err': 'Password  must be between {0} and {1} characters'.format(MIN_PASSWORD_LEN, MAX_PASSWORD_LEN)}), 400

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

        s3.Bucket(app.config['S3_BUCKET']).put_object(Key=user.username + '/')

    return jsonify({'msg': 'User added'})


@app.route('/user/delete', methods=['DELETE'])
@login_required
def delete_user():
    """
    Deletes a user and the user's S3 buckets
    """
    db.session.delete(current_user)
    db.session.commit()

    s3_client.delete_object(
        Bucket=app.config['S3_BUCKET'], Key=current_user.username + '/')
    return jsonify({'msg': 'User deleted'})
 
#
# S3 VIEWS
# --------------------------------------------------------- 
# Views for GET, POST, DELETE, PATCH file(s)
# --------------------------------------------------------- 
@app.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    """
    Uploads a new file if the filename does not exist
    in the current users filenames.

    """
    if request.method == 'POST':

        try:
            file_text = request.form['text']
            file = request.files['file']
            file_date = request.form['date']
        except:
            return jsonify({'msg': 'Missing part of your form'}), 400

        if file.filename == '':
            return jsonify({'msg': 'missing file name'}), 400

        # Must secure filename before checking if it already exists
        filename = secure_filename(file.filename)
        file_names = [file.name for file in current_user.files]
        
        if filename in file_names:
            return jsonify({'msg': 'You already have a file with that name. File names must be unique'}), 400

        if len(file_text) > 130:
            return jsonify({'msg': 'File description must be less than 130 characters'}), 400

        if not allowed_file(file.filename):
            return jsonify({'msg': 'Invalid file type'}), 400

        if file:            
            key_str = "{0}/{1}".format(current_user.username, filename)
            s3.Bucket(app.config['S3_BUCKET']).put_object(
                Key=key_str,
                Body=request.files['file'].stream.read()
            )
            # Add a new file
            new_file = File(name=filename, body=file_text, date=file_date,
                            key=key_str, author=current_user)
            db.session.add(new_file)
            db.session.commit()

            return jsonify({'msg': 'Uploaded {0}'.format(filename)})

        return jsonify({'msg': 'Something went wrong'}), 400

    user_files = [{'name': file.name, 'body': file.body, "id": file.id}
                  for file in current_user.files]
    user_files.reverse()

    return jsonify({'files': user_files})


@app.route('/files/<file_id>')
@login_required
def file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    try:
        res_object = s3_client.get_object(
            Bucket=app.config['S3_BUCKET'],
            Key=file.key
        )
    except ClientError:
        return jsonify({'msg': 'File note in your folder'})

    url = s3_client.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': app.config['S3_BUCKET'],
            'Key': file.key,
        }
    )
    file_dict = {
        'url': url,
        'body': file.body,
        'date': file.date,
        'size': res_object['ResponseMetadata']['HTTPHeaders']['content-length'],
    }

    return jsonify({'file': file_dict})


@app.route('/files/<file_id>/edit', methods=['PATCH'])
@login_required
def edit_file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    if request.method == 'PATCH':
        try:
            file_text = request.form['body']
        except:
            return jsonify({'err': 'Missing part of your form'}), 400

        if len(file_text) > 130:
            return jsonify({'msg': 'File description must be less than 140 characters'}), 400

        file.body = file_text
        db.session.commit()
        return jsonify({'msg': 'Filed edited!'})

    return jsonify({'err': 'You can not do that'})


@app.route('/files/<file_id>/delete', methods=['DELETE'])
@login_required
def delete_file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    try:
        res_object = s3_client.delete_object(
            Bucket=app.config['S3_BUCKET'],
            Key=file.key
        )
    except ClientError:
        return jsonify({'msg': 'File note in your folder'})

    db.session.delete(file)
    db.session.commit()
    return jsonify({'msg': 'File removed'})
