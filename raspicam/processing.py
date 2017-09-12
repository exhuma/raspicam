"""
This module contains various functions which process image objects.
"""

import logging
from datetime import timedelta

import cv2

from raspicam.localtypes import Dimension
from raspicam.operations import add_text
from raspicam.pipeline import tiler

LOG = logging.getLogger(__name__)
MAX_REFERENCE_AGE = timedelta(minutes=1)


def as_jpeg(image):
    """
    Takes a OpenCV image and converts it to a JPEG image

    :param image:  The OpenCV image
    :return: a bytes object
    """
    _, jpeg = cv2.imencode('.jpg', image)
    output = jpeg.tostring()
    return output


def warmup(frame_generator, iterations=20):
    '''
    Read *iterations* frames from *frame_generator*, then return.

    This is useful to give a webcam time to "settle". It usually needs this time
    to determine optimal brightness and exposure settings.
    '''
    LOG.info('Warming up...')
    for i in range(1, iterations+1):
        image = next(frame_generator)
        with_text = add_text(
            image,
            'Warming up... [%d/%d]' % (i, iterations),
            'settling cam...')
        yield with_text
    LOG.info('Warmup done!')


def detect(frame_generator, detection_pipeline, debug=False):
    """
    Run motion detection.

    This will open the Raspberry PI camera and return a stream of JPEG images as
    bytes objects.

    :param frame_generator: A stream/iterable of frames.
    :param detection_pipeline: A pipeline object which gets executed for each
        frame and is responsible to report motion.
    :param debug: If set to True, show intermediate frames as tiles.

    :return: A stream of bytes objects
    """

    if debug:
        detection_pipeline.operations.append(
            tiler(cols=4, tilesize=Dimension(640, 480)))

    for frame in warmup(frame_generator):
        yield frame

    for frame in frame_generator:
        detection_pipeline.feed(frame)
        yield detection_pipeline.output
