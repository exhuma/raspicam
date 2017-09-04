"""
License plate detection for Luxembourgish plates.

The function ``get_license_plates`` returns a generator of regions which are
likely to be a license plate.

The function ``plate_ocr`` can be used to extract the plate text. This is fairly
strict and may not always return a value.
"""
import re
from math import atan2
from statistics import mean

from raspicam.localtypes import Dimension, Point2D

import cv2
import numpy as np
import pytesseract
from PIL import Image


P_PLATE = re.compile(r'[A-Z]{2} [0-9]{4}')


def order_polygon(points):
    '''
    Given a list of Point2D instances, will sweep across the points and order
    them so they can be used for perspective transforms.
    '''
    center = Point2D(mean([p.x for p in points]), mean(p.y for p in points))
    angles = [atan2(p.x-center.x, p.y-center.y) for p in points]
    combined = sorted(zip(points, angles), key=lambda x: x[1])
    output, _ = zip(*combined)
    return output


def project_2d(img, points, target_size=Dimension(300, 70)):
    """
    Take the region bounded by *points* and project it to *target_size*.

    *points* should be a 4-tuple of Point2D instances.
    """
    # First, bring the points in the right order for projection.
    tmp = order_polygon(points)
    origin_points = [
        tmp[0],
        tmp[3],
        tmp[1],
        tmp[2],
    ]
    origin_points = np.float32(origin_points)
    destination_points = np.float32([
        [0, 0],
        [target_size.width, 0],
        [0, target_size.height],
        [target_size.width, target_size.height]
    ])
    transformation = cv2.getPerspectiveTransform(
        origin_points, destination_points)
    output = cv2.warpPerspective(
        img,
        transformation,
        (target_size.width, target_size.height))
    return output


def get_license_plates(img):
    '''
    Returns a license plate from an image.

    Looks for yellow, rectangular regions in the image and returns them via a
    generator.
    '''

    # boundaries for the color yellow. All values seem to range from 0 to 255 so
    # they must be converted from a 0 to 360 and 0 to 1 scale to a 0 to 255
    # scale.  The docs of openCV mention the values range from 0 to 1, but that
    # does not seem to be the case.  Either way, by inspecting the output of the
    # values I am confident that the values range from 0 to 255 (even the hue).
    boundaries_hsv = [
        np.array(((10/360)*255, 0.8*255, 0.6*255), dtype='uint8'),
        np.array(((80/360)*255, 255, 250), dtype='uint8'),
    ]

    clean = img.copy()
    img = cv2.GaussianBlur(img, (11, 11), 0)

    # Mask everything that is not "yellow"
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, boundaries_hsv[0], boundaries_hsv[1])
    masked = cv2.bitwise_and(img, img, mask=mask)

    # Find contours
    gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
    _, contours, _ = cv2.findContours(
        gray,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)

    # Find contours with 4 vertices
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 10:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        # if the approximated contour has four points, then assume that the
        # contour is a book -- a book is a rectangle and thus has four vertices
        if len(approx) == 4:
            points = [
                Point2D(approx[0][0][0], approx[0][0][1]),
                Point2D(approx[1][0][0], approx[1][0][1]),
                Point2D(approx[2][0][0], approx[2][0][1]),
                Point2D(approx[3][0][0], approx[3][0][1]),
            ]
            yield project_2d(clean, points)


def plate_ocr(img) -> str:
    '''
    Takes an image and runs OCR via tesseract. Returns a string if a text
    matching the template "XX 1234" has been found. Otherwise will return an
    empty string.
    '''
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = Image.fromarray(gray)
    text = pytesseract.image_to_string(img)
    matches = P_PLATE.findall(text.upper())
    if matches:
        return matches[0]
    else:
        return ''
