import re
import os
import boto3
from botocore.exceptions import ClientError
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename

from app import app, db
from app.models import User

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

MIN_USERNAME_LEN = 6
MAX_USERNAME_LEN = 20
MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 30

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
@login_required
def index():
    return jsonify({
        'msg': 'This is a restricted page! {}'
                .format(current_user.username)
        })


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Expects two form values:
    - username
    - password
    '''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
        except:
            return jsonify({'msg': 'Missing form information'})

        user = User.query.filter_by(username=username).first()

        if (not user) or (not user.check_password(password)):
            return jsonify({'msg': 'Invalid uername or password'})

        login_user(user)
        return jsonify({'msg': 'Logged in'})

    return jsonify({'msg': 'Please log in'})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'msg': 'Logged out'})


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
    Expects three form values:
    - username
    - password1
    - password2
    '''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
        except:
            return jsonify({'msg': 'Missing part of your form'})

        user = User.query.filter_by(username=username).first()
        if user:
            return jsonify({'msg': 'Username already exists'})
        if (len(username) < 8) or (len(username) > 20):
            return jsonify({'msg': 'Username must be between {0} and {1} characters'.format(MIN_USERNAME_LEN, MAX_USERNAME_LEN)})

        password_len = max(len(password1), len(password2))
        if (password_len < 8) or (password_len > 20):
            return jsonify({'msg': 'Password  must be between {0} and {1} characters'.format(MIN_PASSWORD_LEN, MAX_PASSWORD_LEN)})

        if password1 != password2:
            return jsonify({'msg': 'Passwords do not match'})

        user = User(username=username)
        user.set_password(password1)
        db.session.add(user)
        db.session.commit()

        s3.Bucket(app.config['S3_BUCKET']).put_object(Key=user.username + '/')

    return jsonify({'msg': 'User added'})


@app.route('/user', methods=['DELETE'])
@login_required
def delete_user():
    db.session.delete(current_user)
    db.session.commit()

    s3_client.delete_object(
        Bucket=app.config['S3_BUCKET'], Key=current_user.username + '/')
    return jsonify({'msg': 'User deleted'})


"""
S3 LOGIC
"""


@app.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'msg': 'missing file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'msg': 'missing file name'})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            s3.Bucket(app.config['S3_BUCKET']).put_object(
                Key="{0}/{1}".format(current_user.username, filename),
                Body=request.files['file'].stream.read()
            )
        return jsonify({'msg': 'Uploaded {0}'.format(filename)})

    files_req = s3_client.list_objects(
        Bucket=app.config['S3_BUCKET'],
        Prefix="{0}/".format(current_user.username)
    )

    # First object is empty, so index at 1
    file_urls = []
    for file in files_req['Contents'][1:]:
        url = s3_client.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': app.config['S3_BUCKET'],
            'Key': file['Key'],
            }
        )
        file_dict = {
            'name': file['Key'].split('/')[-1],
            'link': url,
        }
        file_urls.append(file_dict)

    return jsonify({'objects':file_urls})

        
@app.route('/files/<file_name>', methods=['DELETE'])
@login_required
def delete_file(file_name):
    files_req = s3_client.list_objects(
        Bucket=app.config['S3_BUCKET'],
        Prefix="{0}/".format(current_user.username)
    )
    for file in files_req['Contents']:
        if file['Key'].split('/')[-1] == file_name:
            s3_client.delete_object(
            Bucket=app.config['S3_BUCKET'], 
            Key='{0}/{1}'.format(current_user.username, file_name)
            )
            return jsonify({'msg': 'Successfully deleted {}'.format(file_name)})        
    return jsonify({'msg': 'File not found'})