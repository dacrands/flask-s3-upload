from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from app.models import User

def json_msg(msg):
    return jsonify({'msg': msg})


@app.route('/')
@login_required
def index():
    return json_msg('This is a restricted page!')


@app.route('/login', methods=['POST', 'GET'])
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
            return json_msg('Missing form information')            

        user = User.query.filter_by(username=username).first()        

        if (not user) or (not user.check_password(password)):
            return json_msg('Invalid uername or password')    

        login_user(user)

    return json_msg('Logged in')


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
    Expects three form values:
    - username
    - password1
    - password2

    Generates user S3 Object
    '''
    if request.method == 'POST':
        try:
            username = request.form['username']
            password1 = request.form['password1']
            password2 = request.form['password2']
        except:
            return json_msg('Missing part of your form')

        if password1 != password2:
            return json_msg('Passwords do not match')
        
        user = User.query.filter_by(username=username).first()
        if user:
            return json_msg('Usernames already exists')

        user = User(username=username)
        user.set_password(password1)
        db.session.add(user)
        db.session.commit()
        
    return json_msg('User added')
