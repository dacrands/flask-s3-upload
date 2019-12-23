import boto3

import pytest

from app import create_app
from app.auth.email import auth_email, reset_email


def test_send_email():
    """Test email"""
    app = create_app({'TESTING': True})
    with app.app_context() as app_context:
        app_context.push()

    auth_email_resp = auth_email('welcome@justfiles.com',
                                 'Verify Your Account!',
                                 'test@email.com',
                                 'test')

    reset_email_resp = reset_email('welcome@justfiles.com',
                                   'Verify Your Account!',
                                   'test@email.com',
                                   'test')

    app_context.pop()

    assert reset_email_resp == 202
    assert auth_email_resp == 202


def test_s3_bucket():
    """Test configured bucket exists"""

    app = create_app({'TESTING': True})

    s3 = boto3.resource('s3')
    buckets = [bucket.name for bucket in s3.buckets.all()]

    assert app.config['S3_BUCKET'] in buckets
