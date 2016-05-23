import cv2
cap = cv2.VideoCapture(0)

inner_corners = 6, 9 # This is the count of inner corners, change according to the image

while True:
    success, frame = cap.read()
    found, corners = cv2.findChessboardCorners(frame, inner_corners, None, cv2.CALIB_CB_FAST_CHECK )
    if found:
        print "Chessboard corner coordinates are:", corners
    cv2.imshow('img', frame)
    if cv2.waitKey(1) >= 0: break
