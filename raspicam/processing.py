"""
This module contains various functions which process image objects.
"""

import logging
from datetime import datetime, timedelta

import cv2

import numpy as np
from raspicam.localtypes import Dimension, Point2D
from raspicam.operations import blit
from raspicam.pipeline import (
    DetectionPipeline,
    MotionDetector,
    MutatorOutput,
    blur,
    box_drawer,
    masker,
    resizer,
    tiler,
    togray
)
from raspicam.storage import NullStorage

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

    font_face = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 1
    padding = 10

    h_size, h_baseline = cv2.getTextSize(
        header, font_face, font_scale, thickness)
    h_size = Dimension(h_size[0], h_size[1] + h_baseline)

    f_size, f_baseline = cv2.getTextSize(
        footer, font_face, font_scale, thickness)
    f_size = Dimension(f_size[0], f_size[1] + f_baseline)

    new_height = height + h_size.height + (4*padding) + f_size.height
    canvas = np.zeros((new_height, *canvas_args), np.uint8)

    blit(canvas, image, Dimension(width, height),
         Point2D(0, h_size.height + (2*padding)))

    cv2.putText(canvas,
                header,
                (padding, h_size.height - h_baseline + padding),
                font_face,
                font_scale,
                (255, 255, 255),
                thickness)
    cv2.putText(canvas,
                footer,
                (padding, canvas.shape[0] - f_baseline - padding),
                font_face,
                font_scale,
                (255, 255, 255),
                thickness)

    return canvas


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


def text_adder(frames, motion_regions):
    '''
    Pipeline operation which adds a default header and footer to a frame.

    :param frames: The list of pipeline frames.
    :param motion_regions: A list of regions containing motion.
    :returns: A MutatorOutput
    '''
    text = 'Motion detected' if motion_regions else 'No motion'
    current_time = datetime.now()
    with_text = add_text(frames[-1],
                         text,
                         current_time.strftime("%A %d %B %Y %I:%M:%S%p"))
    return MutatorOutput('text_adder', [with_text], motion_regions)


class DiskWriter:
    '''
    Pipeline operation which writes files to a storage.

    :param interval: The minimul interval between which images/snapshots should
        be written to disk.
    :param storage: An implementation of :py:class:`raspicam.storage.Storage`.
    :param pipeline_index: The index of pipeline image which should be used as
        storage source.
    :param subdir: Optional sub-directory name for snapshots.
    '''

    def __init__(self, interval, storage, pipeline_index=-1, subdir='',
                 label='DiskWriter'):
        self.interval = interval
        self.storage = storage
        self.last_image_written = datetime(1970, 1, 1)
        self.pipeline_index = pipeline_index
        self.subdir = subdir
        self.label = label

    def __call__(self, frames, motion_regions):

        self.storage.write_video(
            frames[self.pipeline_index],
            bool(motion_regions)
        )

        if not motion_regions:
            return MutatorOutput(self.label, [], motion_regions)

        now = datetime.now()
        if now - self.last_image_written < self.interval:
            return MutatorOutput(self.label, [], motion_regions)

        self.last_image_written = now

        self.storage.write_snapshot(
            now,
            frames[self.pipeline_index],
            subdir=self.subdir
        )

        return MutatorOutput(self.label, [], motion_regions)


def detect(frame_generator, storage=None, mask=None, detection_pipeline=None,
           debug=False):
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
    :param debug: If set to True, show intermediate frames as tiles.

    :return: A stream of bytes objects
    """

    storage = storage or NullStorage()
    if detection_pipeline:
        detection_pipeline = detection_pipeline
    else:
        detection_pipeline = DetectionPipeline([
            resizer(Dimension(640, 480)),
            togray,
            blur(11),
            MotionDetector(),
            box_drawer(0, 1),
            text_adder,
            DiskWriter(
                timedelta(seconds=5),
                storage,
            ),
        ])
        if debug:
            detection_pipeline.operations.append(
                tiler(cols=4, tilesize=Dimension(640, 480)))
        if mask:
            detection_pipeline.operations.insert(2, masker(mask))

    for frame in warmup(frame_generator):
        yield frame

    for frame in frame_generator:
        detection_pipeline.feed(frame)
        yield detection_pipeline.output
