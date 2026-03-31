from flask import Flask,request
from flask_sqlalchemy import SQLAlchemy
import jwt, secrets, string
from flask_socketio import SocketIO, emit, join_room
from flask_jwt_extended import verify_jwt_in_request

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
    send(username + ' has entered the room.', to=room)

@socketio.on('create')
def on_create(data):
    namespace = request.namespaces['/chat']
    rooms = list(namespace.adapter.rooms.keys()) 
    username = data['username']
    while True:
        chars = string.ascii_uppercase + string.digits
        room = ''.join(secrets.choice(chars) for _ in range(10))
        if room not in rooms:
            break
    join_room(room)
    send(' New room created. Room code = '+ room, to=room)
    send(username + ' has entered the room.', to=room)
    

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', to=room)

@socketio.on('connect')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect(reason):
    print('Client disconnected, reason:', reason)

@app.before_request
def require_jwt_for_all_routes():
    if request.endpoint in PUBLIC_ROUTES:
        return
    verify_jwt_in_request()

room_users = db.Table(
    'room_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'), primary_key=True)
)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    users = db.relationship('User', secondary=room_users, backref='rooms')
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # autoincrement=True is default
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(30))
    name = db.Column(db.String(60))

@app.route("/login",methods=['POST'])
def login():
    data = request.json  
    user_name = data['username']
    password = hash(data['password'])
    user = User.query.filter_by(username=user_name)
    if user ==None:
    return jsonify({'error': 'Invalid credentials'}),401
    if user.password == password:
        payload={ sub:user_name,
                 iat: int(datetime.utcnow().timestamp()),
                 exp: int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
        token=jwt.encode(payload,key)
        return jsonify({'token':token,'status':200})
    return jsonify({'error': 'Invalid credentials'}),401

@app.route("/reg",methods=['POST'])
def register:
    data = request.json
    name = data['name']        
    user_name = data['username']
    password = hash(data['password'])
    user = User.query.filter_by(username=user_name)
    if user:
        return jsonify({'error': 'Username taken'}),400
    user = User(
        username = user_name
        name = name
        password = password)
    db.session.add(user)      # Stage for INSERT
    db.session.commit()       # Execute SQL
    payload={ sub:user_name,
                 iat: int(datetime.utcnow().timestamp()),
                 exp: int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
    token=jwt.encode(payload,key)
    return jsonify({'token': token,'message': 'User created', 'id': user.id}),201

@app.route("/rooms",methods=['GET','POST'])
def rooms:
    if request.method == "GET":
        all_rooms = Room.query.all()
        return jsonify([{
        'id': room.id,
        'code': room.code,
        'name': room.name,
        'desc' : room.description
    } for room in all_rooms])

    elif request.method == "POST":
        data = request.json
        room_code = data['code']
        desc = data['description']
        name = data['name']
        room = Room.query.filter_by(code = room_code)
        if room:
            return jsonify({'error': 'Room already exists'}),400
        room = Room(code= room_code, name=name, description=desc)
        db.session.add(room)
        db.session.commit()
        return jsonify({'message': 'Room created'}),200

@app.route('/rooms/<code>/join', methods=['POST'])
def join_room(code):
    user_id = get_jwt_identity()
    room = Room.query.filter_by(code=code).first()
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    # Check if already member
    if user_id in [u.id for u in room.users]:
        return jsonify({'error': 'Already in room'}), 400
    
    # Add user to room 
    user = User.query.get(user_id)
    room.users.append(user)
    db.session.commit()
    return jsonify({'message': 'Joined room', 'room_id': room.id}), 201

@app.route('/rooms/<code>/leave', methods=['POST'])
def leave_room(code):
    user_id = get_jwt_identity()
    room = Room.query.filter_by(code=code).first()
    
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    # Check if already member
    if user_id not in [u.id for u in room.users]:
        return jsonify({'error': 'Already left room'}), 400
    
    # Add user to room 
    user = User.query.get(user_id)
    room.users.remove(user)
    db.session.commit()
    return jsonify({'message': 'Left room', 'room_id': room.id}), 201


if __name__ == '__main__':
    socketio.run(app)
