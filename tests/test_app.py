import os
import tempfile
import boto3

import pytest

from app import app, db

from app.models import User
from app.email import auth_email, reset_email


@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_send_email():
    """Test email"""
    auth_email_resp = auth_email('welcome@justfiles.com',
                                 'Verify Your Account!',
                                 'test@email.com',
                                 'test')

    reset_email_resp = reset_email('welcome@justfiles.com',
                                   'Verify Your Account!',
                                   'test@email.com',
                                   'test')

    assert auth_email_resp == 202
    assert reset_email_resp == 202


def test_s3_bucket():
    """Test configured bucket exists"""
    s3 = boto3.resource('s3')
    buckets = [bucket.name for bucket in s3.buckets.all()]

    assert app.config['S3_BUCKET'] in buckets


def test_user_password():
    """
    Test new user password hash
    """
    user = User(email='someone@gmail.com', username='This is cool')
    user.set_password('password')
    assert user.check_password('password')
    assert user.password_hash != 'password'
