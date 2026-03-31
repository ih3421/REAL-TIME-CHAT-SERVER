from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import jwt
app = Flask(__name__)
db = SQLAlchemy(app)
key='secret'

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
        payload={ user:user_name,
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
    
    return jsonify({'message': 'User created', 'id': user.id}), 201


    )
    


