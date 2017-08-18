import cv2

cap = cv2.VideoCapture(0)
success, data = cap.read()
assert(success)
print(len(data))
