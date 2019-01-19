from app import db, login
from flask_login import UserMixin

class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(64), index=True, unique=True)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))