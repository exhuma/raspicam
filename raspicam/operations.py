'''
This module contains helper methods for the project.
'''
import logging

import cv2

import numpy as np
from raspicam.localtypes import Dimension, Point2D

LOG = logging.getLogger(__name__)


def blit(canvas, image, size: Dimension, offset: Point2D):
    """
    Resizes an image and copies the resized result onto a canvas at position
    *offset* with size *size*.

    NOTE: The image in *canvas* will be modified in-place!

    Example::

        >>> canvas = np.zeros((100, 100, 3), np.uint8)
        >>> block = np.ones((100, 100, 3), np.uint8)
        >>> blit(canvas, block, Dimension(20, 20), Point2D(10, 10))
    """
    LOG.debug('Blitting image of dimension %r to %r', size, offset)
    if len(image.shape) == 2 and len(canvas.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif len(image.shape) == 3 and len(canvas.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    canvas[offset.y:size.height+offset.y,
           offset.x:size.width + offset.x] = cv2.resize(
               image, (size.width, size.height))


def tile(images, cols=3, tilesize=Dimension(320, 240), gap=5):
    '''
    Creates a new image where each image in *frames* is represented as tile.

    :param images: A collection of images (as numpy arrays)
    :param cols: The number of columns in the resulting image. Rows are added
        automatically on overflow.
    :param tilesize: The size of each tile.
    :param gap: The padding between each tile.
    :returns: A new OpenCV image array.
    '''

    rows = len(images) // cols
    if len(images) % cols != 0:
        rows += 1

    width = (tilesize.width * cols) + (gap * (cols+1))
    height = (tilesize.height * rows) + (gap * (rows+1))

    canvas = np.zeros((height, width, 3), np.uint8)
    LOG.debug('Created tile canvas of size %r', Dimension(width, height))

    current_row = 0
    current_col = 0

    for image in images:
        padded_position = Point2D(
            (current_col * tilesize.width) + (gap * (current_col + 1)),
            (current_row * tilesize.height) + (gap * (current_row + 1)))
        if ((padded_position.x + tilesize.width + gap > width) or
                (padded_position.y + tilesize.height + gap > height)):
            LOG.error('Unable to fit all images on the tiled canvas! Increase '
                      'column number, row number or decrease tilesize!')
            continue
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        blit(canvas, image, tilesize, padded_position)
        current_col += 1
        if current_col >= cols:
            current_col = 0
            current_row += 1

    return canvas
