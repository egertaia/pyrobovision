import cv2
import numpy as np
from flask import Flask, render_template, Response, request
from time import time, sleep

try:
    from motors import *
except:
    class MotorThread:
        def __init__(self):            
            self.dx, self.dy = 0, 0
        def start(self):
            print("Wrooom wroom!!!! (no motors found) ")
        def set(self, m1, m2, m3):
            pass

from camera import FrameGrabber



motors = MotorThread()
motors.start()

grab1 = FrameGrabber(motors=motors)
grabbers = [grab1]

for n in range(1, 10):
    # try:
    temp_camera = cv2.VideoCapture(n)
    success, temp_frame = temp_camera.read()
    sleep(0.05)
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

            TILE_SIZE = (320,240)

            frames = [cv2.resize(grab.frame, TILE_SIZE) for grab in grabbers]
            padding = np.zeros((TILE_SIZE[1],TILE_SIZE[0],3))
            if len(frames) > 1:
                frames = frames + [padding] * (len(frames)%2)
            
                last_frame = np.zeros(0) #
                for i in range(len(frames)//2):
                    A,B = frames.pop(),frames.pop()
                    row = np.vstack([
                        cv2.resize(A, TILE_SIZE),
                        cv2.resize(B, TILE_SIZE)
                    ])
                    if not last_frame.size:
                        last_frame = row
                    else:
                        last_frame = np.hstack([last_frame,row])
            else:
                last_frame = frames[0]
                
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
    global grab1 # will nuke later
    
    blH = int(request.form.get('blH')) #int cant be none
    blS = int(request.form.get('blS'))
    blV = int(request.form.get('blV'))
    bhH = int(request.form.get('bhH'))
    bhS = int(request.form.get('bhS'))
    bhV = int(request.form.get('bhV'))
    print ("lower range is now: " , grab1.BALL_LOWER , (blH, blS, blV))
    grab1.BALL_LOWER = (blH, blS, blV)
    print("Higher range is now: " ,grab1.BALL_UPPER, (bhH, bhS, bhV))
    grab1.BALL_UPPER = (bhH, bhS, bhV)
    return "OK" 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)