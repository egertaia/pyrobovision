import cv2
import numpy as np
import signal
import sys
from flask import Flask, render_template, Response, request
from collections import deque
from datetime import datetime
from time import time, sleep
from threading import Thread, Event

try:
    from PyMata.pymata import PyMata

    # Motor pins on Arduino
    MOTOR_1_PWM = 2
    MOTOR_1_A   = 3
    MOTOR_1_B   = 4
    MOTOR_2_PWM = 5
    MOTOR_2_A   = 6
    MOTOR_2_B   = 7
    MOTOR_3_PWM = 8
    MOTOR_3_A   = 9
    MOTOR_3_B   = 10

    def signal_handler(sig, frame):
        board.reset()

    # Here we initialize the motor pins on Arduino
    board = PyMata(bluetooth=False)
    signal.signal(signal.SIGINT, signal_handler)
    board.set_pin_mode(MOTOR_1_PWM, board.PWM,    board.DIGITAL)
    board.set_pin_mode(MOTOR_1_A,   board.OUTPUT, board.DIGITAL)
    board.set_pin_mode(MOTOR_1_B,   board.OUTPUT, board.DIGITAL)
    board.set_pin_mode(MOTOR_2_PWM, board.PWM,    board.DIGITAL)
    board.set_pin_mode(MOTOR_2_A,   board.OUTPUT, board.DIGITAL)
    board.set_pin_mode(MOTOR_2_B,   board.OUTPUT, board.DIGITAL)
    board.set_pin_mode(MOTOR_3_PWM, board.PWM,    board.DIGITAL)
    board.set_pin_mode(MOTOR_3_A,   board.OUTPUT, board.DIGITAL)
    board.set_pin_mode(MOTOR_3_B,   board.OUTPUT, board.DIGITAL)

    class MotorThread(Thread):
        def __init__(self):
            Thread.__init__(self)
            self.daemon = True
            self.lock = Event()
            self.set(0, 0, 0)

        def set(self, m1, m2, m3):
            self.m1, self.m2, self.m3 = m1, m2, m3
            self.lock.set()

        def run(self):
            while True:
                # Reset all direction pins to avoid damaging H-bridges
                board.digital_write(MOTOR_1_B, 0)
                board.digital_write(MOTOR_1_A, 0)
                board.digital_write(MOTOR_2_B, 0)
                board.digital_write(MOTOR_2_A, 0)
                board.digital_write(MOTOR_3_B, 0)
                board.digital_write(MOTOR_3_A, 0)

                # Set duty cycle
                board.analog_write(MOTOR_1_PWM, int(abs(self.m1) + 25) if self.m1 else 0)
                board.analog_write(MOTOR_2_PWM, int(abs(self.m2) + 25) if self.m2 else 0)
                board.analog_write(MOTOR_3_PWM, int(abs(self.m3) + 25) if self.m3 else 0)

                # Set directions
                board.digital_write(MOTOR_1_A, self.m1 < 0)
                board.digital_write(MOTOR_1_B, self.m1 > 0)
                board.digital_write(MOTOR_2_A, self.m2 < 0)
                board.digital_write(MOTOR_2_B, self.m2 > 0)
                board.digital_write(MOTOR_3_A, self.m3 < 0)
                board.digital_write(MOTOR_3_B, self.m3 > 0)
                self.lock.wait()
                self.lock.clear()

except:
    class MotorThread:
        def __init__(self):            
            self.dx, self.dy = 0, 0
        def start(self):
            print("Wrooom wroom!!!! (no motors found) ")
        def set(self, m1, m2, m3):
            pass

class FrameGrabber(Thread):
    # Set HSV color ranges, this basically means color red regardless of saturation or brightness
    BALL_LOWER = ( 0, 140, 140)
    BALL_UPPER = (10, 255, 255)

    def __init__(self, width=640, height=480, index=0, master=None, cap = cv2.VideoCapture(0)):
        Thread.__init__(self)
        self.daemon = True
        self.cap = cap
        self.width, self.height = width, height
        self.cx, self.cy = width / 2, height
        self.cap.set(3, width)
        self.cap.set(4, height)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        self.slaves = set()
        self.master = master
        if master:
            master.slaves.add(self)
        self.timestamp = time()
        self.frames = 0
        self.fps = 0
        self.running = True
        self.ready = Event() # Used for thread synchronization
        self.ready.clear()
        self.start()



    def run(self):
        while self.running:
            self.process_frame()
            self.ready.set()
            if self.master:
                self.master.ready.wait() # Wait until master is ready


    def process_frame(self):
        timestamp_begin = time()

        succes, frame = self.cap.read()

        self.frames += 1
        timestamp_begin = time()
        if self.frames > 10:
            self.fps = self.frames / (timestamp_begin - self.timestamp)
            self.frames = 0
            self.timestamp = timestamp_begin
        cv2.putText(frame,"%dx%d@%.01fHz" % (self.width, self.height, self.fps),
            (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,255,255),1)

        blurred = cv2.blur(frame, (4,4))
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV) # Convert red, green and blue to hue, saturation and brightness
        mask = cv2.inRange(hsv, self.BALL_LOWER, self.BALL_UPPER)
        mask = cv2.dilate(mask, None, iterations=2)
        cutout = cv2.bitwise_and(frame,frame, mask=mask)
        im2, cnts, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        distance = None

        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            (x, y), radius = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
            if radius > 10:
                cv2.circle(frame, center, int(radius), (0, 0, 255), 5)
                distance = round((1/radius)*100*11.35, 2)
                cv2.putText(frame, str(radius), (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255,255,255),1)

        if distance:
            dx = (x - self.cx) / 2.0
            dy = (self.cy - y) / 3.0
            adx = abs(dx)

            if adx > 100:
                if dx > 0:
                    cv2.putText(frame,"Going right %d" % adx, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
                    motors.set(adx, adx, adx)
                else:
                    cv2.putText(frame,"Going left %d" % adx, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
                    motors.set(-adx, -adx, -adx)
            else:
                cv2.putText(frame,"Going forward %d" % dy, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
                motors.set(100 + dy, -100 -dy, dx)
        else:
            cv2.putText(frame,"Stopping", (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
            motors.set(0, 0, 0)

        cv2.putText(frame,"%.01f fps" % self.fps, (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
        #self.last_frame = np.hstack([frame, cutout])
        self.frame = frame



motors = MotorThread()
motors.start()

grab1 = FrameGrabber()
grabbers = [grab1]

for n in range(1, 10):
    # try:
    temp_camera = cv2.VideoCapture(n)
    success, temp_frame = temp_camera.read()
    sleep(0.25)
    success, temp_frame = temp_camera.read()
    
    print( success, n)
    if success:
        grabbers.append( FrameGrabber(index=n, master=grab1, cap=temp_camera))
    # except:
        # br/eak

print('grabber count',len(grabbers))    

app = Flask(__name__)

@app.route('/video')
def video():
    def generator():
        while True:
            grab1.ready.wait()

            frames = [cv2.resize(grab.frame, (320,240)) for grab in grabbers]
            padding = np.zeros((240,320,3))
            frames = frames + [padding] * (len(frames)%2)
            
            last_frame = np.zeros(0) #
            for i in range(len(frames)//2):
                A,B = frames.pop(),frames.pop()
                row = np.vstack([
                    cv2.resize(A, (320,240)),
                    cv2.resize(B, (320,240))
                ])
                if not last_frame.size:
                    last_frame = row
                else:
                    last_frame = np.hstack([last_frame,row])

            


            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(0.05)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('sliders.html')

# static files for js and css
@app.route('/nouislider.css')
def nouisliderCSS():
    return render_template('nouislider.css')
@app.route('/nouislider.js')
def nouisliderJS():
    return render_template('nouislider.js')

@app.route('/camera/config', methods=['get', 'post'])
def config():
    global grabber
    blH = int(request.form.get('blH')) #int cant be none
    blS = int(request.form.get('blS'))
    blV = int(request.form.get('blV'))
    bhH = int(request.form.get('bhH'))
    bhS = int(request.form.get('bhS'))
    bhV = int(request.form.get('bhV'))
    print ("lower range is now: " , grabber.BALL_LOWER , (blH, blS, blV))
    grabber.BALL_LOWER = (blH, blS, blV)
    print("Higher range is now: " ,grabber.BALL_UPPER, (bhH, bhS, bhV))
    grabber.BALL_UPPER = (bhH, bhS, bhV)
    return "OK" 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)