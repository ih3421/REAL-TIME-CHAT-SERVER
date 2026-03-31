from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)

@app.route("/login",methods=['POST'])
def login():
    data = request.json  
    user_name = data['username']
    password = hash(data['password'])
    user = User.query.filter_by(username=user_name)
    if user.password== password:
    
    return 
