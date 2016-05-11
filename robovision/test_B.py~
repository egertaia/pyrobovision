import cv2
from time import sleep
import test_import_B

for index in range(10):
    temp_camera = cv2.VideoCapture(index)
    sleep(0.05)
    success, temp_frame = temp_camera.read()
    print( 'Camera index {} is returned {}'.format( index,success) )
   
