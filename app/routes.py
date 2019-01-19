from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from app.models import User

MIN_USERNAME_LEN = 6
MAX_USERNAME_LEN = 20
MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 30
    
    


@app.route('/')
@login_required
def index():
    return jsonify({'msg': 'This is a restricted page! {}'.format(current_user.username)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Expects two form values:
    - username
    - password    
    '''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
        except:
            return jsonify({'msg':'Missing form information'})            

        user = User.query.filter_by(username=username).first()        

        if (not user) or (not user.check_password(password)):
            return jsonify({'msg':'Invalid uername or password'})    

        login_user(user)
        return jsonify({'msg':'Logged in'})

    return jsonify({'msg':'Please log in'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'msg':'Logged out'})

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
            return jsonify({'msg':'Missing part of your form'})

        user = User.query.filter_by(username=username).first()
        if user:
            return jsonify({'msg':'Username already exists'})
        if (len(username) < 8) or (len(username) > 20):
            return jsonify({'msg':'Username must be between {0} and {1} characters'.format(MIN_USERNAME_LEN, MAX_USERNAME_LEN)})

        password_len = max(len(password1), len(password2))
        if  (password_len < 8) or (password_len > 20):
            return jsonify({'msg':'Password  must be between {0} and {1} characters'.format(MIN_PASSWORD_LEN, MAX_PASSWORD_LEN)})

        if password1 != password2:
            return jsonify({'msg':'Passwords do not match'})        

        user = User(username=username)
        user.set_password(password1)
        db.session.add(user)
        db.session.commit()
        
    return jsonify({'msg':'User added'})

@app.route('/user', methods=['DELETE'])
@login_required
def delete_user():
    db.session.delete(current_user)
    db.session.commit()
    
    return jsonify({'msg': 'User deleted'})
