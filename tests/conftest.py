import os
import pytest
import boto3
from moto import mock_s3

from app import create_app, db
from app.models import User

basedir = os.path.abspath(os.path.dirname(__file__))

TEST_DB_PATH = os.path.join(basedir, 'test_app.db')
TEST_DB_URI = 'sqlite:///' + TEST_DB_PATH

TEST_S3_BUCKET = 'somebucket'


def create_user(username, password, is_verified=True):
    try:
        user = User(username=username)
        user.set_password(password)
        user.is_verified = is_verified
        return user

    except Exception as err:
        print("Unexpected error creating User: ", err)
        raise


def add_user_to_db(user):
    try:
        db.session.add(user)
        db.session.commit()

    except Exception as err:
        print("Unexpected error adding User to db: ", err)
        raise


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.yield_fixture(scope="function")
def s3_client(aws_credentials):
    mocks3 = mock_s3()
    mocks3.start()

    client = boto3.client("s3")

    yield client

    mocks3.stop()


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=TEST_DB_URI,
        S3_BUCKET=TEST_S3_BUCKET
    )

    with app.app_context() as app_context:
        db.create_all()
        app_context.push()

    yield app

    db.session.remove()
    db.drop_all()
    app_context.pop()
    os.remove(TEST_DB_PATH)


@pytest.fixture
def client(app):
    return app.test_client()
