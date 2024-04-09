# from flask_sqlalchemy import SQLAlchemy
# from flask import Flask
# app = Flask(__name__)

# app.config['SECRET_KEY'] = 'Falgun'
# app.config['UPLOAD_FOLDER'] = 'static/files'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'


# db = SQLAlchemy(app)
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender_user', lazy=True)
#     messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

# class Plates(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     plate_number = db.Column(db.String(20), nullable=False, unique=True)
#     messages = db.relationship('Message', backref='plate', lazy=True)

# class Message(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     receiver_id = db.Column(db.Integer, db.ForeignKey('plates.id'), nullable=False)
#     content = db.Column(db.Text, nullable=False)

#     sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
#     receiver = db.relationship('Plates', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))
