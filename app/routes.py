from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from app.models import User


@app.route('/')
@login_required
def index():
    return 'Hello World'


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
        except:
            return jsonify({
                'msg': 'Missing form information'
            })
            
        user = User.query.filter_by(username=username).first()                
        if not user:
            return jsonify({
                'msg': 'Invalid uername or password'
            })
        
        if not user.check_password(password):
            return jsonify({
                'msg': 'Invalid uername or password'
            })
        login_user(user)

    return 'Logged in'


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
    Expects three form values:
    - username
    - password1
    - password2
    '''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
        except:
            return 'Missing part of your form'

        if password1 != password2:
            return 'Passwords do not match'
        
        user = User.query.filter_by(username=username).first()
        if user:
            return 'Usernames already exists'

        user = User(username=username)
        user.set_password(password1)
        db.session.add(user)
        db.session.commit()
        return 'User added'

    return 'test'
