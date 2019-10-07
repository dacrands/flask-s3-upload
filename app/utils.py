from functools import wraps
from app import app
from flask import redirect, url_for, request
from flask_login import current_user


def allowed_file(filename):
    """
    Makes sure the file has a permitted extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    """
    temp auth middleware until resolve https redirect with
    `login_required` from flask-login
    """
    @wraps(f)
    def https_redirect(*args, **kwargs):
        if not current_user.is_authenticated:
            if not app.debug:
                return redirect(url_for('login', next=request.url, _scheme='https', _external='true'))
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return https_redirect
