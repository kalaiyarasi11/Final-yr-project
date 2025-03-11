import cv2
import numpy as np
import bcrypt
import webbrowser
import smtplib
import threading
import time
import matplotlib.pyplot as plt
from flask import Flask, request, Response, render_template_string, redirect, url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import deque

app = Flask(__name__)

stored_password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt())

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

EMAIL_SENDER = "kalaiarasimohanraj4455@gmail.com"
EMAIL_PASSWORD = "ksph gewc ssha scjx"
EMAIL_RECEIVER = "kalaiyarasi4327@gmail.com"
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

email_sent = False
logged_in_email = ""
video_active = False
prev_eye_position = None

eye_movements = deque(maxlen=20)
blink_rates = deque(maxlen=20)

def send_email_alert(to_email, message):
    global email_sent
    if email_sent:
        return
    
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = "Eye Movement Alert 🚨"
    msg.attach(MIMEText(message, "plain"))
    
    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        print(f"✅ Email alert sent to {to_email}")
        email_sent = True
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def detect_eye_movement(eyes):
    global prev_eye_position
    if len(eyes) == 2:
        left_eye, right_eye = eyes
        avg_x = (left_eye[0] + right_eye[0]) / 2
        
        if prev_eye_position is not None:
            if avg_x < prev_eye_position - 5:
                movement = "Looking Left"
            elif avg_x > prev_eye_position + 5:
                movement = "Looking Right"
            else:
                movement = "Looking Straight"
        else:
            movement = "Looking Straight"
        
        prev_eye_position = avg_x
        eye_movements.append(movement)
        return movement
    return "Eyes Detected"

def process_frame(frame):
    global logged_in_email, email_sent
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        movement = detect_eye_movement(eyes)
        
        eye_status = "Both Eyes Opened" if len(eyes) == 2 else ("One Eye Opened" if len(eyes) == 1 else "Eyes Closed")
        color = (0, 255, 0) if len(eyes) > 0 else (0, 0, 255)
        
        cv2.putText(frame, eye_status, (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(frame, movement, (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        if movement != "Looking Straight":
            send_email_alert(logged_in_email, f"Alert! Eye movement detected: {movement}")
        
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)
            cv2.circle(roi_color, (ex + ew // 2, ey + eh // 2), 4, (255, 255, 0), -1)
    
    return frame

def generate_frames():
    global video_active
    cap = cv2.VideoCapture(0)
    while video_active:
        success, frame = cap.read()
        if not success:
            break
        else:
            processed_frame = process_frame(frame)
            _, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

@app.route('/')
def login_page():
    return render_template_string('''
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f4f4f4;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            width: 300px;
        }
        h2 {
            margin-bottom: 15px;
            color: #333;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: black;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background-color: #333;
        }
    </style>
    
    <div class="login-container">
        <h2>Login Form</h2>
        <form action="/login" method="post">
            <input type="email" name="email" placeholder="Enter Email" required>
            <input type="password" name="password" placeholder="Enter Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
    ''')


@app.route('/login', methods=['POST'])
def login():
    global logged_in_email, email_sent
    email = request.form['email']
    password = request.form['password'].encode('utf-8')
    
    if bcrypt.checkpw(password, stored_password_hash):
        logged_in_email = email
        email_sent = False
        return redirect(url_for('home'))
    else:
        return "❌ Invalid Credentials. Try Again."

@app.route('/home')
def home():
    return render_template_string('''
    <h1 style="text-align: center; margin-bottom: 50px;">EYE MOVEMENT TRACKING SYSTEM</h1>

<div style="display: flex; justify-content: center; gap: 15px; padding: 15px; border: 2px solid black; width: fit-content; margin: 0 auto; border-radius: 8px;">
    <button onclick="window.location.href='/start_video'" style="padding: 10px 20px; background-color: black; color: white; border: none; border-radius: 4px; cursor: pointer;">
        View Live Camera Feed
    </button>
    <button onclick="window.location.href='/dashboard'" style="padding: 10px 20px; background-color: black; color: white; border: none; border-radius: 4px; cursor: pointer;">
        View Dashboard
    </button>
</div>

    ''')

@app.route('/start_video')
def start_video():
    global video_active
    video_active = True
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template_string('''
    <h2>Eye Movement Tracking System</h2>
    <img src="{{ url_for('video_feed') }}" width="60%">
    
    <img src="{{ url_for('graph') }}" width="60%">
    
    <button onclick="window.location.href='/stop_video'">Close Video</button>
    ''')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_video')
def stop_video():
    global video_active
    video_active = False
    return redirect(url_for('home'))

@app.route('/graph')
def graph():
    plt.figure(figsize=(6, 4))
    plt.plot(list(eye_movements), marker='o', linestyle='-')
    plt.title('Eye Movement Trend')
    plt.xlabel('Time')
    plt.ylabel('Eye Position')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig('graph.png')
    return redirect('/graph.png')

@app.route('/graph.png')
def serve_graph():
    return open('graph.png', 'rb').read()

def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=False, port=5000)
