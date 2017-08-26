"""
This module contains various functions which process image objects.
"""

import logging
from datetime import datetime, timedelta
from os import makedirs
from os.path import join, exists

import cv2
import numpy as np

from raspicam.storage import NullStorage
from raspicam.localtypes import Dimension, Point2D

LOG = logging.getLogger(__name__)
MAX_REFERENCE_AGE = timedelta(minutes=1)
MIN_SNAPSHOT_INTERVAL = timedelta(seconds=5)


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


def combine(current, foreground, unmodified, modified):
    """
    Tile 4 images onto one big canvas.
    
    :param current: The image that is currently in use for detection
    :param foreground: The result of foreground detection
    :param unmodified: The frame as seen by the camera
    :param modified: With debug information
    :return: A new canvas with those 4 images tiled
    """

    # make a canvas big enough for 2x2 images of 320x240 and 10px offset
    width = 320 * 2 + 30
    height = 240 * 2 + 30
    canvas = np.zeros((height, width, 3), np.uint8)

    current = cv2.cvtColor(current, cv2.COLOR_GRAY2RGB)
    foreground = cv2.cvtColor(foreground, cv2.COLOR_GRAY2RGB)

    blit(canvas, current, Dimension(320, 240), Point2D(10, 10))
    blit(canvas, foreground, Dimension(320, 240), Point2D(320+20, 10))
    blit(canvas, unmodified, Dimension(320, 240), Point2D(10, 240+20))
    blit(canvas, modified, Dimension(320, 240), Point2D(320+20, 240+20))

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
    if len(image.shape) == 3:
        height, width, channels = image.shape
        canvas_args = [width, channels]
    else:
        height, width = image.shape
        canvas_args = [width]

    title_offset = 20
    new_height = height + (2 * title_offset)
    canvas = np.zeros((new_height, *canvas_args), np.uint8)

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


def warmup(frame_generator, iterations=20):
    LOG.info('Warming up...')
    for i in range(1, iterations+1):
        image = next(frame_generator)
        with_text = add_text(
            image,
            'Warming up... [%d/%d]' % (i, iterations),
            'settling cam...')
        yield with_text
    LOG.info('Warmup done!')


def prepare_frame(frame):
    '''
    Prepares a frame for all comparison operations.

    For this only resizes and blurs it. But this could in the future also apply
    masks and whatnot. The general idea is to remove any unwanted data (noise)
    from the frame which we do not want to consider in motion detection.
    '''
    resized = cv2.resize(frame, (320, 240))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    output = cv2.GaussianBlur(gray, (11, 11), 0)
    return resized, output


def find_motion_regions(fgbg, current):
    '''
    Returns a list of OpenCV contours of areas where motion was detected.
    If the list is empty, no motion was detected.

    The second part of the returned tuple is a list of intermediate images.
    '''

    fgmask = fgbg.apply(current)
    _, contours, _ = cv2.findContours(
        fgmask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 30]
    return contours, [fgmask]


def detect(frame_generator, storage=None):
    """
    Run motion detection.
    
    This will open the Raspberry PI camera and return a stream of JPEG images as bytes objects.
    
    :return: A stream of bytes objects
    """

    storage = storage or NullStorage()

    for frame in warmup(frame_generator):
        yield frame

    fgbg = cv2.createBackgroundSubtractorMOG2()

    last_snap_taken = last_debug_taken = current_time = datetime.now()
    video_output_needed = False

    for frame in frame_generator:
        text = 'no motion detected'
        resized, current = prepare_frame(frame)
        current_time = datetime.now()
        modified = resized.copy()

        contours, intermediaries = find_motion_regions(fgbg, current)

        if contours:
            text = 'motion detected'
            video_output_needed = True
            LOG.debug('Motion detected in %d regions', len(contours))

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(modified, (x, y), (x + w, y + h), (0, 255, 0), 1)

            time_since_snap = current_time - last_snap_taken
            if time_since_snap > MIN_SNAPSHOT_INTERVAL:
                storage.write_snapshot(current_time, modified)
                last_snap_taken = current_time

        combined = combine(
            current,
            intermediaries[0],
            resized,
            modified
        )

        video_storage_finished = storage.write_video(combined, video_output_needed)
        video_output_needed = not video_storage_finished

        with_text = add_text(combined,
                             "Status: {}".format(text),
                             current_time.strftime("%A %d %B %Y %I:%M:%S%p"))

        yield with_text
