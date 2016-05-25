from threading import Thread, Event
import cv2
from time import time, sleep
import numpy as np


class CameraMaster:
    """docstring for CameraMaster"""
    def __init__(self, target=None):
        self.slaves = {}
        self.target = target
        self.spawnSlaves()

    def spawnSlaves(self):

        for index in range(10):
            temp_camera = cv2.VideoCapture(index)
            success, temp_frame = temp_camera.read()
            sleep(0.05)
            success, temp_frame = temp_camera.read()
            print( 'Camera index {} is returned {}'.format( index,success) )
            camera_id = 'camera_{}'.format(index)
            if success:
                self.slaves[camera_id] = FrameGrabber( camera=temp_camera, motors=self.target)


    @property
    def slaveCount(self):
        return len(self.slaves)

    def getSlavePhoto(self,camera_id,TILE_SIZE = (320,240) ):
        camera = self.slaves.get(camera_id)        
        frame = cv2.resize(camera.frame, TILE_SIZE) 

        return frame


    def getGroupPhoto(self,TILE_SIZE = (320,240)):

        frames = [cv2.resize(grab.frame, TILE_SIZE) for grab in self.slaves.values()]
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

        return last_frame    

    def getSlavesList(self):
        import random
        return list( self.slaves.items() )* random.randint(1,8)

    def setSlaveProperty(self,camera_id,channel,LOWER,UPPER):
        camera = self.slaves.get(camera_id)
        camera.setChannel(channel,LOWER,UPPER)
        
class FrameGrabber(Thread):
    # Set HSV color ranges, this basically means color red regardless of saturation or brightness
    BALL_LOWER = [ 0, 140, 140]
    BALL_UPPER = [10, 255, 255]

    def __init__(self, width=640, height=480, master=None, camera = None, motors=None, key = None):
        Thread.__init__(self)
        self.daemon = True
        self.key = key
        self.camera = camera
        self.motors = motors
        self.width, self.height = width, height
        self.cx, self.cy = width / 2, height
        self.camera.set(3, width)
        self.camera.set(4, height)
        self.camera.set(cv2.CAP_PROP_FPS, 60)
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


    def setChannel(self,channel,LOWER,UPPER):
        index = ['H','S','V'].index(channel)
        self.BALL_LOWER[index] = LOWER
        self.BALL_UPPER[index] = UPPER
    def run(self):
        while self.running:
            self.process_frame()
            self.ready.set()
            if self.master:
                self.master.ready.wait() # Wait until master is ready


    def process_frame(self):
        timestamp_begin = time()

        succes, frame = self.camera.read()

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
        mask = cv2.inRange(hsv, tuple(self.BALL_LOWER), tuple(self.BALL_UPPER))
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
                    self.motors.set(adx, adx, adx)
                else:
                    cv2.putText(frame,"Going left %d" % adx, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
                    self.motors.set(-adx, -adx, -adx)
            else:
                cv2.putText(frame,"Going forward %d" % dy, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
                self.motors.set(100 + dy, -100 -dy, dx)
        else:
            cv2.putText(frame,"Stopping", (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
            self.motors.set(0, 0, 0)

        cv2.putText(frame,"%.01f fps" % self.fps, (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255,255,255),1)
        #self.last_frame = np.hstack([frame, cutout])
        self.frame = frame
