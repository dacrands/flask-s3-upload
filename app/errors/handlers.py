from flask import jsonify
from flask_wtf.csrf import CSRFError
from app.errors import bp


@bp.app_errorhandler(CSRFError)
def csrf_error(e):
    return jsonify({
        'msg': 'You are missing a CSRF token'
    }), 400
