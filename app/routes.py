import re
import os
import boto3
from botocore.exceptions import ClientError
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename

from app import app, db
from app.models import User, File

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
        return jsonify({'username': current_user.username, 'msg': 'Logged in'})

    return jsonify({'msg': 'Please log in'}), 403


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
    '''
    Expects three form values:
    - File Info
    - File  
    '''
    if request.method == 'POST':
        try:
            file_text = request.form['text']
            file = request.files['file']
        except:
            return jsonify({'msg': 'Missing part of your form'})

        if file.filename == '':
            return jsonify({'msg': 'missing file name'})

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            key_str = "{0}/{1}".format(current_user.username, filename)
            s3.Bucket(app.config['S3_BUCKET']).put_object(
                Key=key_str,
                Body=request.files['file'].stream.read()
            )
            # ADD A NEW FILE
            new_file = File(name=filename, body=file_text,
                            key=key_str, author=current_user)
            db.session.add(new_file)
            db.session.commit()

        return jsonify({'msg': 'Uploaded {0}'.format(filename)})

    print([(file.key, file.id) for file in current_user.files])
    user_files = [{'name': file.name, 'body': file.body, "id": file.id}
                  for file in current_user.files]

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
        'size': res_object['ResponseMetadata']['HTTPHeaders']['content-length'],
        'date': res_object['ResponseMetadata']['HTTPHeaders']['last-modified'],
        'id': res_object['ResponseMetadata']['RequestId'],
    }
    
    return jsonify({'file' : file_dict})


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
