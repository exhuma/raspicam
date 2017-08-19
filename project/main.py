# main.py

from datetime import datetime
from collections import namedtuple

from flask import Flask, render_template, Response
import cv2
import imutils
import numpy as np

from camera import USBCam, PiCamera

Point2D = namedtuple('Point2D', 'x y')
Dimension = namedtuple('Dimension', 'width height')
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


def blit(canvas, image, size: Dimension, offset: Point2D):
    """
    Blits an image onto a canvas at position *offset* with size *size*.
    """
    canvas[offset.y:size.height+offset.y,
           offset.x:size.width + offset.x] = cv2.resize(image, (size.width, size.height))


def combine(original, frame_delta, thresh, modified):
    # make a canvas big enough for 2x2 images of 320x240 and 10px offset
    width = 320 * 2 + 30
    height = 240 * 2 + 30
    canvas = np.zeros((height, width, 3), np.uint8)

    delta_rgb = cv2.cvtColor(frame_delta, cv2.COLOR_GRAY2RGB)
    thresh_rgb = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)

    blit(canvas, original, Dimension(320, 240), Point2D(10, 10))
    blit(canvas, modified, Dimension(320, 240), Point2D(320+20, 10))
    blit(canvas, delta_rgb, Dimension(320, 240), Point2D(10, 240+20))
    blit(canvas, thresh_rgb, Dimension(320, 240), Point2D(320+20, 240+20))

    return canvas


def detect():
    cam = PiCamera()
    generator = cam.frame_generator()

    # XXX for _ in range(100):
    # XXX     # give the cam a chance to warm up
    # XXX     first_frame = next(generator)
    first_frame = next(generator)

    resized = imutils.resize(first_frame, width=500)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    reference = cv2.GaussianBlur(gray, (21, 21), 0)

    for frame in generator:
        text = 'unoccupied'
        resized = imutils.resize(frame, width=500)
        modified = resized.copy()
        current_gray = cv2.cvtColor(modified, cv2.COLOR_BGR2GRAY)

        frame_delta = cv2.absdiff(reference, current_gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        dilated = cv2.dilate(thresh, None, iterations=2)
        contoured, contours, hierarchy = cv2.findContours(
            dilated.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # if cv2.contourArea(contour) < MIN_AREA:
            #     continue
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(modified, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(modified,
                    "Room Status: {}".format(text),
                    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2)
        cv2.putText(modified,
                    datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                    (10, modified.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (0, 0, 255),
                    1)

        combined = combine(
            resized,
            frame_delta,
            thresh,
            modified
        )

        ret, jpeg = cv2.imencode('.jpg', combined)
        output = jpeg.tostring()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + output + b'\r\n\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(detect(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
