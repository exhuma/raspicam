# main.py

from collections import namedtuple
from datetime import datetime
import logging

from flask import Flask, render_template, Response
import cv2
import numpy as np

from camera import USBCam, PiCamera

LOG = logging.getLogger(__name__)
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


def combine(reference, frame_delta, dilated, modified):
    # make a canvas big enough for 2x2 images of 320x240 and 10px offset
    width = 320 * 2 + 30
    height = 240 * 2 + 30
    canvas = np.zeros((height, width, 3), np.uint8)

    reference_rgb = cv2.cvtColor(reference, cv2.COLOR_GRAY2RGB)
    delta_rgb = cv2.cvtColor(frame_delta, cv2.COLOR_GRAY2RGB)
    dilated_rgb = cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB)

    blit(canvas, reference_rgb, Dimension(320, 240), Point2D(10, 10))
    blit(canvas, modified, Dimension(320, 240), Point2D(320+20, 10))
    blit(canvas, delta_rgb, Dimension(320, 240), Point2D(10, 240+20))
    blit(canvas, dilated_rgb, Dimension(320, 240), Point2D(320+20, 240+20))

    return canvas


def add_text(image, header, footer):
    height, width, channels = image.shape

    title_offset = 20
    new_height = height + (2 * title_offset)
    canvas = np.zeros((new_height, width, channels), np.uint8)

    blit(canvas, image, Dimension(width, height), Point2D(0, title_offset))

    cv2.putText(canvas,
                header,
                (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2)
    cv2.putText(canvas,
                footer,
                (10, canvas.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1)

    return canvas


def detect():
    cam = PiCamera()
    generator = cam.frame_generator()

    LOG.info('Warming up...')
    for _ in range(100):
        next(generator)

    first_frame = next(generator)

    resized = cv2.resize(first_frame, (320, 240))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    reference = cv2.GaussianBlur(gray, (21, 21), 0)

    for frame in generator:
        text = 'no motion detected'
        resized = cv2.resize(frame, (320, 240))
        modified = resized.copy()
        current_gray = cv2.cvtColor(modified, cv2.COLOR_BGR2GRAY)

        frame_delta = cv2.absdiff(reference, current_gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        dilated = cv2.dilate(thresh, None, iterations=2)
        contoured, contours, hierarchy = cv2.findContours(
            dilated.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 1:  # first contour is always the complete image
            text = 'motion detected'
            for contour in contours[1:]:
                # if cv2.contourArea(contour) < MIN_AREA:
                #     continue
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(modified, (x, y), (x + w, y + h), (0, 255, 0), 2)

        combined = combine(
            reference,
            frame_delta,
            dilated,
            modified
        )

        with_text = add_text(combined,
                             "Status: {}".format(text),
                             datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"))

        ret, jpeg = cv2.imencode('.jpg', with_text)
        output = jpeg.tostring()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + output + b'\r\n\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(detect(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
