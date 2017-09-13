'''
This module contains helper methods for the project.
'''
import logging

import cv2
from itertools import zip_longest

import numpy as np
from raspicam.localtypes import Dimension, Point2D

LOG = logging.getLogger(__name__)


def add_boxed_text(image, text, origin, font_face, font_scale, thickness,
                   bgcolor, fgcolor):
    '''
    Adds a text-string at the given position surrounded by a filled box.

    The image will be modified in-place!

    :param image: The image onto which to add the text.
    :param text: The string to display.
    :param origin: The upper-left corner of the text.
    :param font_face: The OpenCV font to use.
    :param font_scale: The OpenCV font size.
    :param thickness: "boldness"/font-weight.
    :param bgcolor: The color of the surrounding box.
    :param fgcolor: The color of the text.
    '''
    x_padding = 10
    y_padding = 5
    text_size, text_baseline = cv2.getTextSize(
        text, font_face, font_scale, thickness)
    text_box_size = Dimension(
        text_size[0] + 2*x_padding,
        text_size[1] + text_baseline + 2*y_padding
    )
    cv2.rectangle(image,
                  origin,
                  (origin.x+text_box_size.width, origin.y+text_box_size.height),
                  bgcolor,
                  -1)
    cv2.putText(image,
                text,
                (
                    origin.x+x_padding,
                    origin.y+text_box_size.height-y_padding-int(text_baseline/2)
                ),
                font_face,
                font_scale,
                fgcolor,
                thickness)


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


def tile(images, cols=3, tilesize=Dimension(320, 240), gap=5, labels=None):
    '''
    Creates a new image where each image in *frames* is represented as tile.

    :param images: A collection of images (as numpy arrays)
    :param cols: The number of columns in the resulting image. Rows are added
        automatically on overflow.
    :param tilesize: The size of each tile.
    :param gap: The padding between each tile.
    :param labels: An optional array of labels to apply to tiles.
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

    for image, label in zip_longest(images, labels):
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
        else:
            image = image.copy()

        add_boxed_text(image,
                       str(label),
                       Point2D(30, 30),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       1,
                       2,
                       (60, 0, 0),
                       (255, 255, 255))

        blit(canvas, image, tilesize, padded_position)
        current_col += 1
        if current_col >= cols:
            current_col = 0
            current_row += 1

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


