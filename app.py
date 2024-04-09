from flask import Flask, render_template, Response,jsonify,request,session,redirect,url_for,json

#FlaskForm--> it is required to receive input from the user
# Whether uploading a video file  to our object detection model

from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy

import numpy as np


from wtforms import FileField, SubmitField,StringField,DecimalRangeField,IntegerRangeField
from werkzeug.utils import secure_filename
from wtforms.validators import InputRequired,NumberRange
import os


# Required to run the YOLOv8 model
import cv2

dictionary={}
# YOLO_Video is the python file which contains the code for our object detection model
#Video Detection is the Function which performs Object Detection on Input Video
from YOLO_Video import video_detection
from server import main as start_server
from client import start_client
app = Flask(__name__)

app.config['SECRET_KEY'] = 'Falgun'
app.config['UPLOAD_FOLDER'] = 'static/files'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)



class Plates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
 
from datetime import datetime


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)

   
#Use FlaskForm to get input video file  from user
class UploadFileForm(FlaskForm):
    #We store the uploaded video file path in the FileField in the variable file
    #We have added validators to make sure the user inputs the video in the valid format  and user does upload the
    #video when prompted to do so
    file = FileField("File",validators=[InputRequired()])
    submit = SubmitField("Run")


def generate_frames(path_x=''):
    # Call video_detection function to get the generator
    yolo_output = video_detection(path_x)

    
    # Iterate over the generator
    for output in yolo_output:
        # Check the type of the yielded output
        if isinstance(output, np.ndarray):
            # If it's a frame, encode it and yield as a multipart frame
            ref, buffer = cv2.imencode('.jpg', output)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        elif isinstance(output, dict):
            with app.app_context():
                    Plates.query.delete()
                    for car_id, data in output.items():
                        plate = Plates(license_plate=data['licence_plate_number'])
                        db.session.add(plate)
                    db.session.commit() 
                    


def generate_frames_web(path_x):
    yolo_output = video_detection(path_x)
    for detection_ in yolo_output:
        ref,buffer=cv2.imencode('.jpg',detection_)

        frame=buffer.tobytes()
        yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame +b'\r\n')

@app.route('/', methods=['GET','POST'])
@app.route('/home', methods=['GET','POST'])
def home():
    session.clear()
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user is None:
            # Create a new user if not present in the database
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        userId=user.id
        print(userId)
        session['username']=username
        session['userId']=userId
        print(session['userId'])
        session['license_final']={}
        session['helloworld']=True
        print(username,user.id)
        return redirect(url_for('front'))
    return render_template('indexproject.html')


@app.route('/store_username', methods=['POST'])
def store_username():
    username = request.form['username']  # Get the username from the request data
    user = User.query.filter_by(username=username).first()
    if user is None:
        print(username)
        # Create a new user if not present in the database
        user = User(username=username)
        print(user)
        db.session.add(user)
        print("half")
        db.session.commit()
        print("full")

        return 'Username stored successfully'
    else:
        return "username already stored"


def insert_or_append_message(sender_id, receiver_id, message_data):
    existing_message = Message.query.filter_by(sender_id=sender_id, receiver_id=receiver_id).first()
    if existing_message:
        existing_data = json.loads(existing_message.text)
        new_index=len(existing_data)+1
        existing_data[new_index] = message_data
        existing_message.text = json.dumps(existing_data)
    else:
        # If no entry exists, create a new message entry
        new_message = Message(sender_id=sender_id, receiver_id=receiver_id, data=json.dumps([message_data]))
        db.session.add(new_message)
    db.session.commit()


@app.route('/send_message', methods=['POST'])
def send_message():
    recipient_id = request.form['recipient_id']  # Get the recipient ID (license plate)
    print(recipient_id)
    content = request.form['content']  # Get the message content
    print(content)
    sender_id = session.get('userId')  # Get the sender ID from the session
    print(sender_id)
    # Assuming you have logic to determine the category (e.g., 'a') based on sender_id
    category = 'a'  # Replace with your logic
    # Prepare the message data
    message_data = [category,content,str(datetime.now())]
    insert_or_append_message(sender_id, recipient_id, message_data)
    # Here, you can store the message_data in the database or perform any other operations
    return jsonify({'message': 'Message sent successfully'})


@app.route('/view_messages/<int:recipient_id>')
def view_messages(recipient_id):
    messages = Message.query.filter_by(recipient_id=recipient_id).all()
    return render_template('messages.html', messages=messages)


@app.route("/webcam", methods=['GET','POST'])
def webcam():
    session.clear()
    return render_template('ui.html')

@app.route('/start_server_route', methods=['POST'])
def start_server_route():
    # Execute the server startup code from server.py
     if 'helloworld' in session and session['helloworld'] is True:
        # If condition is met, execute the server startup code from server.py
        print("Server started successfully")
        start_server()
        session['helloworld']=False
    # return jsonify({'message': 'Server started successfully'})

@app.route('/start_client_route', methods=['POST'])
def start_client_route():
    
    start_client()
    print("client started successfully")
    return 'client started successfully'  # Return

   
    # return jsonify({'message': 'Server started successfully'})


@app.route('/front', methods=['GET','POST'])
def front():
    # Upload File Form: Create an instance for the Upload File Form
    form = UploadFileForm()
    if form.validate_on_submit():
        # Our uploaded video file path is saved here
        file = form.file.data
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                               secure_filename(file.filename)))  # Then save the file
        # Use session storage to save video file path
        session['video_path'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'],
                                             secure_filename(file.filename))


        
        # print(session.get('license_final'))
       
    print(dictionary)
    print(".......palgnun")
    return render_template('videoprojectnew.html', form=form)



@app.route('/video')
def video():
    #return Response(generate_frames(path_x='static/files/bikes.mp4'), mimetype='multipart/x-mixed-replace; boundary=frame')
    print("He")
    return Response(generate_frames(path_x = session.get('video_path', None)),mimetype='multipart/x-mixed-replace; boundary=frame' )

# To display the Output Video on Webcam page

@app.route('/get_data', methods=['GET'])
def get_data():
    # Query the database to fetch all data
    data = Plates.query.all()

    # Construct a list of dictionaries with id and license_plate
    response_data = [{'id': item.id, 'license_plate': item.license_plate} for item in data]

    # Return the JSON response
    return jsonify(response_data)

@app.route('/webapp')
def webapp():
    print("she")
    #return Response(generate_frames(path_x = session.get('video_path', None),conf_=round(float(session.get('conf_', None))/100,2)),mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(generate_frames_web(path_x=0), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)