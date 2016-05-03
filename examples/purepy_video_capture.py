#!/usr/bin/env python3

"""
Webcam picture capture using only python
and feeding captured picture buffers directly to numpy and cv2
without any stupid yuv > rgb > hsv converting.

When turning off all the filtering and live prew then the cpu
usage hovers around 5% on my Intel i5 3317U cpu vs alot more
with the cv implementation
"""


from v4l2 import *
import fcntl
import mmap
import select
import time

import cv2
import numpy

webcam = '/dev/video1'

vd = open(webcam, 'rb+', buffering=0)

max_pref = False
preview = True


print(">> get device capabilities")
cp = v4l2_capability()
fcntl.ioctl(vd, VIDIOC_QUERYCAP, cp)

print("Driver:", "".join((chr(c) for c in cp.driver)))
print("Name:", "".join((chr(c) for c in cp.card)))
print("Is a video capture device?", bool(cp.capabilities & V4L2_CAP_VIDEO_CAPTURE))
print("Supports read() call?", bool(cp.capabilities &  V4L2_CAP_READWRITE))
print("Supports streaming?", bool(cp.capabilities & V4L2_CAP_STREAMING))

print(">> device setup")
fmt = v4l2_format()
fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
fcntl.ioctl(vd, VIDIOC_G_FMT, fmt)  # get current settings
print("width:", fmt.fmt.pix.width, "height", fmt.fmt.pix.height)
print("pxfmt:", "V4L2_PIX_FMT_YUYV" if fmt.fmt.pix.pixelformat == V4L2_PIX_FMT_YUYV else fmt.fmt.pix.pixelformat)
print("bytesperline:", fmt.fmt.pix.bytesperline)
print("sizeimage:", fmt.fmt.pix.sizeimage)
fcntl.ioctl(vd, VIDIOC_S_FMT, fmt)  # set whatever default settings we got before

print(">>> streamparam")  ## somewhere in here you can set the camera framerate
parm = v4l2_streamparm()
parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
parm.parm.capture.capability = V4L2_CAP_TIMEPERFRAME
fcntl.ioctl(vd, VIDIOC_G_PARM, parm) # get current camera settings
# set framerate to 60fps or 1/60
parm.parm.capture.timeperframe.numerator = 1
parm.parm.capture.timeperframe.denominator = 60
print("parm.capture.timeperframe: 1/60 fps")
fcntl.ioctl(vd, VIDIOC_S_PARM, parm)  # change camera capture settings

print(">>> control set V4L2_CID_AUTOGAIN = False")
ctrl = v4l2_control()
ctrl.id = V4L2_CID_AUTOGAIN
ctrl.value = 0;
fcntl.ioctl(vd, VIDIOC_S_CTRL, ctrl)

print(">>> control set V4L2_CID_GAIN = 0")
ctrl = v4l2_control()
ctrl.id = V4L2_CID_GAIN
ctrl.value = 0;
fcntl.ioctl(vd, VIDIOC_S_CTRL, ctrl)

print(">> init mmap capture")
req = v4l2_requestbuffers()
req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
req.memory = V4L2_MEMORY_MMAP
req.count = 2  # nr of buffer frames
fcntl.ioctl(vd, VIDIOC_REQBUFS, req)  # tell the driver that we want some buffers 
print("nr of buffers", req.count)

buffers = []

print(">>> VIDIOC_QUERYBUF, mmap, VIDIOC_QBUF")
for ind in range(req.count):
    # setup a buffer
    buf = v4l2_buffer()
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
    buf.memory = V4L2_MEMORY_MMAP
    buf.index = ind
    fcntl.ioctl(vd, VIDIOC_QUERYBUF, buf)

    mm = mmap.mmap(vd.fileno(), buf.length, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=buf.m.offset)
    buffers.append(mm)

    # queue the buffer for capture
    fcntl.ioctl(vd, VIDIOC_QBUF, buf)


print(">> Start streaming")
buf_type = v4l2_buf_type(V4L2_BUF_TYPE_VIDEO_CAPTURE)
fcntl.ioctl(vd, VIDIOC_STREAMON, buf_type)

# duno
print(">> Capture image")
t0 = time.time()
max_t = 1
ready_to_read, ready_to_write, in_error = ([], [], [])
print(">>> select")
while len(ready_to_read) == 0 and time.time() - t0 < max_t:
    ready_to_read, ready_to_write, in_error = select.select([vd], [], [], max_t)


print(">>> download buffers from camera")

frames = 0
fps = 0
timestamp = time.time()

while True:
    frames += 1
    timestamp_begin = time.time()
    if frames > 10:
        time.time()
        fps = frames / (timestamp_begin - timestamp)
        print("fps:", "%.01f" % (fps), end="\r")
        frames = 0
        timestamp = timestamp_begin

    # get image from the driver queue
    buf = v4l2_buffer()
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
    buf.memory = V4L2_MEMORY_MMAP
    fcntl.ioctl(vd, VIDIOC_DQBUF, buf)  
    mm = buffers[buf.index]
    
    # print first few pixels in gray scale part of yuvv format packed data
    #print(" ".join(("{0:08b}".format(mm[x]) for x in range(0,16,2))))

    # gives us a V part of YUYV image
    #v = numpy.asarray(mm, numpy.uint8)[3::4].repeat(6).reshape(((480, 640, 3)))

    # gives us a U part of YUYV image
    #u = numpy.asarray(mm, numpy.uint8)[1::4].repeat(6).reshape(((480, 640, 3)))

    
    uv = numpy.asarray(mm, numpy.uint8)[1::2].reshape(((480, 320, 2)))
    uv = numpy.repeat(uv, 2, axis=1)  # kills perf but fixes aspect ratio
    #blurred_uv = cv2.blur(uv, (4,4))  # kills perf but smooths the picture
    blurred_uv = uv
    mask = cv2.inRange(blurred_uv, (60, 160), (90, 255))  ## FILTER THE COLORS!!
    #mask = cv2.dilate(mask, None, iterations=2) # kills perf, removes sparkling


    im2, contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## PERF KILLER!!!!
    # kills alot of perf, gives us a grayscale (Y part of YUYV) picture
    # probably perf gets killed by cache misses that this extra processing introduces
    #frame = luma = numpy.asarray(mm, numpy.uint8)[0::2].repeat(3).reshape(((480, 640, 3)))
    frame = numpy.asarray(mm, numpy.uint8).reshape((480, 640, 2))
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUYV)
    #frame = mask  # draw balls on the mask when grayscale pictre is disabled
    
    if len(contours) > 0:
        c = max(contours, key=cv2.contourArea)  # get the biggest circle
        (x, y), radius = cv2.minEnclosingCircle(c)
        if radius > 10:
            distance = round((1/radius)*100*11.35, 2)
            cv2.circle(frame, (int(x),int(y)), int(radius), (255, 255, 255), 5)
            cv2.putText(frame, str(radius), (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255,255,255),1)

    cv2.putText(frame,"fps: %.01f" % (fps), (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,255,255),1)

    cv2.imshow("Got balls?", frame)

    # duno, some cv2 shit
    if cv2.waitKey(1) >= 0:
        break
    

    fcntl.ioctl(vd, VIDIOC_QBUF, buf)  # requeue the buffer

print(">> Stop streaming")
fcntl.ioctl(vd, VIDIOC_STREAMOFF, buf_type)
vd.close()

print(">> END OF LINE")
