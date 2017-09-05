"""
This module contains various functions which process image objects.
"""

import logging
from datetime import datetime, timedelta
from os import makedirs
from os.path import exists, join

import cv2

import numpy as np
from raspicam.localtypes import Dimension, Point2D
from raspicam.operations import blit, tile
from raspicam.pipeline.detect import (
    DetectionPipeline,
    MotionDetector,
    MutatorOutput,
    box_drawer,
    file_extractor,
    masker
)
from raspicam.pipeline.report import ReportPipeline
from raspicam.storage import NullStorage

LOG = logging.getLogger(__name__)
MAX_REFERENCE_AGE = timedelta(minutes=1)


def as_jpeg(image):
    """
    Takes a OpenCV image and converts it to a JPEG image

    :param image:  The OpenCV image
    :return: a bytes object
    """
    ret, jpeg = cv2.imencode('.jpg', image)
    output = jpeg.tostring()
    return output


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


def text_adder(frames, motion_regions):
    current_time = datetime.now()
    with_text = add_text(frames[-1],
                         'Hello',
                         current_time.strftime("%A %d %B %Y %I:%M:%S%p"))
    return MutatorOutput([with_text], motion_regions)


class DiskWriter:

    def __init__(self, interval, storage, pipeline_index=-1, subdir=''):
        self.interval = interval
        self.storage = storage
        self.last_image_written = datetime(1970, 1, 1)
        self.pipeline_index = pipeline_index
        self.subdir = subdir

    def __call__(self, frames, motion_regions):

        self.storage.write_video(
            frames[self.pipeline_index],
            bool(motion_regions)
        )

        if not motion_regions:
            return MutatorOutput([frames[-1]], motion_regions)

        now = datetime.now()
        if now - self.last_image_written < self.interval:
            return MutatorOutput([frames[-1]], motion_regions)

        self.last_image_written = now

        self.storage.write_snapshot(
            now,
            frames[self.pipeline_index],
            subdir=self.subdir
        )

        return MutatorOutput([frames[-1]], motion_regions)


def detect(frame_generator, storage=None, mask=None, detection_pipeline=None,
           report_pipeline=None):
    """
    Run motion detection.

    This will open the Raspberry PI camera and return a stream of JPEG images as
    bytes objects.

    :param frame_generator: A stream/iterable of frames.
    :param storage: An instance of a storage class. If ``None``, don't store
        anything
    :param mask: An black/white image which will be used as mask for each frame.
        Black pixels will be ignored in motion detection, white pixels will be
        kept.
    :param detection_pipeline: A pipeline object which gets executed for each
        frame and is responsible to report motion.
    :param report_pipeline: A pipeline object which gets executed for each frame
        which contains motion.

    :return: A stream of bytes objects
    """

    storage = storage or NullStorage()
    detection_pipeline = detection_pipeline or DetectionPipeline.make_default()
    if mask:
        detection_pipeline.operations.append(masker(mask))
    detection_pipeline.operations.append(MotionDetector())
    detection_pipeline.operations.append(box_drawer(1))
    detection_pipeline.operations.append(text_adder)
    detection_pipeline.operations.append(DiskWriter(
        timedelta(seconds=5),
        storage,
    ))

    for frame in warmup(frame_generator):
        yield frame

    for frame in frame_generator:
        detection_pipeline.feed(frame)
        yield detection_pipeline.output
