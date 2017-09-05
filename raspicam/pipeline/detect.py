import logging
from collections import namedtuple

import cv2

import numpy as np
from raspicam.localtypes import Dimension

LOG = logging.getLogger(__name__)
MutatorOutput = namedtuple('MutatorOutput', 'intermediate_frames motion_regions')


def resizer(dimension):
    def fun(frames, motion_regions):
        return MutatorOutput([cv2.resize(frames[-1], dimension)], motion_regions)
    return fun


def togray(frames, motion_regions):
    return MutatorOutput([cv2.cvtColor(frames[-1], cv2.COLOR_BGR2GRAY)], motion_regions)


def blur(pixels):
    def fun(frames, motion_regions):
        return MutatorOutput([cv2.GaussianBlur(frames[-1], (pixels, pixels), 0)], motion_regions)
    return fun


def masker(mask_filename):

    LOG.debug('Setting mask to %s', mask_filename)
    if not mask_filename:
        return lambda frames, motion_regions: MutatorOutput([frames[-1]], motion_regions)

    mask = cv2.imread(mask_filename, 0)

    def fun(frames, motion_regions):
        frame = frames[-1]

        if len(frame.shape) == 3:
            LOG.warning('Unable to apply the mask to a color image. Convert to B/W first!')
            return MutatorOutput([frame], motion_regions)

        if frame.shape != mask.shape:
            LOG.warning('Mask has differend dimensions than the processed image. '
                        'It should be %s but is %s', frame.shape, mask.shape)
            resized_mask = mask.resize(mask, frame.shape)
        else:
            resized_mask = mask
        bitmask = cv2.inRange(resized_mask, 0, 0) != 0
        output = np.ma.masked_array(frame, mask=bitmask, fill_value=0).filled()
        return MutatorOutput([output], motion_regions)
    return fun


class MotionDetector:

    def __init__(self):
        self.fgbg = cv2.createBackgroundSubtractorMOG2()

    def __call__(self, frames, motion_regions):
        fgmask = self.fgbg.apply(frames[-1])
        shadows = cv2.inRange(fgmask, 127, 127) == 255
        without_shadows = np.ma.masked_array(fgmask, mask=shadows, fill_value=0).filled()
        _, contours, _ = cv2.findContours(
            without_shadows,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 30]
        return MutatorOutput([fgmask, without_shadows], contours)


def file_extractor(filename):
    def extract(frames, motion_regions):
        cv2.imwrite(filename, frames[-1])
        return MutatorOutput(frames, motion_regions)
    return extract


def box_drawer(ref_index=1):
    def draw_bounding_boxes(frames, motion_regions):
        modified = frames[ref_index].copy()
        for contour in motion_regions:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(modified, (x, y), (x+w, y+h), (0, 255, 0), 1)
        return MutatorOutput([modified], motion_regions)
    return draw_bounding_boxes


class DetectionPipeline:

    @staticmethod
    def make_default():
        return DetectionPipeline([
            resizer(Dimension(320, 240)),
            togray,
            blur(11),
        ])

    def __init__(self, operations):
        self.operations = operations
        self.intermediate_frames = []
        self.motion_callbacks = []

    def feed(self, frame):
        del self.intermediate_frames[:]
        self.intermediate_frames.append(frame)
        motion_regions = []
        for i, func in enumerate(self.operations):
            try:
                output = func(self.intermediate_frames, motion_regions)
            except Exception:
                LOG.critical('Exception raise at pipeline position %d in '
                             'function %s', i, func)
                raise
            frame = output.intermediate_frames[-1]
            motion_regions = output.motion_regions
            self.intermediate_frames.extend(output.intermediate_frames)
            if output.motion_regions:
                for callback in self.motion_callbacks:
                    callback(output.motion_regions)
        return frame
