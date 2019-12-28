import os
import tempfile
import pytest

from app import create_app, db
from app.models import User

basedir = os.path.abspath(os.path.dirname(__file__))

TEST_DB_PATH = os.path.join(basedir, 'test_app.db')
TEST_DB_URI = 'sqlite:///' + TEST_DB_PATH


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

    except Exception as err:
        print("Unexpected error adding User to db: ", err)
        raise


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=TEST_DB_URI
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
