"""
This module contains various functions which process image objects.
"""

import logging
from collections import namedtuple
from datetime import datetime

import cv2
import numpy as np
from camera import PiCamera

LOG = logging.getLogger(__name__)
Point2D = namedtuple('Point2D', 'x y')
Dimension = namedtuple('Dimension', 'width height')


def as_jpeg(image):
    """
    Takes a OpenCV image and converts it to a JPEG image
    
    :param image:  The OpenCV image
    :return: a bytes object
    """
    ret, jpeg = cv2.imencode('.jpg', image)
    output = jpeg.tostring()
    return output


def blit(canvas, image, size: Dimension, offset: Point2D):
    """
    Resizes an image and copies the resized result onto a canvas at position *offset* with size *size*.
    
    NOTE: The image in *canvas* will be modified in-place!
    
    Example::
    
        >>> canvas = np.zeros((100, 100, 3), np.uint8)
        >>> block = np.ones((100, 100, 3), np.uint8)
        >>> blit(canvas, block, Dimension(20, 20), Point2D(10, 10))
    """
    canvas[offset.y:size.height+offset.y,
    offset.x:size.width + offset.x] = cv2.resize(image, (size.width, size.height))


def combine(reference, frame_delta, dilated, modified):
    """
    Tile 4 images onto one big canvas.
    
    :param reference: The first image
    :param frame_delta: The second image
    :param dilated: The third image
    :param modified: The fourth image
    :return: A new canvas with those 4 images tiled
    """

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
    """
    Add a header and footer to an image.
    
    Example::
    
        >>> new_image = add_text(old_image, 'Hello', 'world!')
        
    :param image: The original image
    :param header:  The header text
    :param footer:  The footer text
    :return: A new image with header and footer added
    """
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


def warmup(frame_generator, iterations=100):
    LOG.info('Warming up...')
    for i in range(1, iterations+1):
        image = next(frame_generator)
        with_text = add_text(
            image,
            'Warming up... [%d/%d]' % (i, iterations),
            'settling cam...')
        yield as_jpeg(with_text)


def detect():
    """
    Run motion detection.
    
    This will open the Raspberry PI camera and return a stream of JPEG images as bytes objects.
    
    :return: A stream of bytes objects
    """
    cam = PiCamera()
    generator = cam.frame_generator()

    for frame in warmup(generator):
        yield frame

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

        yield as_jpeg(with_text)

