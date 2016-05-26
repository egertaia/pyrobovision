import cv2
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

from camera import CameraMaster

motors = MotorThread()
motors.start()

cameras = CameraMaster(target=motors)
print('grabber count', cameras.slaveCount)    

app = Flask(__name__)

@app.route('/video')
def video_combined():
    def generator():
        while True:
            last_frame = cameras.getGroupPhoto()
                
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(0.05)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video/<path:camera_id>')
def video(camera_id):
    def generator():
        while True:
            last_frame = cameras.getSlavePhoto(camera_id)
                
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(0.05)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('main.html',camera_list = cameras.getSlavesList())


# static files for js and css
@app.route('/nouislider.css')
def nouisliderCSS():
    return render_template('nouislider.css')
@app.route('/nouislider.js')
def nouisliderJS():
    return render_template('nouislider.js')

@app.route('/config/camera/<path:camera_id>', methods=['get', 'post'])
def config(camera_id):
    channel = request.form.get('channel')
    LOWER     = int(request.form.get('LOWER'))
    UPPER     = int(request.form.get('UPPER'))
    
    cameras.setSlaveProperty(camera_id,channel,LOWER,UPPER)
    return 'Mkay, yes, a response, I guess I can do that.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)
    print("surin")
    del cameras