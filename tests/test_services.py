import boto3

import pytest

from app import app
from app.email import auth_email, reset_email


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
