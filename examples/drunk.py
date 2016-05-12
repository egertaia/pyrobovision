import cv2
cap = cv2.VideoCapture(0)
p = 3
frames = [cap.read()[1] >> p for j in range(0,2**p)]
while True:
    success, frame = cap.read()
    frames = frames[1:] + [frame >> p]
    avg = sum(frames)
    cv2.imshow('img', avg)
    if cv2.waitKey(1) >= 0: break
