from raspicam.localtypes import Dimension

import cv2


def resizer(dimension):
    def fun(frame):
        return cv2.resize(frame, dimension)
    return fun


def togray(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def blur(pixels):
    def fun(frame):
        return cv2.GaussianBlur(frame, (pixels, pixels), 0)
    return fun


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

    def feed(self, frame):
        self.intermediate_frames.append(frame)
        del self.intermediate_frames[:]
        for func in self.operations:
            frame = func(frame)
            self.intermediate_frames.append(frame)
        return frame
