import cv2
from time import sleep
from camera import CameraMaster

for index in range(10):
    temp_camera = cv2.VideoCapture(index)
    sleep(0.05)
    success, temp_frame = temp_camera.read()
    print( 'Camera index {} is returned {}'.format( index,success) )
   