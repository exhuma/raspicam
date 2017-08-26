import logging
from abc import ABCMeta, abstractmethod

import cv2

LOG = logging.getLogger(__name__)


class Camera(metaclass=ABCMeta):

    @abstractmethod
    def frame_generator(self):
        raise NotImplementedError('Not yet implemented')


class USBCam(Camera):

    def __init__(self, index=-1):
        self.index = index

    def frame_generator(self):
        video = cv2.VideoCapture(self.index)
        if not video.isOpened():
            raise Exception('Unable to open camera')
        while True:
            success, image = video.read()
            yield image
        video.release()


class PiCamera(Camera):

    def frame_generator(self):
        import picamera
        import picamera.array
        with picamera.PiCamera() as camera:
            with picamera.array.PiRGBArray(camera) as output:
                camera.resolution = (640, 480)
                camera.framerate = 32
                while True:
                    camera.capture(output, 'rgb', use_video_port=True)
                    yield output.array
                    output.truncate(0)
