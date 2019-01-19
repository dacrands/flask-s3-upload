from flask_login import login_user, logout_user, current_user, login_required
from app import app, db

@app.route('/')
def index():
  return 'Hello World'