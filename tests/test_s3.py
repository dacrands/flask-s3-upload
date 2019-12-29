import io

from app.models import User

from tests.conftest import create_user, add_user_to_db

TEST_S3_BUCKET = 'somebucket'


def test_upload_file(client, s3_fixture):
    username = 'testuser'
    password = 'testpass'
    invalid_file_name = 'test.txt'
    valid_file_name = 'test.pdf'
    invalid_file_desc = "test" * 50

    (s3_client, s3) = s3_fixture
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)

    s3.Bucket(TEST_S3_BUCKET).put_object(Key=username + '/')

    add_user_to_db(create_user(username, password))

    client.post('/login', data=dict(
        username=username,
        password=password
    ))

    # Form missing file
    missing_file_rv = client.post('/files', follow_redirects=True)
    assert missing_file_rv.status_code == 400
    assert b'Missing part of your form' in missing_file_rv.data

    # Invalid file type
    invalid_file_type_rv = client.post(
        '/files',
        data=dict(
            text="This is a file",
            date="some date",
            file=(
                io.BytesIO(b'this is a test'), invalid_file_name
            )
        ),
        follow_redirects=True)
    assert invalid_file_type_rv.status_code == 400
    assert b'Invalid file type' in invalid_file_type_rv.data

    # File missing name
    missing_filename_rv = client.post(
        '/files',
        data=dict(
            text="This is a file",
            date="some date",
            file=(io.BytesIO(b'this is a test'), '')
        ),
        follow_redirects=True)
    assert missing_filename_rv.status_code == 400
    assert b'missing file name' in missing_filename_rv.data

    # File description too long
    invalid_file_desc_rv = client.post(
        '/files',
        data=dict(
            text=invalid_file_desc,
            date="some date",
            file=(
                io.BytesIO(b'this is a test'), valid_file_name
            )
        ),
        follow_redirects=True)
    assert invalid_file_desc_rv.status_code == 400
    assert b'File description must be less than 130 characters' \
        in invalid_file_desc_rv.data

    # Valid file post
    post_file_rv = client.post(
        '/files',
        data=dict(
            text="This is a file",
            date="some date",
            file=(
                io.BytesIO(b'this is a test'), valid_file_name
            )
        ),
        follow_redirects=True)
    assert post_file_rv.status_code == 200
    assert b'Uploaded %b' % valid_file_name.encode('utf-8') \
        in post_file_rv.data

    # Filename already exists
    file_exists_rv = client.post(
        '/files',
        data=dict(
            text="This is a file",
            date="some date",
            file=(
                io.BytesIO(b'this is a test'), valid_file_name
            )
        ),
        follow_redirects=True)
    assert file_exists_rv.status_code == 400
    assert b'You already have a file with that name' in file_exists_rv.data
