from app import db
from app.models import User

from tests.conftest import create_user, add_user_to_db

TEST_S3_BUCKET = 'somebucket'


def test_unauthorized_redirect(client):
    """Test unauthorized redirect"""
    get_index = client.get('/')
    assert get_index.status_code == 302

    get_files = client.get('/files')
    assert get_files.status_code == 302


def test_unauthorized_request(client):
    """Test unauthorized request"""
    get_index = client.get('/', follow_redirects=True)
    assert get_index.status_code == 401

    get_files = client.get('/files', follow_redirects=True)
    assert get_files.status_code == 401


def test_authorized_request(client):
    """Test authorized requests"""
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    login_rv = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    get_index = client.get('/')
    assert get_index.status_code == 200

    get_files = client.get('/files')
    assert get_files.status_code == 200


def test_register_user(client, s3_fixture):
    """Test register User"""
    s3_client = s3_fixture[0]
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
    assert no_token_rv.status_code == 401
    assert b'Please log in' in no_token_rv.data

    invalid_rv = client.get('/verify?token={}'.format("token"),
                            follow_redirects=True)
    assert invalid_rv.status_code == 401
    assert b'Please log in' in invalid_rv.data

    valid_rv = client.get('/verify?token={}'.format(token),
                          follow_redirects=True)
    assert valid_rv.status_code == 200
    assert verified_user.is_verified is True
    assert b'This is a restricted page! <User %b>' % username.encode('utf-8') \
        in valid_rv.data


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

    unverified_login_rv = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    assert unverified_login_rv.status_code == 401
    assert b'Please verify your account. We just sent another email' \
        in unverified_login_rv.data


def test_login_user(client):
    """Test login user"""

    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login_rv = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)
    assert valid_login_rv.status_code == 200

    invalid_login_rv = client.post('/login', data=dict(
        username="baduser",
        password="badpass"
    ), follow_redirects=True)
    assert invalid_login_rv.status_code == 400

    invalid_form_rv = client.post('/login', data=dict(
        username=username
    ), follow_redirects=True)
    assert invalid_form_rv.status_code == 400


def test_logout_user(client):
    """Test User logout"""
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login_rv = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    logged_in_rv = client.get('/')
    assert logged_in_rv.status_code == 200

    logout_rv = client.get('/logout')
    assert b'Logged out' in logout_rv.data

    logged_out_rv = client.get('/', follow_redirects=True)
    assert logged_out_rv.status_code == 401
    assert b'Please log in' in logged_out_rv.data


def test_delete_user(client, s3_fixture):
    """Delete a User and that User's bucket"""
    s3_client = s3_fixture[0]
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)
    username = "test"
    password = "test123"

    add_user_to_db(create_user(username, password))

    valid_login_rv = client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

    delete_rv = client.delete('/user/delete')

    assert delete_rv.status_code == 200
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
