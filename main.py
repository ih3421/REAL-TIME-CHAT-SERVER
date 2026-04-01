from flask import Flask, request, jsonify
import secrets, string, bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room,leave_room
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, decode_token

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
jwt = JWTManager(app)
socket_users = {}

@socketio.on("join")
def on_join(data):
    if request.sid not in socket_users:
        disconnect()
        return
    username = socket_users[request.sid]
    room = data["room"]
    join_room(room)
    emit("joined", f"{username} has entered the room.", to=room)


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
    emit('created',' New room created. Room code = '+ room, to=room)
    emit('joined',username + ' has entered the room.', to=room)
    

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('left',username + ' has left the room.', to=room)

@socketio.on("connect")
def handle_connect(auth):
    token = None
    if "token" in auth:
        token = auth["token"]
    if not token:
        return False
    try:
        decoded = decode_token(token)
        username = decoded["sub"]
        socket_users[request.sid] = username
        return True
    except Exception:
        return False

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')
@socketio.on('send_message')
def handle_send_message(data):
    emit('new_message', data, to=data['room'])

    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # autoincrement=True is default
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200))
    name = db.Column(db.String(60))

@app.route("/chat", methods=["GET"])
@jwt_required()
def chat():   
    return jsonify({
        "message": "Chat enabled",
        "user": get_jwt_identity()
    }), 200

@app.route("/login",methods=['POST'])
def login():
    data = request.json  
    user_name = data['username']
    user = User.query.filter_by(username=user_name).first()
    if user is None:
        return jsonify({'error': 'Invalid credentials'}),401
    if bcrypt.checkpw(data['password'].encode('utf-8'), user.password.encode('utf-8')):
        token=create_access_token(identity=user_name)
        return jsonify({'token':token}),200
    return jsonify({'error': 'Invalid credentials'}),401

@app.route("/reg",methods=['POST'])
def register():
    data = request.json
    name = data['name']        
    user_name = data['username']
    salt = bcrypt.gensalt()
    password = bcrypt.hashpw(data['password'].encode('utf-8'),salt).decode('utf-8')
    user = User.query.filter_by(username=user_name).first()
    if user:
        return jsonify({'error': 'Username taken'}),400
    user = User(
        username = user_name,
        name = name,
        password = password)
    db.session.add(user)      
    db.session.commit()       
    token=create_access_token(identity=user_name)
    return jsonify({'token': token,'message': 'User created', 'id': user.id}),201

if __name__ == '__main__':
    socketio.run(app)
