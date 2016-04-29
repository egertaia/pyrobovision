import cv2
import numpy as np
import signal
import sys
from flask import Flask, render_template, Response
from collections import deque
from datetime import datetime
from time import time, sleep
from threading import Thread, Event
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

class FrameGrabber(Thread):
    # Set HSV color ranges, this basically means color red regardless of saturation or brightness
    BALL_LOWER = ( 0, 140, 140)
    BALL_UPPER = (10, 255, 255)

    def __init__(self, width=640, height=480):
        Thread.__init__(self)
        self.daemon = True
        self.video = cv2.VideoCapture(0)

        # PS3 eye config:
        self.video.set(3, width)             # Set capture width to 640px
        self.video.set(4, height)            # Set capture height to 480px
        self.video.set(cv2.CAP_PROP_FPS, 60) # Set framerate to 60 fps

        self.cx, self.cy = width / 2, height
        self.timestamp = time()
        self.frames = 0
        self.fps = 0
        self.last_frame = None

    def run(self):
        while True:
            self.frames += 1
            timestamp_begin = time()
            if self.frames > 10:
                self.fps = self.frames / (timestamp_begin - self.timestamp)
                self.frames = 0
                self.timestamp = timestamp_begin

            success, frame = self.video.read() # Grab another frame from the camera
            blurred = cv2.blur(frame, (4,4))
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV) # Convert red, green and blue to hue, saturation and brightness
            mask = cv2.inRange(hsv, self.BALL_LOWER, self.BALL_UPPER)
            mask = cv2.dilate(mask, None, iterations=2)
            cutout = cv2.bitwise_and(frame,frame, mask=mask)
            cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

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
            self.last_frame = np.hstack([frame, cutout])

motors = MotorThread()
motors.start()

grabber = FrameGrabber()
grabber.start()

app = Flask(__name__)

@app.route('/')
def index():
    def generator():
        while True:
            if grabber.last_frame != None:
                ret, jpeg = cv2.imencode('.jpg', grabber.last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(0.05)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)
