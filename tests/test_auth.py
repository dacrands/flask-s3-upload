import os
import tempfile
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
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=TEST_DB_URI,
        S3_BUCKET=TEST_S3_BUCKET
    )

    with app.test_client() as client:
        with app.app_context() as app_context:
            db.create_all()
            app_context.push()

            yield client

            db.session.remove()
            db.drop_all()
            app_context.pop()
            os.remove(TEST_DB_PATH)


def test_unauthorized_redirect(client):
    """Test unauthorized redirect"""

    get_index = client.get('/')
    get_files = client.get('/files')

    assert get_index.status_code == 302
    assert get_files.status_code == 302


def test_unauthorized_request(client):
    """Test unauthorized request"""

    get_index = client.get('/', follow_redirects=True)
    get_files = client.get('/files', follow_redirects=True)

    assert get_index.status_code == 401
    assert get_files.status_code == 401


def test_authorized_request(client):
    """Test authorized requests"""
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    login = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    get_index = client.get('/')
    get_files = client.get('/files')

    assert get_index.status_code == 200
    assert get_files.status_code == 200


def test_register_user(client, s3_client):
    """Test register User"""
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)

    valid_username = "test1234"
    valid_username_2 = "test4567"
    invalid_username = "shorts"

    valid_password = "ThisIsAValidPassword"
    valid_password_2 = "ThisIsAValidPassword2"
    invalid_password = "tooshort"

    valid_email = "test@email.com"
    valid_email_2 = "test2@email.com"

    # Username does not meet length requirement
    invalid_username_rv = client.post('/register', data=dict(
        username=invalid_username,
        email=valid_email_2,
        password1=valid_password,
        password2=valid_password
    ))

    assert invalid_username_rv.status_code == 400
    assert b'Username must be between' in invalid_username_rv.data

    # Password does not meet length requirement
    invalid_password_rv = client.post('/register', data=dict(
        username=valid_username,
        email=valid_email_2,
        password1=invalid_password,
        password2=invalid_password
    ))

    assert invalid_password_rv.status_code == 400
    assert b'Password  must be between' in invalid_password_rv.data

    # Passwords are valid but do not match
    mismatched_password_rv = client.post('/register', data=dict(
        username=valid_username,
        email=valid_email_2,
        password1=valid_password,
        password2=valid_password_2
    ))

    assert mismatched_password_rv.status_code == 400
    assert b'Passwords do not match' in mismatched_password_rv.data

    # Valid registration
    valid_rv = client.post('/register', data=dict(
        username=valid_username,
        email=valid_email,
        password1=valid_password,
        password2=valid_password
    ))

    assert valid_rv.status_code == 200
    assert b'User added' in valid_rv.data

    # New user's email already in db
    email_exists_rv = client.post('/register', data=dict(
        username=valid_username_2,
        email=valid_email,
        password1=valid_password,
        password2=valid_password
    ))

    assert b'Username or email already exists' in email_exists_rv.data
    assert email_exists_rv.status_code == 400

    # New user's username already in db
    user_exists_rv = client.post('/register', data=dict(
        username=valid_username,
        email=valid_email_2,
        password1=valid_password,
        password2=valid_password
    ))

    assert b'Username or email already exists' in user_exists_rv.data
    assert user_exists_rv.status_code == 400


def test_verify_user(client):
    """Test verify User token route"""
    username = "test"
    password = "test123"

    verified_user = create_user(username, password, is_verified=False)
    add_user_to_db(verified_user)
    verified_user.id = 0

    token = verified_user.get_email_token()

    no_token_rv = client.get('/verify', follow_redirects=True)
    invalid_rv = client.get('/verify?token={}'.format("token"),
                            follow_redirects=True)
    valid_rv = client.get('/verify?token={}'.format(token),
                          follow_redirects=True)

    assert no_token_rv.status_code == 401
    assert b'Please log in' in no_token_rv.data

    assert invalid_rv.status_code == 401
    assert b'Please log in' in invalid_rv.data

    assert valid_rv.status_code == 200
    assert b'This is a restricted page! <User %b>' % username.encode('utf-8') \
        in valid_rv.data

    assert verified_user.is_verified is True


def test_unverified_login(client):
    """
    Test unverified login and resend verification email
    NOTE: This test will fail if your SendGrid API key
          is not set
    """
    username = "test"
    password = "test123"
    email = "test@email.com"

    unverified_user = create_user(username, password, is_verified=False)
    unverified_user.email = "test@email.com"
    add_user_to_db(unverified_user)

    unverified_login = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    assert unverified_login.status_code == 401
    assert b'Please verify your account. We just sent another email' \
        in unverified_login.data


def test_login_user(client):
    """Test login user"""

    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    invalid_login = client.post('/login', data=dict(
        username="baduser",
        password="badpass"
    ), follow_redirects=True)

    invalid_form = client.post('/login', data=dict(
        username=username
    ), follow_redirects=True)

    assert valid_login.status_code == 200
    assert invalid_login.status_code == 400
    assert invalid_form.status_code == 400


def test_logout_user(client):
    """Test User logout"""
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    logged_in_rv = client.get('/')

    logout = client.get('/logout')

    logged_out_rv = client.get('/', follow_redirects=True)

    assert logged_in_rv.status_code == 200

    assert b'Logged out' in logout.data

    assert logged_out_rv.status_code == 401
    assert b'Please log in' in logged_out_rv.data


def test_delete_user(client, s3_client):
    """Delete a User and that User's bucket"""
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    delete_rv = client.delete('/user/delete')

    delete_rv.status_code == 200
    assert b'User deleted' in delete_rv.data


def test_user_token(client):
    """Test verification of User JWT"""
    user = User(id=0)
    token = user.get_email_token()
    valid_token = user.verify_email_token(token)
    invalid_token = user.verify_email_token("token")

    assert valid_token == 0
    assert invalid_token is False


def test_user_password():
    """Test new user password hash"""

    user = User(email='someone@gmail.com', username='This is cool')
    user.set_password('password')

    assert user.check_password('password')
    assert user.password_hash != 'password'
