import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    S3_BUCKET = os.environ.get('S3_BUCKET') or 'NOT_SET'
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY') or 'whoops'
