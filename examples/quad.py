
"""
Example how to capture video feed from four cameras and
perform shape recognition on all of them
"""

import cv2
import numpy as np
import threading
from time import time

BALL_LOWER = ( 0, 140, 140)
BALL_UPPER = (10, 255, 255)

class FrameGrabber(threading.Thread):
    def __init__(self, index=0, width=640, height=480, master=None):
        threading.Thread.__init__(self)
        self.cap = cv2.VideoCapture(index)
        self.width, self.height = width, height
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
        self.ready = threading.Event() # Used for thread synchronization
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
        mask = cv2.inRange(hsv, BALL_LOWER, BALL_UPPER)
        mask = cv2.dilate(mask, None, iterations=2)
        cutout = cv2.bitwise_and(frame,frame, mask=mask)
        cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            (x, y), radius = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
            if radius > 10:
                cv2.circle(frame, center, int(radius), (0, 0, 255), 5)
                distance = round((1/radius)*100*11.35, 2)
                cv2.putText(frame, str(radius), (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255,255,255),1)

        self.frame = frame


grab1 = FrameGrabber()
grab2 = FrameGrabber(index=1, master=grab1)
grab3 = FrameGrabber(index=2, master=grab1)
grab4 = FrameGrabber(index=3, master=grab1)

from time import sleep
sleep(2)

while True:
    grab1.ready.wait()
    cv2.imshow('img', np.vstack([
        np.hstack([
            cv2.resize(grab1.frame, (320,240)),
            cv2.resize(grab2.frame, (320,240))
        ]),
        np.hstack([
            cv2.resize(grab4.frame, (320,240)),
            cv2.resize(grab3.frame, (320,240))
        ])
    ]))
    if cv2.waitKey(1) >= 0:
        break

grab1.running = False
grab2.running = False
grab3.running = False
grab4.running = False

grab1.join()
grab2.join()
grab3.join()
grab4.join()

cv2.destroyAllWindows()

