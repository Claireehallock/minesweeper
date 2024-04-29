from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
import os, time
from sqlalchemy import text, true, ForeignKey, false
from flask_login import UserMixin, LoginManager, login_required, current_user, logout_user, login_user
from sqlalchemy.dialects.sqlite import json
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
import json
from flask_admin import Admin, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'  # Update as needed
app.config['SECRET_KEY'] = 'hxjowf'  # random characters

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

admin = Admin(app, name='MyApp', template_mode='bootstrap3')


# database models for the user,

class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)

    # password hashing
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # checking the hashed password in the db
    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.user_id)


class BaseModelView(ModelView):
    form_excluded_columns = []

    def __init__(self, model, *args, **kwargs):
        super(BaseModelView, self).__init__(model, *args, **kwargs)
        # exclude primary key column
        self.form_excluded_columns = [column.name for column in model.__table__.primary_key.columns]


# class views for each model to ignore primary key by passing the model view
class UserModelView(BaseModelView):
    form_columns = ['user_id', 'name', 'username', 'password', 'email']

    # Labels for the columns
    column_labels = {
        'user_id': 'User Id',
        'name': 'Name',
        'username': 'Username',
        'password': 'Password',
        'email': 'Email',
    }

    # Fields to display in the list view
    column_list = ['user_id', 'name', 'username', 'password', 'email']

    def __init__(self, model, session, **kwargs):
        super(UserModelView, self).__init__(model, session, **kwargs)
        self.static_folder = 'static'
        self.name = 'User'

    def on_model_change(self, form, model, is_created):
        # If the user is being created, `is_created` will be True.
        # hash password on creation
        if is_created:
            model.password = generate_password_hash(form.password.data)
        super(UserModelView, self).on_model_change(form, model, is_created)


admin.add_view(UserModelView(User, db.session))


# flask-login
# reloads the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




def insert_default_data():
    user1 = User(name='Jim Doe', username='jimdoe', email='jimdoe@abc.com')
    user1.set_password("password123")
    db.session.add(user1)


    user2 = User(name='Jose Santos', username='josesantos', email='jsantos@uc.edu')
    user2.set_password("realpassword123")
    db.session.add(user2)

    user3 = User(name='Nancy Little', username='nancylittle', email='test@123.com')
    user3.set_password("opassword123")
    db.session.add(user3)

    db.session.commit()


# create database
with app.app_context():
    db.drop_all()  # Delete the previous cache database
    db.create_all()
    insert_default_data()
    print("database successfully created")


# setup so default page is the login
@app.route('/')
def home():
    return render_template('login-teacher.html')


# function for login
@app.route('/login')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # need these from front end
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            # check roles and bring to correct page
        else:
            # If authentication fails, reload the login page with an error
            print('Invalid username or password.', 'error')
    # For GET requests or failed login attempts
    return render_template('login-teacher.html')


# sign out button
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


#cache buster
@app.context_processor
def inject_cache_buster():
    def cache_buster():
        return int(time.time())

    return dict(cache_buster=cache_buster)


# Remove cache to prevent errors - additional method
@app.after_request
def add_cache_control_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    app.run(debug=True)
