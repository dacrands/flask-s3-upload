from flask import Blueprint

bp = Blueprint('s3', __name__)

from app.s3 import routes
