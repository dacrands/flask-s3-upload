import io

from app import db
from app.models import User, File

from tests.conftest import create_user, add_user_to_db

TEST_S3_BUCKET = 'somebucket'


def create_file(name, username, user_id,
                id=0, desc=""):
    try:
        file = File(
            id=id,
            name=name,
            key="{0}/{1}".format(username, name),
            body=desc
        )
        file.user_id = user_id
        return file

    except Exception as err:
        print("Unexpected error creating File: ", err)
        raise


def add_file_to_db(file):
    try:
        db.session.add(file)
        db.session.commit()

    except Exception as err:
        print("Unexpected error adding User to db: ", err)
        raise


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


def test_get_file_by_id(client, s3_fixture):
    username = 'testuser'
    user_id = 0
    file_id = 0
    file_2_id = 1
    invalid_file_id = 9
    password = 'testpass'
    file_name = 'test.pdf'
    file_2_name = 'test2.pdf'
    file_desc = 'test'

    (s3_client, s3) = s3_fixture
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)

    user = create_user(username, password)
    user.id = user_id
    add_user_to_db(user)

    file = create_file(
        name=file_name,
        id=file_id,
        desc=file_desc,
        username=username,
        user_id=user_id
    )

    file_2 = create_file(
        name=file_2_name,
        id=file_2_id,
        username=username,
        user_id=user_id
    )

    add_file_to_db(file)
    add_file_to_db(file_2)

    s3.Bucket(TEST_S3_BUCKET).put_object(
        Key=file.key,
        Body=io.BytesIO(b'this is a test')
    )

    client.post('/login', data=dict(
        username=username,
        password=password
    ))

    invalid_file_id_rv = client.get('/files/{}'.format(invalid_file_id))
    assert b'File does not exist' in invalid_file_id_rv.data

    file_not_in_bucket_rv = client.get('/files/{}'.format(file_2_id))
    assert b'File not in your folder' in file_not_in_bucket_rv.data

    valid_get_rv = client.get('/files/{}'.format(file_id))
    assert valid_get_rv.status_code == 200
    assert b'{"file":{"body":"%b"' % file_desc.encode('utf-8') \
        in valid_get_rv.data


def test_edit_file_by_id(client, s3_fixture):
    username = 'testuser'
    user_id = 0
    password = 'testpass'

    file_name = 'test.pdf'
    file_id = 0
    file_desc = "This will change."
    file_desc_changed = "This is changed."
    file_desc_too_long = "t" * 131
    invalid_file_id = 9

    file = create_file(
        name=file_name,
        id=file_id,
        username=username,
        user_id=user_id,
        desc=file_desc
    )

    add_user_to_db(create_user(username, password))
    add_file_to_db(file)

    client.post('/login', data=dict(
        username=username,
        password=password
    ))

    invalid_file_id_rv = client.patch(
        '/files/{}/edit'.format(invalid_file_id)
    )
    assert b'File does not exist' in invalid_file_id_rv.data

    missing_form_rv = client.patch(
        '/files/{}/edit'.format(file_id)
    )
    assert b'Missing part of your form' in missing_form_rv.data
    assert missing_form_rv.status_code == 400

    too_long_desc_rv = client.patch(
        '/files/{}/edit'.format(file_id), data=dict(
            body=file_desc_too_long
        )
    )
    assert b'File description must be less than 130 characters' \
        in too_long_desc_rv.data
    assert too_long_desc_rv.status_code == 400

    file_edit_rv = client.patch(
        '/files/{}/edit'.format(file_id), data=dict(
            body=file_desc_changed
        )
    )
    assert file.body == file_desc_changed
    assert b'File edited!' in file_edit_rv.data
    assert file_edit_rv.status_code == 200


def test_delete_file_by_id(client, s3_fixture):
    username = 'testuser'
    user_id = 0
    password = 'testpass'
    file_id = 0
    file_2_id = 1
    invalid_file_id = 9
    file_name = 'test.pdf'
    file_2_name = 'test2.pdf'

    (s3_client, s3) = s3_fixture
    s3_client.create_bucket(Bucket=TEST_S3_BUCKET)

    add_user_to_db(create_user(username, password))

    file = create_file(
        name=file_name,
        id=file_id,
        username=username,
        user_id=user_id
    )

    file_2 = create_file(
        name=file_2_name,
        id=file_2_id,
        username=username,
        user_id=user_id
    )

    add_file_to_db(file)
    add_file_to_db(file_2)

    client.post('/login', data=dict(
        username=username,
        password=password
    ))

    invalid_file_id_rv = client.delete(
        '/files/{}/delete'.format(invalid_file_id)
    )
    assert b'File does not exist' in invalid_file_id_rv.data

    delete_file_rv = client.delete('/files/{}/delete'.format(file_id))
    assert delete_file_rv.status_code == 200
    assert b'File removed' in delete_file_rv.data
