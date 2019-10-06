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

    db.create_all()

    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            yield client

            db.drop_all()


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
