from random import randint
from flask import session
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy, session
import os, time
from sqlalchemy import text, true, ForeignKey, false
from flask_login import UserMixin, LoginManager, login_required, current_user, logout_user, login_user
from sqlalchemy.dialects.sqlite import json
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
import json
from flask import jsonify
from flask_admin import Admin, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from flask_login import LoginManager
from flask_admin import Admin
from flask_socketio import SocketIO, emit, join_room, leave_room, send

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SECRET_KEY'] = 'hxjowf'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
admin = Admin(app, name='MyApp', template_mode='bootstrap3')

# Initialize SocketIO
socketio = SocketIO(app)


# database models for the user,

class User(db.Model, UserMixin):
    __tablename__ = 'users'  # Explicit table name
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    profile_image = db.Column(db.String(255), nullable=False, default='default_pic.png')


    # password hashing
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # checking the hashed password in the db
    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.user_id)


#store each game as an event
class Game(db.Model):
    __tablename__ = 'games'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


#store the winner/loser of each game
class GameResult(db.Model):
    #store the ids of the current game, the winning user id and losing user id
    __tablename__ = 'game_results'  # Explicit table name
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), primary_key=True)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    loser_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    game = db.relationship('Game', backref=db.backref('results', lazy=True))
    winner = db.relationship('User', foreign_keys=[winner_id], backref=db.backref('wins', lazy='dynamic'))
    loser = db.relationship('User', foreign_keys=[loser_id], backref=db.backref('losses', lazy='dynamic'))

    def get_id(self):
        return str(self.game_id)

class GameRoom(db.Model):
    __tablename__ = 'game_rooms'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)  # ForeignKey must reference 'games.id'
    room_code = db.Column(db.String(10), unique=True)
    player_count = db.Column(db.Integer, default=1)  # Count of current players in the room

    game = db.relationship('Game', backref=db.backref('room', uselist=False, cascade="all, delete"))


# model view for all the tables for admin
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


class GameResultModelView(BaseModelView):
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    ## game_id = db.Column(db.Integer, db.ForeignKey('games.id'), primary_key=True)
    #winner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    #loser_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    #game = db.relationship('Game', backref=db.backref('results', lazy=True))
    #winner = db.relationship('User', foreign_keys=[winner_id], backref=db.backref('wins', lazy='dynamic'))
    #loser =
    # Fields to display in the form

    form_columns = ['game_id', 'winner_id', 'loser_id', 'game', 'winner', 'loser']
    # Labels for the columns
    column_labels = {
        'game_id': 'Game Id',
        'winner_id': 'Winner id',
        'loser_id': 'Loser id',
        'game': 'Game',
        'winner': 'Winner',
        'loser': 'Loser'
    }

    # Fields to display in the list view
    column_list = ['game_id', 'winner_id', 'loser_id', 'game', 'winner', 'loser']

    def __init__(self, model, session, **kwargs):
        super(GameResultModelView, self).__init__(model, session, **kwargs)
        self.static_folder = 'static'
        self.name = 'Classes'

    def after_model_change(self, form, model, is_created):
        super(GameResultModelView, self).after_model_change(form, model, is_created)


class GameModelView(BaseModelView):
    column_list = ('id', 'timestamp')
    column_labels = {
        'id': 'Game Id',
        'timestamp': 'Timestamp',
    }

    def __init__(self, model, session, **kwargs):
        super(GameModelView, self).__init__(model, session, **kwargs)
        self.static_folder = 'static'
        # self.endpoint = 'admin.index'
        self.name = 'Game'


# flask views
admin.add_view(UserModelView(User, db.session))
admin.add_view(GameModelView(Game, db.session))
admin.add_view(GameResultModelView(GameResult, db.session))


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

    admin_user = User(name='admin', username='admin', email='admin@admin.com')
    admin_user.set_password("AdminPassword123")
    db.session.add(admin_user)
    db.session.commit()

    ## add default game data
    game1 = Game()
    db.session.add(game1)
    game2 = Game()
    db.session.add(game2)
    db.session.commit()

    #set result as jimdoe win, jose lost
    result1 = GameResult(game_id=game1.id, winner_id=user1.user_id, loser_id=user2.user_id)
    db.session.add(result1)

    #set result as jimdoe lost, jose win
    result2 = GameResult(game_id=game2.id, winner_id=user2.user_id, loser_id=user1.user_id)
    db.session.add(result2)

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


#requires user to be logged in before accessing dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/profile')
@login_required
def profile():
    # user profile
    user_profile = User.query.filter_by(user_id=current_user.user_id).first()

    # Calculate wins and losses
    wins = GameResult.query.filter_by(winner_id=current_user.user_id).count()
    losses = GameResult.query.filter_by(loser_id=current_user.user_id).count()

    # Calculate win rate
    total_games = wins + losses
    if total_games > 0:
        win_rate = (wins / total_games) * 100
    else:
        win_rate = 0  # Avoid division by zero if no games played

    # Render the profile page with the data
    return render_template('profile_page.html', display_name=current_user.name, profile_data=user_profile,
                           wins=wins, losses=losses, win_rate=win_rate)
    
@app.route('/update_profile_pic', methods=['POST'])
@login_required
def update_profile_pic():
    data = request.get_json()
    user = User.query.get(current_user.user_id)
    if data and 'profile_image' in data:
        user.profile_image = data['profile_image']
        db.session.commit()
        return jsonify({'message': 'Profile image updated successfully!'}), 200
    return jsonify({'message': 'Invalid request'}), 400


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
            #added admin route
            if user.username == 'admin':
                return redirect(url_for('admin.index'))
            else:
                return redirect(url_for('dashboard'))  # Redirect to dashboard
        else:
            # If authentication fails, reload the login page with an error
            print('Invalid username or password.', 'error')
    # For GET requests or failed login attempts
    return render_template('login-teacher.html')


@app.route('/game', methods=['GET', 'POST'])
def game():
    return render_template('index.html')


#####################################
######### 2 player stuff ################
###################################
@app.route('/game2p')
def game2p():
    return render_template('index2p.html')


#join the new room
@app.route('/new_game_or_join')
def new_game_or_join():
    #room capacity is 2
    available_room = GameRoom.query.filter(GameRoom.player_count < 2).first()
    if available_room:
        available_room.player_count += 1 #commit join to room
        db.session.commit()
        if available_room.player_count == 2: #start game/room full
            # Emit event to all clients in this room that the game is ready
            socketio.emit('game_ready', {'message': 'All players connected. Game starting...'}, room=available_room.room_code)
        return redirect(url_for('game2p', room_code=available_room.room_code))
    else:
        #create new game for 1 player
        new_game = Game()
        db.session.add(new_game)
        db.session.flush()
        new_room_code = str(randint(1000, 9999))
        new_game_room = GameRoom(game_id=new_game.id, room_code=new_room_code, player_count=1)
        db.session.add(new_game_room)
        db.session.commit()
        return redirect(url_for('game2p', room_code=new_room_code))


#############################################



# sign out button
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

################################
#cache busting
###################

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

############################

###########################
#socketio stuff
########################
@socketio.on('connect')
def socket_connet():
    print("Client Connected :D")

@socketio.on('message')
def handle_message(data):
    print('received message: ' + str(data))
    emit('response', {'data': 'Server received: ' + str(data)})

# socketio.on('join_game')
# def handle_join_game(data):
#     join_room(data['game_id'])
#     emit('join_confirmation', {'message': 'Joined game: ' + data['game_id']}, room=data['game_id'])

@socketio.on('end_game')
def handle_end_game(data):
    game = Game(result=data['result'], end_time=datetime.utcnow())
    db.session.add(game)
    db.session.commit()
    emit('game_over', {'result': data['result']}, room=data['game_id'])
#user joins a new room
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['game_id']
    join_room(room)
    send(username + ' has entered the room.room}', room=room)

#user leaves the room
@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['game_id']
    leave_room(room)
    send(username + ' has left the room.', room=room)


########game run###############

if __name__ == '__main__':
    # app.run(debug=True)
    socketio.run(app, debug=True)
