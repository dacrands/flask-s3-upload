import os
import tempfile
import pytest

from app import create_app, db
from app.models import User

basedir = os.path.abspath(os.path.dirname(__file__))

TEST_DB_PATH = 'sqlite:///' + os.path.join(basedir, 'test_app.db')


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=TEST_DB_PATH
    )

    with app.test_client() as client:
        with app.app_context() as app_context:
            db.create_all()
            app_context.push()

            yield client

            db.session.remove()
            db.drop_all()
            app_context.pop()


def test_login_user(client):
    """Test login user"""

    username = "test"
    email = "test@email.com"
    password = "test123"
    user = User(
        username=username,
        email=email
    )

    user.set_password(password)
    user.is_verified = True
    db.session.add(user)

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


def test_user_password():
    """Test new user password hash"""

    user = User(email='someone@gmail.com', username='This is cool')
    user.set_password('password')

    assert user.check_password('password')
    assert user.password_hash != 'password'
