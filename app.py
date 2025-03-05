import cv2
import numpy as np
import bcrypt
import webbrowser
import smtplib
import threading
from flask import Flask, request, Response, render_template_string, redirect, url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Sample stored hashed password (Replace with a real database)
stored_password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt())

# Haar cascade classifiers for face & eye detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Email credentials (Replace with actual credentials)
EMAIL_SENDER = "kalaiarasimohanraj4455@gmail.com"
EMAIL_PASSWORD = "ksph gewc ssha scjx"  # Use App Password
EMAIL_RECEIVER = "kalaiyarasi4327@gmail.com"
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587  # Use 587 for TLS

# Variables to track login and email status
email_sent = False  
logged_in_email = ""  
video_active = True  # Flag to control video stream

def send_email_alert(to_email):
    """Send an email alert when eyes are detected open."""
    global email_sent
    if email_sent:
        return  # Prevent multiple emails

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = "Eye Detection Alert 🚨"
    body = "Alert! Your eyes have been detected as open during monitoring."
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email alert sent to {to_email}")
        email_sent = True  # Prevents multiple alerts
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def process_frame(frame):
    """Detects face and eyes, then blurs the background."""
    global logged_in_email, email_sent
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    mask = np.zeros_like(frame)

    for (x, y, w, h) in faces:
        mask[y:y+h, x:x+w] = frame[y:y+h, x:x+w]
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]
        eyes = eye_cascade.detectMultiScale(roi_gray)

        if len(eyes) == 0:
            eye_status = "Eyes Closed"
            color = (0, 0, 255)
        else:
            eye_status = "Eyes Open"
            color = (0, 255, 0)
            send_email_alert(logged_in_email)  # Send email when eyes are open

        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), color, 2)

        cv2.putText(frame, eye_status, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    blurred_frame = cv2.GaussianBlur(frame, (15, 15), 0)
    combined = np.where(mask == 0, blurred_frame, frame)

    return combined

def generate_frames():
    """Start the camera feed and stream video."""
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
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

@app.route('/')
def login_page():
    """Serve the login page."""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login Page</title>
    </head>
    <body>
        <div>
            <h2>Login</h2>
            <form action="/login" method="POST">
                <input type="email" name="email" placeholder="Enter Email" required>
                <input type="password" name="password" placeholder="Enter Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/login', methods=['POST'])
def login():
    """Handle login requests."""
    global logged_in_email, email_sent
    email = request.form['email']
    password = request.form['password'].encode('utf-8')

    if email and bcrypt.checkpw(password, stored_password_hash):
        logged_in_email = email
        email_sent = False
        return redirect(url_for('dashboard'))  # Redirect to dashboard after login
    else:
        return "❌ Invalid Credentials. Try Again."

@app.route('/dashboard')
def dashboard():
    """Display the dashboard with the camera feed."""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - Camera Feed</title>
    </head>
    <body>
        <h2>Live Camera Feed</h2>
        <img src="{{ url_for('video_feed') }}" width="60%">
        <br>
        <button onclick="window.location.href='/stop_video'">Close Video</button>
    </body>
    </html>
    ''')

@app.route('/video_feed')
def video_feed():
    """Serve the live video feed."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_video')
def stop_video():
    """Stop the live video feed."""
    global video_active
    video_active = False
    return redirect(url_for('dashboard'))

def open_browser():
    """Open the default web browser to the login page."""
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=False, port=5000)
