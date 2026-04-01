from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import secrets, string, bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room,leave_room
from flask_jwt_extended import verify_jwt_in_request, create_access_token

app = Flask(__name__)
db = SQLAlchemy(app)
key='secret'
socketio = SocketIO(app, cors_allowed_origins="*")
PUBLIC_ROUTES = {"login", "register"}

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit(joined,username + ' has entered the room.', to=room)

@socketio.on('create')
def on_create(data):
    namespace = request.namespaces['/']
    rooms = list(namespace.adapter.rooms.keys()) 
    username = data['username']
    while True:
        chars = string.ascii_uppercase + string.digits
        room = ''.join(secrets.choice(chars) for _ in range(10))
        if room not in rooms:
            break
    join_room(room)
    emit(created,' New room created. Room code = '+ room, to=room)
    emit(joined,username + ' has entered the room.', to=room)
    

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit(left,username + ' has left the room.', to=room)

@socketio.on('connect')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')
@socketio.on('send_message')
def handle_send_message(data):
    emit('new_message', data, to=data['room'])

@app.before_request
def require_jwt_for_all_routes():
    if request.endpoint in PUBLIC_ROUTES:
        return
    verify_jwt_in_request()
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # autoincrement=True is default
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(30))
    name = db.Column(db.String(60))

@app.route("/login",methods=['POST'])
def login():
    data = request.json  
    user_name = data['username']
    salt = bcrypt.gensalt()
    password = bcrypt.hashpw(data['password'],salt)
    user = User.query.filter_by(username=user_name).first()
    if user is None:
        return jsonify({'error': 'Invalid credentials'}),401
    if user.password == password:
        payload={ 'sub':user_name,
                 'iat': int(datetime.utcnow().timestamp()),
                 'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
                token=create_access_token(identity=user_name)
        return jsonify({'token':token}),200
    return jsonify({'error': 'Invalid credentials'}),401

@app.route("/reg",methods=['POST'])
def register():
    data = request.json
    name = data['name']        
    user_name = data['username']
    salt = bcrypt.gensalt()
    password = bcrypt.hashpw(data['password'],salt)
    user = User.query.filter_by(username=user_name).first()
    if user:
        return jsonify({'error': 'Username taken'}),400
    user = User(
        username = user_name,
        name = name,
        password = password)
    db.session.add(user)      
    db.session.commit()       
    payload={ 'sub':user_name,
                 'iat': int(datetime.utcnow().timestamp()),
                 'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
    token=create_access_token(identity=user_name)
    return jsonify({'token': token,'message': 'User created', 'id': user.id}),201

if __name__ == '__main__':
    socketio.run(app)
