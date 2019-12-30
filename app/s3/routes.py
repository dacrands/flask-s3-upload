import re
import os
import boto3
from botocore.exceptions import ClientError
from flask import current_app, redirect, url_for, request, jsonify
from flask_login import current_user
from werkzeug.utils import secure_filename

from app import db
from app.auth import bp
from app.models import File
from app.utils import login_required, allowed_file


# S3 Instances
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')


@bp.route('/')
@login_required
def index():
    return jsonify({
        'msg': 'This is a restricted page! {}'
        .format(current_user)
    })


@bp.route('/files', methods=['GET', 'POST'])
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
        except KeyError:
            return jsonify({'msg': 'Missing part of your form'}), 400

        if file.filename == '':
            return jsonify({'msg': 'missing file name'}), 400

        # Must secure filename before checking if it already exists
        filename = secure_filename(file.filename)
        file_names = [file.name for file in current_user.files]

        if filename in file_names:
            return jsonify({
                'msg': 'You already have a file with that name. \
                        File names must be unique'
            }), 400

        if len(file_text) > 130:
            return jsonify({
                'msg': 'File description must be less than 130 characters'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({'msg': 'Invalid file type'}), 400

        if file:
            key_str = "{0}/{1}".format(current_user.username, filename)
            s3.Bucket(current_app.config['S3_BUCKET']).put_object(
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


@bp.route('/files/<file_id>')
@login_required
def file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    try:
        res_object = s3_client.get_object(
            Bucket=current_app.config['S3_BUCKET'],
            Key=file.key
        )
    except ClientError:
        return jsonify({'msg': 'File not in your folder'})

    url = s3_client.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': current_app.config['S3_BUCKET'],
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


@bp.route('/files/<file_id>/edit', methods=['PATCH'])
@login_required
def edit_file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    if request.method == 'PATCH':
        try:
            file_text = request.form['body']
        except KeyError:
            return jsonify({'err': 'Missing part of your form'}), 400

        if len(file_text) > 130:
            return jsonify({
                'msg': 'File description must be less than 140 characters'
            }), 400

        file.body = file_text
        db.session.commit()
        return jsonify({'msg': 'Filed edited!'})

    return jsonify({'err': 'You can not do that'})


@bp.route('/files/<file_id>/delete', methods=['DELETE'])
@login_required
def delete_file(file_id):
    file = File.query.filter_by(id=file_id).first()
    if not file:
        return jsonify({'msg': 'File does not exist'})

    try:
        res_object = s3_client.delete_object(
            Bucket=current_app.config['S3_BUCKET'],
            Key=file.key
        )
    except ClientError:
        return jsonify({'msg': 'File note in your folder'})

    db.session.delete(file)
    db.session.commit()
    return jsonify({'msg': 'File removed'})
