from flask import Flask, render_template, Response,jsonify,request,session,redirect,url_for,json

#FlaskForm--> it is required to receive input from the user
# Whether uploading a video file  to our object detection model

from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy

import numpy as np
from sqlalchemy import JSON

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
    s_messages = db.Column(JSON)
    r_messages = db.Column(JSON)
   
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
        Plates.query.delete()
        print(username,user.id)
        return redirect(url_for('front'))
    return render_template('indexproject.html')


@app.route('/store_username', methods=['POST'])
def store_username():
    username = request.form['username']  
    user = User.query.filter_by(username=username).first()
    if user is None:
        print(username)
        user = User(username=username)
        print(user)
        db.session.add(user)
        print("half")
        db.session.commit()
        print("full")

        return 'Username stored successfully'
    else:
        return "username already stored"


def insert_or_append_message(sender_id, receiver_id, s_message_data,r_message_data):
    s_existing_message = Message.query.filter_by(sender_id=sender_id, receiver_id=receiver_id).first()
    if s_existing_message:
        print("Exists")
        print(s_existing_message)
        print(s_existing_message.s_messages)
        if s_existing_message.s_messages:
            existing_data = json.loads(s_existing_message.s_messages)
            new_index=len(existing_data)
            existing_data[str(new_index)] = s_message_data
            s_existing_message.s_messages = json.dumps(existing_data)
        else:
            print("chammak chello")
            s_data={0:s_message_data}
            s_existing_message.s_messages = json.dumps(s_data)
    else:
        print("not exists")
        s_data={0:s_message_data}
        new_message = new_message = Message(sender_id=sender_id, receiver_id=receiver_id,s_messages=json.dumps(s_data))
        db.session.add(new_message)
    db.session.commit()

    r_existing_message = Message.query.filter_by(sender_id=receiver_id, receiver_id=sender_id).first()
    if r_existing_message:
        print("Exists")
        if r_existing_message.r_messages:
            existing_data = json.loads(r_existing_message.r_messages)
            new_index=len(existing_data)
            existing_data[str(new_index)] = r_message_data
            r_existing_message.r_messages = json.dumps(existing_data)
        else:
            r_data={0:r_message_data}
            r_existing_message.r_messages = json.dumps(r_data)
    else:
        print("not exists")
        r_data={0:r_message_data}
        new_message = Message(sender_id=receiver_id, receiver_id=sender_id,r_messages=json.dumps(r_data))
        db.session.add(new_message)
    db.session.commit()
    



@app.route('/send_message', methods=['POST'])
def send_message():
    receiver_name = request.form['receiver_name'] 
    receipient = User.query.filter_by(username=receiver_name).first()
    content = request.form['content']  
    sender_id = session.get('userId')  
    print(sender_id)
    print(receipient.id)
    print(content) 
    s_message_data = ['a',content,str(datetime.now())]
    r_message_data = ['b',content,str(datetime.now())]
    insert_or_append_message(sender_id, receipient.id, s_message_data,r_message_data)
    return jsonify({'message': 'Message sent successfully'})




@app.route('/view_messages/<int:recipient_id>')
def view_messages(recipient_id):
    messages = Message.query.filter_by(recipient_id=recipient_id).all()
    return render_template('messages.html', messages=messages)


@app.route("/webcam", methods=['GET','POST'])
def webcam():
    session.clear()
    return render_template('ui.html')



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
    data = Plates.query.all()
    
    username = session['username']

    user_id=session['userId']

    print(username,user_id,data)
    response_data = {'data': [{'id': item.id, 'license_plate': item.license_plate} for item in data], 'username': username,'user_id':user_id}

    return jsonify(response_data)

@app.route('/get_chats', methods=['GET'])
def get_chats():
    userId =session['userId']
    print(userId)
    data = Message.query.filter_by(sender_id=userId).all()
    print(data)
    TOTAL=[]
    if data:
        for convo in data:
            convo_king = User.query.filter_by(id=convo.receiver_id).first().username

            total_chats_merged=[]

            sender_messages_filtered=[]
            
            if convo.s_messages:
                parsed_dict = json.loads(convo.s_messages) 
                for key,val in parsed_dict.items():
                    message=val[1]
                    timestamp=val[2]
                    category=val[0]
                    c={'category':category,'message':message,'timestamp':timestamp}
                    sender_messages_filtered.append(c)
            receiver_messages_filtered=[]
            if convo.r_messages:
                parsed_dict2 = json.loads(convo.r_messages) 
                for key,val in parsed_dict2.items():
                    message=val[1]
                    timestamp=val[2]
                    category=val[0]
                    c={'category':category,'message':message,'timestamp':timestamp}
                    receiver_messages_filtered.append(c)

            total_chats_merged = []

            total_chats_merged.extend(sender_messages_filtered)
            total_chats_merged.extend(receiver_messages_filtered)

            total_chats_merged.sort(key=lambda x: x['timestamp'])


            final_chat_messages = [{'category': message['category'], 'message': message['message']} for message in total_chats_merged]

            usha  = {'user':convo_king,'list':final_chat_messages}
            TOTAL.append(usha)

    else:
        return []

    print(TOTAL)

    for i in TOTAL:
        username=i['user']
        liste=i['list']
        for k in liste:
            print(k['category'])
            print(k['message'])


    
    return TOTAL




@app.route('/webapp')
def webapp():
    print("she")
    #return Response(generate_frames(path_x = session.get('video_path', None),conf_=round(float(session.get('conf_', None))/100,2)),mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(generate_frames_web(path_x=0), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)