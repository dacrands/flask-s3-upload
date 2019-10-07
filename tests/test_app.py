import os
import tempfile
import pytest

from app import app, db
from app.models import User

basedir = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] =  \
        'sqlite:///' + os.path.join(basedir, 'test_app.db')

    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            yield client

    db.drop_all()


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

    assert valid_login.status_code == 200
    assert invalid_login.status_code == 400


def test_unauthorized_redirect(client):
    """Test unauthorized redirect"""

    rv = client.get('/')

    assert rv.status_code == 302


def test_unauthorized_request(client):
    """Test unauthorized request"""

    rv = client.get('/', follow_redirects=True)

    assert rv.status_code == 401


def test_user_password():
    """Test new user password hash"""

    user = User(email='someone@gmail.com', username='This is cool')
    user.set_password('password')

    assert user.check_password('password')
    assert user.password_hash != 'password'
